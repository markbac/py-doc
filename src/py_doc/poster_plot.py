"""``plot``: short statistical, quality-control and scientific charts, expanded into Vega-Lite (or Vega, for the
hierarchy charts) and drawn by the tool container like a ``vega-lite`` fence.

A ``plot`` is a ``type=`` and pipe-separated rows. ``expand`` turns it into a spec; the poster or document then
draws it with the theme's Vega config. Anything a preset cannot say is written as a full ``vega-lite`` fence.
"""

from __future__ import annotations

import json
import re
import statistics

from py_doc.errors import ConversionError

VL = "https://vega.github.io/schema/vega-lite/v5.json"
VEGA = "https://vega.github.io/schema/vega/v5.json"
TYPES = (
    "pareto", "spc", "boxplot", "violin", "scatter", "function", "heatmap", "polar", "slope", "parallel", "fan",
    "sunburst", "icicle", "pack",
)  # fmt: skip


class PlotError(ConversionError):
    """A ``plot`` block has a mistake."""


def _rows(code):
    out = []
    for line in code.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            out.append([cell.strip() for cell in line.split("|")])
    return out


def _num(text, what):
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        raise PlotError(f"{what} '{text}' is not a number") from None


def _flag(opts, name):
    return opts.get(name, "no").lower() in ("yes", "true", "1")


def _axis(opts, name, title=None):
    return {"title": opts.get(f"{name}title", title)} if opts.get(f"{name}title", title) is not None else {}


def _spec(opts, body, vega=False):
    spec = {"$schema": VEGA if vega else VL, **body}
    if opts.get("title"):
        spec["title"] = opts["title"]
    if not vega:
        for key in ("width", "height"):
            if opts.get(key, "").isdigit():
                spec[key] = int(opts[key])
    return spec


def expand(code: str, opts: dict) -> tuple[str, str]:
    """The fence (``vega-lite`` or ``vega``) and the JSON spec that draw the ``plot`` block. Raises PlotError."""
    kind = opts.get("type", "").lower()
    if kind not in TYPES:
        raise PlotError(f"plot type must be one of {', '.join(TYPES)}, not '{kind or 'nothing'}'")
    rows = _rows(code)
    spec = globals()[f"_{kind}"](rows, opts)
    fence = "vega" if spec["$schema"] == VEGA else "vega-lite"
    return fence, json.dumps(spec, ensure_ascii=False, indent=1)


# --- quality control ---


def _pareto(rows, opts):
    """Causes as bars in descending order, and the cumulative share as a line with an 80 % guide."""
    data = [{"cause": r[0], "count": _num(r[1], "a count")} for r in rows if len(r) > 1]
    if not data:
        raise PlotError("a pareto plot needs 'cause | count' lines")
    data.sort(key=lambda d: -d["count"])
    total, running = sum(d["count"] for d in data), 0.0
    for d in data:
        running += d["count"]
        d["share"] = running / total
    order = [d["cause"] for d in data]
    x = {"field": "cause", "type": "nominal", "sort": order, "title": opts.get("xtitle")}
    return _spec(opts, {
        "data": {"values": data},
        "layer": [
            {"mark": "bar", "encoding": {"x": x, "y": {"field": "count", "type": "quantitative", "title": opts.get("ytitle", "Count")}}},
            {
                "layer": [
                    {"mark": {"type": "line", "point": True, "color": "#b4540a"},
                     "encoding": {"x": x, "y": {"field": "share", "type": "quantitative", "axis": {"format": "%"}, "scale": {"domain": [0, 1]}, "title": "Cumulative"}}},
                    {"mark": {"type": "rule", "strokeDash": [6, 4], "color": "#a3322b"}, "encoding": {"y": {"datum": 0.8, "type": "quantitative"}}},
                ],
            },
        ],
        "resolve": {"scale": {"y": "independent"}},
    })  # fmt: skip


def _spc(rows, opts):
    """A control chart: the values in order, the centre line, ±1, 2 and 3 sigma, and points outside the limits."""
    data = [{"label": r[0], "value": _num(r[1], "a value"), "n": i} for i, r in enumerate(rows) if len(r) > 1]
    if len(data) < 2:
        raise PlotError("an spc plot needs at least two 'label | value' lines")
    values = [d["value"] for d in data]
    mean = _num(opts["mean"], "mean") if "mean" in opts else statistics.fmean(values)
    sigma = _num(opts["sigma"], "sigma") if "sigma" in opts else statistics.stdev(values)
    ucl = _num(opts["ucl"], "ucl") if "ucl" in opts else mean + 3 * sigma
    lcl = _num(opts["lcl"], "lcl") if "lcl" in opts else mean - 3 * sigma
    for d in data:
        d["out"] = "outside" if not lcl <= d["value"] <= ucl else "inside"
    x = {"field": "label", "type": "ordinal", "sort": None, "title": opts.get("xtitle")}
    bands = [
        {"mark": {"type": "rect", "opacity": 0.08, "color": "#3f74b8"}, "data": {"values": [{"a": mean - k * sigma, "b": mean + k * sigma}]},
         "encoding": {"y": {"field": "a", "type": "quantitative"}, "y2": {"field": "b"}}}
        for k in (2, 1)
    ]  # fmt: skip
    rules = [
        {"mark": {"type": "rule", "color": colour, "strokeDash": dash}, "encoding": {"y": {"datum": value, "type": "quantitative"}}}
        for value, colour, dash in ((mean, "#2a3150", [1, 0]), (ucl, "#a3322b", [6, 4]), (lcl, "#a3322b", [6, 4]))
    ]  # fmt: skip
    labels = [
        {"mark": {"type": "text", "align": "right", "dx": -4, "dy": -6, "color": colour}, "encoding": {"y": {"datum": value, "type": "quantitative"}, "x": {"value": "width"}, "text": {"value": name}}}
        for value, colour, name in ((mean, "#2a3150", "CL"), (ucl, "#a3322b", "UCL"), (lcl, "#a3322b", "LCL"))
    ]  # fmt: skip
    return _spec(opts, {
        "data": {"values": data},
        "layer": bands + rules + labels + [
            {"mark": {"type": "line", "color": "#4a4f5c"}, "encoding": {"x": x, "y": {"field": "value", "type": "quantitative", "scale": {"zero": False}, "title": opts.get("ytitle")}}},
            {"mark": {"type": "point", "filled": True, "size": 60},
             "encoding": {"x": x, "y": {"field": "value", "type": "quantitative"},
                          "color": {"field": "out", "type": "nominal", "scale": {"domain": ["inside", "outside"], "range": ["#3f74b8", "#a3322b"]}, "legend": None}}},
        ],
    })  # fmt: skip


# --- distributions ---


def _samples(rows):
    data = []
    for r in rows:
        if len(r) < 2:
            raise PlotError(f"a line is 'group | values', not '{' | '.join(r)}'")
        for v in re.split(r"[,\s]+", r[1].strip()):
            if v:
                data.append({"group": r[0], "value": _num(v, "a value")})
    if not data:
        raise PlotError("the plot needs 'group | values' lines")
    return data


def _boxplot(rows, opts):
    """Median, quartiles and whiskers of each group, with its samples as dots when ``points=yes``."""
    data = _samples(rows)
    x = {"field": "group", "type": "nominal", "title": opts.get("xtitle")}
    y = {"field": "value", "type": "quantitative", "title": opts.get("ytitle"), "scale": {"zero": False}}
    layers = [{"mark": {"type": "boxplot", "extent": 1.5, "size": 40}, "encoding": {"x": x, "y": y}}]
    if _flag(opts, "points"):
        layers.append({"mark": {"type": "point", "filled": True, "opacity": 0.5, "color": "#1d1f27"},
                       "transform": [{"calculate": "random()", "as": "jitter"}],
                       "encoding": {"x": x, "xOffset": {"field": "jitter", "type": "quantitative"}, "y": y}})  # fmt: skip
    return _spec(opts, {"data": {"values": data}, "layer": layers})


def _violin(rows, opts):
    """The density of each group's values, mirrored as a violin."""
    data = _samples(rows)
    return _spec(opts, {
        "data": {"values": data},
        "transform": [{"density": "value", "groupby": ["group"], "as": ["value", "density"]}],
        "mark": {"type": "area", "orient": "horizontal"},
        "width": 90,
        "encoding": {
            "y": {"field": "value", "type": "quantitative", "title": opts.get("ytitle")},
            "x": {"field": "density", "type": "quantitative", "stack": "center", "impute": None, "title": None,
                  "axis": {"labels": False, "values": [0], "grid": False, "ticks": True}},
            "column": {"field": "group", "type": "nominal", "header": {"titleOrient": "bottom", "labelOrient": "bottom", "labelPadding": 0}, "title": opts.get("xtitle")},
            "color": {"field": "group", "type": "nominal", "legend": None},
        },
        "config": {"facet": {"spacing": 0}, "view": {"stroke": None}},
    })  # fmt: skip


# --- relations ---


def _scatter(rows, opts):
    """``label | x | y | size | colour`` points; log and inverted axes, and labels with ``labels=yes``."""
    data = []
    for r in rows:
        if len(r) < 3:
            raise PlotError(f"a scatter line is 'label | x | y', not '{' | '.join(r)}'")
        point = {"label": r[0], "x": _num(r[1], "an x value"), "y": _num(r[2], "a y value")}
        if len(r) > 3 and r[3]:
            point["size"] = _num(r[3], "a size")
        if len(r) > 4 and r[4]:
            point["group"] = r[4]
        data.append(point)
    if not data:
        raise PlotError("a scatter plot needs 'label | x | y' lines")

    def scale(axis):
        out = {"type": "log"} if _flag(opts, f"{axis}log") else {"zero": False}
        if _flag(opts, f"{axis}invert"):
            out["reverse"] = True
        return out

    enc = {
        "x": {"field": "x", "type": "quantitative", "scale": scale("x"), "title": opts.get("xtitle", "x")},
        "y": {"field": "y", "type": "quantitative", "scale": scale("y"), "title": opts.get("ytitle", "y")},
        "tooltip": [{"field": "label"}],
    }
    if any("size" in d for d in data):
        enc["size"] = {"field": "size", "type": "quantitative", "legend": None}
    if any("group" in d for d in data):
        enc["color"] = {"field": "group", "type": "nominal", "title": None}
    layers = [{"mark": {"type": "point", "filled": True, "opacity": 0.85}, "encoding": enc}]
    if _flag(opts, "labels"):
        layers.append(
            {
                "mark": {"type": "text", "align": "left", "dx": 7, "fontSize": 11},
                "encoding": {"x": enc["x"], "y": enc["y"], "text": {"field": "label"}},
            }
        )
    return _spec(opts, {"data": {"values": data}, "layer": layers})


def _function(rows, opts):
    """Curves from expressions of ``x`` over ``from`` to ``to``: ``curve: label | expression`` lines, with
    ``area: from | to | label`` shading under the first curve and ``rule: x | label`` lines. ``preset=normal``
    draws the normal distribution with its sigma bands."""
    curves, areas, rules = [], [], []
    preset = opts.get("preset", "").lower()
    if preset == "normal":
        curves.append(("Normal", "exp(-datum.x * datum.x / 2) / sqrt(2 * PI)"))
        areas += [(-3, 3, "99.7 %"), (-2, 2, "95 %"), (-1, 1, "68 %")]
        opts = {"from": "-4", "to": "4", **opts}
    elif preset:
        raise PlotError(f"function preset must be normal, not '{preset}'")
    for r in rows:
        kind, _, first = r[0].partition(":")
        kind = kind.strip().lower()
        cells = [first.strip()] + r[1:]
        if kind == "curve":
            if len(cells) < 2:
                raise PlotError("a curve is 'curve: label | expression in x'")
            curves.append((cells[0], re.sub(r"\bx\b", "datum.x", cells[1])))
        elif kind == "area":
            areas.append(
                (_num(cells[0], "an area start"), _num(cells[1], "an area end"), cells[2] if len(cells) > 2 else "")
            )
        elif kind == "rule":
            rules.append((_num(cells[0], "a rule"), cells[1] if len(cells) > 1 else ""))
        else:
            raise PlotError(f"a function line starts curve:, area: or rule:, not '{r[0]}'")
    if not curves:
        raise PlotError("a function plot needs a 'curve: label | expression' line")
    low, high = _num(opts.get("from", "0"), "from"), _num(opts.get("to", "10"), "to")
    if high <= low:
        raise PlotError("function to= must be above from=")
    step = (high - low) / int(opts.get("samples", "200"))
    calcs = [{"calculate": expr, "as": f"c{n}"} for n, (_, expr) in enumerate(curves)]
    names = {f"c{n}": name for n, (name, _) in enumerate(curves)}
    base = {"data": {"sequence": {"start": low, "stop": high + step / 2, "step": step, "as": "x"}}, "transform": calcs}
    x = {"field": "x", "type": "quantitative", "title": opts.get("xtitle", "x")}
    layers = []
    for a, b, text in areas:
        layers.append({
            "mark": {"type": "area", "opacity": 0.18},
            "transform": [{"filter": f"datum.x >= {a} && datum.x <= {b}"}],
            "encoding": {"x": x, "y": {"field": "c0", "type": "quantitative"}},
        })  # fmt: skip
    layers.append({
        "transform": [{"fold": list(names), "as": ["curve", "y"]}, {"calculate": f"{json.dumps(names)}[datum.curve]", "as": "name"}],
        "mark": {"type": "line", "strokeWidth": 2.5},
        "encoding": {"x": x, "y": {"field": "y", "type": "quantitative", "title": opts.get("ytitle", "y")},
                     "color": {"field": "name", "type": "nominal", "title": None, "legend": None if len(curves) == 1 else {}}},
    })  # fmt: skip
    for value, text in rules:
        layers.append(
            {
                "mark": {"type": "rule", "strokeDash": [5, 4]},
                "encoding": {"x": {"datum": value, "type": "quantitative"}},
            }
        )
        if text:
            layers.append(
                {
                    "mark": {"type": "text", "dy": -6, "align": "left", "dx": 4},
                    "encoding": {
                        "x": {"datum": value, "type": "quantitative"},
                        "y": {"value": 0},
                        "text": {"value": text},
                    },
                }
            )
    return _spec(opts, {**base, "layer": layers})


# --- matrices and comparisons ---

RISK = ["#2e6b3a", "#8dce46", "#ffd500", "#ef8023", "#a3322b"]


def _heatmap(rows, opts):
    """A header ``| col | col`` then ``row | value | value`` lines, as coloured cells with their values.
    ``preset=risk`` is a likelihood by severity matrix in green to red."""
    if opts.get("preset", "").lower() == "risk":
        size = 5
        data = [{"row": str(r), "col": str(c), "value": r * c} for r in range(size, 0, -1) for c in range(1, size + 1)]
        marks = {(r[0], r[1]): r[2] for r in rows if len(r) > 2}  # likelihood | severity | label
        for d in data:
            d["label"] = marks.get((d["row"], d["col"]), "")
        level = "datum.value <= 4 ? 'Low' : datum.value <= 9 ? 'Medium' : datum.value <= 14 ? 'High' : 'Very high'"
        return _spec(opts, {
            "data": {"values": data},
            "transform": [{"calculate": level, "as": "level"}],
            "width": 300, "height": 300,
            "encoding": {
                "x": {"field": "col", "type": "ordinal", "title": opts.get("xtitle", "Severity")},
                "y": {"field": "row", "type": "ordinal", "sort": "descending", "title": opts.get("ytitle", "Likelihood")},
            },
            "layer": [
                {"mark": {"type": "rect", "stroke": "#fff", "strokeWidth": 2},
                 "encoding": {"color": {"field": "level", "type": "ordinal", "scale": {"domain": ["Low", "Medium", "High", "Very high"], "range": RISK[0:1] + RISK[2:]}, "title": None}}},
                {"mark": {"type": "text", "fontWeight": "bold", "color": "#1d1f27"}, "encoding": {"text": {"field": "label"}}},
            ],
        })  # fmt: skip
    if not rows or rows[0][0]:
        raise PlotError("a heatmap starts with a header such as '| Mon | Tue | Wed'")
    heads = rows[0][1:]
    data = []
    for r in rows[1:]:
        for head, cell in zip(heads, r[1:]):
            data.append({"row": r[0], "col": head, "value": _num(cell, "a heatmap value")})
    return _spec(opts, {
        "data": {"values": data},
        "encoding": {
            "x": {"field": "col", "type": "ordinal", "sort": heads, "title": opts.get("xtitle")},
            "y": {"field": "row", "type": "ordinal", "sort": None, "title": opts.get("ytitle")},
        },
        "layer": [
            {"mark": "rect", "encoding": {"color": {"field": "value", "type": "quantitative", "scale": {"scheme": opts.get("scheme", "blues")}, "title": opts.get("unit")}}},
            {"mark": {"type": "text", "fontSize": 11}, "encoding": {"text": {"field": "value", "type": "quantitative"}}},
        ],
    })  # fmt: skip


def _polar(rows, opts):
    """``label | value | colour`` as equal slices whose radius is the value: a wind rose or a polar bar chart."""
    data = [{"label": r[0], "value": _num(r[1], "a value"), "n": i} for i, r in enumerate(rows) if len(r) > 1]
    if not data:
        raise PlotError("a polar plot needs 'label | value' lines")
    return _spec(opts, {
        "data": {"values": data},
        "width": 300, "height": 300,
        "layer": [
            {"mark": {"type": "arc", "stroke": "#fff", "padAngle": 0.02},
             "encoding": {"theta": {"field": "label", "type": "nominal", "sort": None, "stack": True},
                          "radius": {"field": "value", "type": "quantitative", "scale": {"type": "sqrt", "zero": True, "rangeMin": 20}},
                          "color": {"field": "label", "type": "nominal", "sort": None, "legend": None}}},
            {"mark": {"type": "text", "radiusOffset": 14},
             "encoding": {"theta": {"field": "label", "type": "nominal", "sort": None, "stack": True},
                          "radius": {"field": "value", "type": "quantitative", "scale": {"type": "sqrt", "zero": True, "rangeMin": 20}},
                          "text": {"field": "label"}}},
        ],
    })  # fmt: skip


def _slope(rows, opts):
    """A header ``| Before | After`` then ``label | before | after`` lines, as lines that rise or fall."""
    if not rows or rows[0][0] or len(rows[0]) < 3:
        raise PlotError("a slope plot starts with a header such as '| 2020 | 2025'")
    heads = rows[0][1:3]
    data = []
    for r in rows[1:]:
        a, b = _num(r[1], "a value"), _num(r[2], "a value")
        trend = "up" if b >= a else "down"
        data += [
            {"label": r[0], "when": heads[0], "value": a, "trend": trend},
            {"label": r[0], "when": heads[1], "value": b, "trend": trend},
        ]
    x = {"field": "when", "type": "ordinal", "sort": heads, "title": None, "axis": {"orient": "top", "labelAngle": 0}}
    y = {"field": "value", "type": "quantitative", "title": opts.get("ytitle"), "scale": {"zero": False}}
    colour = {
        "field": "trend",
        "type": "nominal",
        "scale": {"domain": ["up", "down"], "range": ["#2e6b3a", "#a3322b"]},
        "legend": None,
    }
    return _spec(opts, {
        "data": {"values": data},
        "width": 260,
        "layer": [
            {"mark": {"type": "line", "point": True, "strokeWidth": 2.5}, "encoding": {"x": x, "y": y, "detail": {"field": "label"}, "color": colour}},
            {"transform": [{"filter": f"datum.when == {json.dumps(heads[1])}"}], "mark": {"type": "text", "align": "left", "dx": 8},
             "encoding": {"x": x, "y": y, "text": {"field": "label"}}},
        ],
    })  # fmt: skip


def _parallel(rows, opts):
    """A header ``| axis | axis`` then ``item | value | value`` lines: one line per item across its axes, each
    axis scaled from its own lowest to its highest value."""
    if not rows or rows[0][0] or len(rows[0]) < 3:
        raise PlotError("a parallel plot starts with a header such as '| Range | Battery | Cost'")
    heads = rows[0][1:]
    data = []
    for r in rows[1:]:
        values = [_num(c, "a value") for c in r[1 : len(heads) + 1]]
        data.append({"item": r[0], **{h: v for h, v in zip(heads, values)}})
    ranges = {h: (min(d[h] for d in data), max(d[h] for d in data)) for h in heads}
    long = []
    for d in data:
        for h in heads:
            lo, hi = ranges[h]
            long.append(
                {"item": d["item"], "axis": h, "share": 0.5 if hi == lo else (d[h] - lo) / (hi - lo), "value": d[h]}
            )
    ends = [{"axis": h, "share": s, "text": f"{v:g}"} for h in heads for s, v in ((0, ranges[h][0]), (1, ranges[h][1]))]
    x = {"field": "axis", "type": "nominal", "sort": heads, "title": None, "axis": {"orient": "top", "labelAngle": 0}}
    return _spec(opts, {
        "width": 120 * len(heads),
        "layer": [
            {"data": {"values": long}, "mark": {"type": "rule", "color": "#9aa0ab"}, "encoding": {"x": x}},
            {"data": {"values": long}, "mark": {"type": "line", "strokeWidth": 2.5, "point": True},
             "encoding": {"x": x, "y": {"field": "share", "type": "quantitative", "axis": None}, "color": {"field": "item", "type": "nominal", "title": None}, "detail": {"field": "item"}}},
            {"data": {"values": ends}, "mark": {"type": "text", "dx": -6, "align": "right", "fontSize": 10}, "encoding": {"x": x, "y": {"field": "share", "type": "quantitative"}, "text": {"field": "text"}}},
        ],
    })  # fmt: skip


def _fan(rows, opts):
    """``history: x | value`` lines, then ``forecast: x | median | 50 % low | high | 80 % low | high | 95 % low | high``."""
    history, forecast = [], []
    for r in rows:
        kind, _, first = r[0].partition(":")
        cells = [first.strip()] + r[1:]
        if kind.strip().lower() == "history":
            history.append({"x": cells[0], "y": _num(cells[1], "a value")})
        elif kind.strip().lower() == "forecast":
            if len(cells) < 8:
                raise PlotError(
                    "a forecast line is 'forecast: x | median | 50 low | 50 high | 80 low | 80 high | 95 low | 95 high'"
                )
            v = [_num(c, "a forecast value") for c in cells[1:8]]
            forecast.append(
                {"x": cells[0], "y": v[0], "l50": v[1], "h50": v[2], "l80": v[3], "h80": v[4], "l95": v[5], "h95": v[6]}
            )
        else:
            raise PlotError(f"a fan line starts history: or forecast:, not '{r[0]}'")
    if not history or not forecast:
        raise PlotError("a fan plot needs history: and forecast: lines")
    order = [d["x"] for d in history] + [d["x"] for d in forecast if d["x"] not in {h["x"] for h in history}]
    x = {"field": "x", "type": "ordinal", "sort": order, "title": opts.get("xtitle")}
    bands = [
        {"data": {"values": forecast}, "mark": {"type": "area", "opacity": opacity, "color": "#3f74b8"},
         "encoding": {"x": x, "y": {"field": low, "type": "quantitative"}, "y2": {"field": high}}}
        for low, high, opacity in (("l95", "h95", 0.15), ("l80", "h80", 0.25), ("l50", "h50", 0.4))
    ]  # fmt: skip
    return _spec(opts, {
        "layer": bands + [
            {"data": {"values": history}, "mark": {"type": "line", "strokeWidth": 2.5, "color": "#2a3150"}, "encoding": {"x": x, "y": {"field": "y", "type": "quantitative", "title": opts.get("ytitle"), "scale": {"zero": False}}}},
            {"data": {"values": forecast}, "mark": {"type": "line", "strokeDash": [6, 4], "strokeWidth": 2.5, "color": "#2a3150"}, "encoding": {"x": x, "y": {"field": "y", "type": "quantitative"}}},
        ],
    })  # fmt: skip


# --- hierarchies, in Vega ---


def _tree(rows):
    """``Group / Item | value`` lines as the id, parent and size records of a Vega stratify transform."""
    nodes, leaves = {"root": None}, []
    for r in rows:
        if len(r) < 2:
            raise PlotError(f"a hierarchy line is 'Group / Item | value', not '{' | '.join(r)}'")
        path = [p.strip() for p in r[0].split("/") if p.strip()]
        parent = "root"
        for depth in range(len(path)):
            node = "/".join(path[: depth + 1])
            nodes.setdefault(node, parent)
            parent = node
        leaves.append((parent, _num(r[1], "a value")))
    sizes = dict(leaves)
    data = [{"id": "root", "parent": None, "name": "", "size": 0}]
    for node, parent in nodes.items():
        if node != "root":
            data.append({"id": node, "parent": parent, "name": node.split("/")[-1], "size": sizes.get(node, 0)})
    if len(data) < 2:
        raise PlotError("the plot needs 'Group / Item | value' lines")
    return data


def _hierarchy(rows, opts, layout):
    data = _tree(rows)
    size = int(opts.get("size", "360"))
    transforms = [{"type": "stratify", "key": "id", "parentKey": "parent"}]
    if layout == "pack":
        transforms.append(
            {
                "type": "pack",
                "field": "size",
                "sort": {"field": "value"},
                "size": [{"signal": "width"}, {"signal": "height"}],
                "padding": 3,
            }
        )
    else:
        transforms.append({
            "type": "partition", "field": "size", "sort": {"field": "value", "order": "descending"},
            "size": [{"signal": "2 * PI"}, {"signal": "width / 2"}] if layout == "sunburst" else [{"signal": "width"}, {"signal": "height"}],
            "as": ["a0", "r0", "a1", "r1", "depth", "children"],
        })  # fmt: skip
    colour = {"scale": "color", "field": "depth"}
    if layout == "sunburst":
        marks = [{
            "type": "arc", "from": {"data": "tree"},
            "encode": {"enter": {"x": {"signal": "width / 2"}, "y": {"signal": "height / 2"}, "fill": colour, "stroke": {"value": "#fff"}, "tooltip": {"signal": "datum.name"}},
                       "update": {"startAngle": {"field": "a0"}, "endAngle": {"field": "a1"}, "innerRadius": {"field": "r0"}, "outerRadius": {"field": "r1"}, "fillOpacity": {"signal": "datum.depth == 0 ? 0 : 1"}}},
        }, {
            "type": "text", "from": {"data": "tree"},
            "encode": {"enter": {"x": {"signal": "width / 2"}, "y": {"signal": "height / 2"}, "fill": {"value": "#fff"}, "fontSize": {"value": 11}, "align": {"value": "center"}, "baseline": {"value": "middle"}},
                       "update": {"radius": {"signal": "(datum.r0 + datum.r1) / 2"}, "theta": {"signal": "(datum.a0 + datum.a1) / 2"},
                                  "text": {"signal": "datum.depth > 0 && (datum.a1 - datum.a0) * (datum.r0 + datum.r1) / 2 > 34 ? datum.name : ''"}}},
        }]  # fmt: skip
    elif layout == "icicle":
        marks = [{
            "type": "rect", "from": {"data": "tree"},
            "encode": {"enter": {"fill": colour, "stroke": {"value": "#fff"}, "tooltip": {"signal": "datum.name"}},
                       "update": {"x": {"field": "a0"}, "x2": {"field": "a1"}, "y": {"field": "r0"}, "y2": {"field": "r1"}, "fillOpacity": {"signal": "datum.depth == 0 ? 0 : 1"}}},
        }, {
            "type": "text", "from": {"data": "tree"},
            "encode": {"enter": {"fill": {"value": "#fff"}, "fontSize": {"value": 11}, "align": {"value": "center"}, "baseline": {"value": "middle"}},
                       "update": {"x": {"signal": "(datum.a0 + datum.a1) / 2"}, "y": {"signal": "(datum.r0 + datum.r1) / 2"},
                                  "text": {"signal": "datum.depth > 0 && datum.a1 - datum.a0 > 40 ? datum.name : ''"}}},
        }]  # fmt: skip
    else:
        marks = [{
            "type": "symbol", "from": {"data": "tree"},
            "encode": {"enter": {"shape": {"value": "circle"}, "fill": colour, "stroke": {"value": "#fff"}, "tooltip": {"signal": "datum.name"}},
                       "update": {"x": {"field": "x"}, "y": {"field": "y"}, "size": {"signal": "4 * datum.r * datum.r"}, "fillOpacity": {"signal": "datum.depth == 0 ? 0.08 : 1"}}},
        }, {
            "type": "text", "from": {"data": "tree"},
            "encode": {"enter": {"fill": {"value": "#fff"}, "fontSize": {"value": 11}, "align": {"value": "center"}, "baseline": {"value": "middle"}},
                       "update": {"x": {"field": "x"}, "y": {"field": "y"}, "text": {"signal": "!datum.children && datum.r > 22 ? datum.name : ''"}}},
        }]  # fmt: skip
    return _spec(opts, {
        "width": size, "height": size if layout != "icicle" else int(size * 0.6), "padding": 4, "autosize": "none",
        "data": [{"name": "tree", "values": data, "transform": transforms}],
        "scales": [{"name": "color", "type": "ordinal", "domain": [0, 1, 2, 3, 4], "range": "category"}],
        "marks": marks,
    }, vega=True)  # fmt: skip


def _sunburst(rows, opts):
    return _hierarchy(rows, opts, "sunburst")


def _icicle(rows, opts):
    return _hierarchy(rows, opts, "icicle")


def _pack(rows, opts):
    return _hierarchy(rows, opts, "pack")
