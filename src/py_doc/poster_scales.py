"""Poster blocks that show values on a scale: bands with trigger points, a waterfall, tanks, a dial, a 24-hour
clock, a rating, a colour ruler, a log ruler and spectra. Each is drawn as SVG with ``poster_svg``, so it prints
sharp and can be a picture of its own in a document.
"""

from __future__ import annotations

import hashlib
import math
import re

from py_doc.poster_blocks import Fragment, PosterError, block, esc
from py_doc.poster_svg import Linear, Log10, extent, label, number, polar, sector, spread, svg, text_width, wrap

WIDTH = 640  # the width every scale is drawn at; it is scaled to its column like a chart
SIZE = 13  # label size, as in a chart
SMALL = 11.5


def _width(opts, ctx, default=WIDTH):
    """The width the block is drawn at: ``width=`` in pixels, else ``default``. A wider drawing keeps its
    text smaller when the block spans a full-width section."""
    if "width" not in opts:
        return default
    if not opts["width"].isdigit() or not 300 <= int(opts["width"]) <= 2400:
        raise PosterError(
            f"{ctx.where}: width must be a whole number of pixels from 300 to 2400, not '{opts['width']}'"
        )
    return int(opts["width"])


def _fig(opts, picture):
    title = f'<div class="fig-title">{esc(opts["title"])}</div>' if opts.get("title") else ""
    return Fragment(f'<div class="fig">{title}{picture}</div>', picture)


def _id(kind, code, n=0):
    """An id for a gradient that differs between blocks, and stays the same between builds."""
    return f"{kind}{hashlib.sha1(code.encode('utf-8')).hexdigest()[:8]}{n}"


def _number_of(text, what, ctx):
    try:
        return float(str(text).replace(",", "").replace("£", "").replace("$", "").strip())
    except ValueError:
        raise PosterError(f"{ctx.where}: {what} '{text}' is not a number") from None


def _lines(code):
    return [line.strip() for line in code.splitlines() if line.strip()]


def _cells(line):
    return [cell.strip() for cell in line.split("|")]


def _is_colour(text, ctx):
    try:
        ctx.theme.colour(text)
        return bool(text) and not re.search(r"\s", text)
    except Exception:
        return False


def _text_block(x, y, lines, size, width, anchor="start", extra=""):
    """Lines of wrapped text from ``y`` down; returns the SVG and the y under the last line."""
    out, step = "", size * 1.3
    for line in lines:
        for part in wrap(line, width, size, "700" in extra):
            y += step
            out += label(x, y - size * 0.3, part, size, anchor, extra)
    return out, y


# ---------------------------------------------------------------------------
# threshold: proportional bands, with exact trigger points pinned to their edges
# ---------------------------------------------------------------------------


def _span(cells, ctx):
    """``label | text ... | colour | weight``: the colour and the weight are optional, at the end."""
    weight = 1.0
    if len(cells) > 1 and re.fullmatch(r"\d+(\.\d+)?", cells[-1]):
        weight = float(cells.pop())
    colour = None
    if len(cells) > 1 and _is_colour(cells[-1], ctx):
        colour = cells.pop()
    return {"label": cells[0], "texts": [c for c in cells[1:] if c], "colour": colour, "weight": weight}


@block(
    "threshold",
    "span: label | text | colour | weight lines, with pin: text | colour lines between them; title=, target=",
    "span: Normal | Supply on | green | 4\npin: £0.00 Credit exhausted | red\nspan: Emergency credit | £10 pool | amber | 2",
)
def threshold_html(code, opts, ctx):
    """Bands in proportion to their weights, and trigger points pinned between them, with each band's words
    under it so no text is squeezed into a narrow box. ``target:`` (or ``target=``) marks a nominal point."""
    WIDTH = _width(opts, ctx, 960)  # noqa: N806
    items = []
    for line in _lines(code):
        kind, _, rest = line.partition(":")
        kind = kind.strip().lower()
        if kind not in ("span", "pin", "target") or not rest.strip():
            raise PosterError(f"{ctx.where}: a threshold line starts span:, pin: or target:, not '{line}'")
        cells = _cells(rest)
        if kind == "span":
            items.append(("span", _span(cells, ctx)))
        else:
            colour = cells[1] if len(cells) > 1 and cells[1] else None
            items.append((kind, {"label": cells[0], "colour": colour}))
    spans = [item for kind, item in items if kind == "span"]
    if not spans:
        raise PosterError(f"{ctx.where}: a threshold block needs at least one span: line")
    total = sum(span["weight"] for span in spans)
    left, right = 8, WIDTH - 8
    x_of = Linear(0, total, left, right)
    # Where each span starts and ends, and where each pin or target goes
    at, pins, marks = 0.0, [], []
    for kind, item in items:
        if kind == "span":
            item["x0"], item["x1"] = x_of(at), x_of(at + item["weight"])
            at += item["weight"]
        elif kind == "pin":
            pins.append((x_of(at), item))
        else:
            previous = [span for span in spans if "x1" in span]
            centre = (previous[-1]["x0"] + previous[-1]["x1"]) / 2 if previous else x_of(at)
            marks.append((centre, item))
    if opts.get("target"):
        widest = max(spans, key=lambda span: span["weight"])
        marks.append(((widest["x0"] + widest["x1"]) / 2, {"label": opts["target"], "colour": None}))
    # Pin labels above the bar, in rows so no two overlap
    rows: list[list[tuple[float, float]]] = []
    placed = []
    for x, item in pins + marks:
        lines = wrap(item["label"], 200, SMALL, bold=True)
        half = max(text_width(line, SMALL, bold=True) for line in lines) / 2 + 6
        lo, hi = max(left, x - half), min(right, x + half)
        row = next((r for r, used in enumerate(rows) if all(hi < a or lo > b for a, b in used)), len(rows))
        if row == len(rows):
            rows.append([])
        rows[row].append((lo, hi))
        placed.append((x, item, lines, row, (lo + hi) / 2))
    line_h = SMALL * 1.3
    row_h = [max([len(p[2]) for p in placed if p[3] == r] or [1]) * line_h + 6 for r in range(len(rows))]
    top = 6 + sum(row_h)
    bar_y, bar_h = top + 10, 30
    out = []
    for span in spans:
        colour = ctx.theme.colour(span["colour"], "secondary")
        w = span["x1"] - span["x0"]
        out.append(
            f'<rect x="{span["x0"]:.1f}" y="{bar_y:.1f}" width="{w:.1f}" height="{bar_h}" fill="{colour}" stroke="#fff" stroke-width="1.5"/>'
        )
    for x, item, lines, row, middle in placed:
        colour = ctx.theme.colour(item["colour"], "strong")
        y_text = 6 + sum(row_h[:row])
        anchor_x = min(max(middle, left + 4), right - 4)
        text, y_end = _text_block(anchor_x, y_text, lines, SMALL, 200, "middle", f'fill="{colour}" font-weight="700"')
        out.append(text)
        is_target = item in [m[1] for m in marks]
        out.append(
            f'<line x1="{x:.1f}" y1="{y_end + 1:.1f}" x2="{x:.1f}" y2="{bar_y + bar_h + 4:.1f}" stroke="{colour}" stroke-width="2"'
            + (' stroke-dasharray="4 3"' if is_target else "")
            + "/>"
        )
        shape = (
            f'<path d="M{x - 6:.1f},{bar_y - 9:.1f} L{x + 6:.1f},{bar_y - 9:.1f} L{x:.1f},{bar_y - 1:.1f} Z" fill="{colour}"/>'
            if is_target
            else f'<circle cx="{x:.1f}" cy="{bar_y - 4:.1f}" r="4" fill="{colour}"/>'
        )
        out.append(shape)
    # Each band's words under it
    bottom = bar_y + bar_h + 8
    for span in spans:
        w = max(span["x1"] - span["x0"] - 6, 40)
        colour = ctx.theme.colour(span["colour"], "secondary")
        head, y = _text_block(
            span["x0"] + 3,
            bar_y + bar_h + 6,
            [span["label"]],
            SMALL + 0.5,
            w,
            extra=f'font-weight="700" fill="{colour}"',
        )
        body, y = _text_block(span["x0"] + 3, y, span["texts"], SMALL, w, extra=f'fill="{ctx.theme.colours["muted"]}"')
        out += [head, body]
        bottom = max(bottom, y)
    return _fig(opts, svg(WIDTH, bottom + 6, "".join(out), opts.get("title", "threshold"), "chart"))


# ---------------------------------------------------------------------------
# waterfall: an amount, with what is added and taken away, step by step
# ---------------------------------------------------------------------------


def waterfall_html(code, opts, ctx):
    """``Label | +25.00 | colour | note`` lines: ``+`` adds, ``-`` takes away, ``=`` shows the total so far."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    unit = opts.get("unit", "")
    rows, total = [], 0.0
    for line in _lines(code):
        cells = _cells(line)
        if len(cells) < 2:
            raise PosterError(f"{ctx.where}: a waterfall line is 'Label | +value', not '{line}'")
        raw = cells[1].replace(" ", "")
        kind = "=" if raw.startswith("=") else "step"
        value = _number_of(raw.lstrip("="), "a waterfall value", ctx)
        start = 0.0 if kind == "=" else total
        end = value if kind == "=" else total + value
        total = end
        colour = cells[2] if len(cells) > 2 and cells[2] else None
        default = "primary" if kind == "=" else "good" if value >= 0 else "bad"
        rows.append(
            (cells[0], value, start, end, kind, ctx.theme.colour(colour, default), cells[3] if len(cells) > 3 else "")
        )
    if not rows:
        raise PosterError(f"{ctx.where}: a waterfall needs at least one 'Label | value' line")
    low, high = extent([v for row in rows for v in (row[2], row[3])] + [0])
    left, right, top = 52, 12, 14
    plot_h = 220
    y_of = Linear(low, high, top + plot_h, top)
    band = (WIDTH - left - right) / len(rows)
    out = []
    step = (high - low) / 4
    for v in y_of.ticks(step):
        out.append(
            f'<line x1="{left}" y1="{y_of(v):.1f}" x2="{WIDTH - right}" y2="{y_of(v):.1f}" stroke="currentColor" stroke-opacity=".2"/>'
        )
        out.append(label(left - 6, y_of(v) + 4, number(round(v, 9)), SIZE, "end"))
    bottom = top + plot_h
    for i, (name, value, start, end, kind, colour, note) in enumerate(rows):
        x = left + band * i + band * 0.15
        w = band * 0.7
        y0, y1 = sorted((y_of(start), y_of(end)))
        out.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{max(y1 - y0, 1):.1f}" fill="{colour}"/>')
        sign = "-" if value < 0 else "" if kind == "=" else "+"
        amount = f"{unit}{number(abs(value))}" if unit in ("£", "$", "€") else f"{number(abs(value))}{unit}"
        out.append(label(x + w / 2, y0 - 5, sign + amount, SIZE, "middle", 'font-weight="700"'))
        if i + 1 < len(rows):
            out.append(
                f'<line x1="{x + w:.1f}" y1="{y_of(end):.1f}" x2="{x + band:.1f}" y2="{y_of(end):.1f}" stroke="currentColor" stroke-dasharray="3 3" stroke-opacity=".6"/>'
            )
        head, y = _text_block(
            left + band * (i + 0.5), top + plot_h + 4, [name], SMALL, band - 6, "middle", 'font-weight="700"'
        )
        small, y = _text_block(
            left + band * (i + 0.5),
            y,
            [note] if note else [],
            SMALL - 1,
            band - 6,
            "middle",
            f'fill="{ctx.theme.colours["muted"]}"',
        )
        out += [head, small]
        bottom = max(bottom, y)
    out.append(
        f'<line x1="{left}" y1="{y_of(max(low, 0)):.1f}" x2="{WIDTH - right}" y2="{y_of(max(low, 0)):.1f}" stroke="currentColor"/>'
    )
    return _fig(opts, svg(WIDTH, bottom + 6, "".join(out), opts.get("title", "waterfall"), "chart"))


# ---------------------------------------------------------------------------
# buckets: what each holds, against what it can hold, with trigger lines
# ---------------------------------------------------------------------------


@block(
    "buckets",
    "Label | current | capacity | colour | value label; value label ... lines; unit=",
    "Emergency credit | 10 | 10 | amber\nNormal credit | 8.4 | 30 | green | 2 Low credit",
)
def buckets_html(code, opts, ctx):
    """Tanks side by side, each filled to its current value, with dashed lines at its thresholds."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    unit = opts.get("unit", "")
    rows = []
    for line in _lines(code):
        cells = _cells(line)
        if len(cells) < 3:
            raise PosterError(f"{ctx.where}: a buckets line is 'Label | current | capacity', not '{line}'")
        current, capacity = _number_of(cells[1], "a bucket value", ctx), _number_of(cells[2], "a bucket capacity", ctx)
        if capacity <= 0:
            raise PosterError(f"{ctx.where}: the capacity of '{cells[0]}' must be above zero")
        colour = cells[3] if len(cells) > 3 and cells[3] else None
        marks = []
        for part in cells[4].split(";") if len(cells) > 4 and cells[4] else []:
            m = re.match(r"^\s*([-\d.,£$]+)\s*(.*)$", part)
            if not m:
                raise PosterError(f"{ctx.where}: a bucket threshold is 'value label', not '{part.strip()}'")
            marks.append((_number_of(m[1], "a bucket threshold", ctx), m[2].strip()))
        rows.append((cells[0], current, capacity, ctx.theme.colour(colour, "secondary"), marks))
    if not rows:
        raise PosterError(f"{ctx.where}: a buckets block needs at least one line")
    cols = len(rows)
    slot = WIDTH / cols
    tank_w, tank_h, top = min(110, slot * 0.45), 170, 26
    out, bottom = [], top + tank_h
    money = unit in ("£", "$", "€")

    def amount(v):
        return f"{unit}{number(v)}" if money else f"{number(v)}{unit}"

    for i, (name, current, capacity, colour, marks) in enumerate(rows):
        x = slot * i + (slot - tank_w) / 2
        fill = max(0.0, min(current / capacity, 1.0))
        out.append(
            f'<rect x="{x:.1f}" y="{top + tank_h * (1 - fill):.1f}" width="{tank_w:.1f}" height="{tank_h * fill:.1f}" fill="{colour}"/>'
        )
        out.append(
            f'<rect x="{x:.1f}" y="{top}" width="{tank_w:.1f}" height="{tank_h}" fill="none" stroke="currentColor" stroke-width="2" rx="4"/>'
        )
        out.append(
            label(x + tank_w / 2, top - 8, f"{current / capacity * 100:.0f} %", SIZE, "middle", 'font-weight="700"')
        )
        for value, text in marks:
            y = top + tank_h * (1 - max(0.0, min(value / capacity, 1.0)))
            out.append(
                f'<line x1="{x - 6:.1f}" y1="{y:.1f}" x2="{x + tank_w + 6:.1f}" y2="{y:.1f}" stroke="{ctx.theme.colours["bad"]}" stroke-width="2" stroke-dasharray="5 3"/>'
            )
            out.append(
                label(
                    x + tank_w + 9,
                    y + 4,
                    f"{amount(value)} {text}".strip(),
                    SMALL,
                    extra=f'fill="{ctx.theme.colours["bad"]}"',
                )
            )
        head, y = _text_block(x + tank_w / 2, top + tank_h + 4, [name], SIZE, slot - 8, "middle", 'font-weight="700"')
        sub_, y = _text_block(
            x + tank_w / 2,
            y,
            [f"{amount(current)} of {amount(capacity)}"],
            SMALL,
            slot - 8,
            "middle",
            f'fill="{ctx.theme.colours["muted"]}"',
        )
        out += [head, sub_]
        bottom = max(bottom, y)
    return _fig(opts, svg(WIDTH, bottom + 6, "".join(out), opts.get("title", "buckets"), "chart"))


# ---------------------------------------------------------------------------
# gauge: a dial with coloured zones and a needle
# ---------------------------------------------------------------------------


@block(
    "gauge",
    "from | to | colour zone lines; value=, min=, max=, unit=, label=",
    "48.5 | 49.5 | red\n49.5 | 49.8 | amber\n49.8 | 50.2 | green\n50.2 | 51.5 | amber",
    'value=49.93 min=48.5 max=51.5 unit=" Hz"',
)
def gauge_html(code, opts, ctx):
    """A half dial from ``min`` to ``max`` with coloured zones, its ticks, and a needle at ``value``."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    for name in ("value", "min", "max"):
        if name not in opts:
            raise PosterError(f"{ctx.where}: a gauge needs value=, min= and max=")
    value, low, high = (_number_of(opts[n], f"gauge {n}", ctx) for n in ("value", "min", "max"))
    if high <= low:
        raise PosterError(f"{ctx.where}: gauge max must be above min")
    unit = opts.get("unit", "")
    angle = Linear(low, high, -90, 90)
    cx, cy, r = WIDTH / 2, 200, 170
    out = [f'<path d="{sector(cx, cy, r - 34, r, -90, 90)}" fill="{ctx.theme.colours["border"]}"/>']
    ticks = {low, high}
    for line in _lines(code):
        cells = _cells(line)
        if len(cells) < 2:
            raise PosterError(f"{ctx.where}: a gauge zone is 'from | to | colour', not '{line}'")
        a, b = (min(max(_number_of(c, "a gauge zone", ctx), low), high) for c in cells[:2])
        colour = ctx.theme.colour(cells[2] if len(cells) > 2 and cells[2] else None, "secondary")
        out.append(f'<path d="{sector(cx, cy, r - 34, r, angle(min(a, b)), angle(max(a, b)))}" fill="{colour}"/>')
        ticks |= {a, b}
    for t in sorted(ticks):
        x0, y0 = polar(cx, cy, r + 2, angle(t))
        x1, y1 = polar(cx, cy, r + 10, angle(t))
        tx, ty = polar(cx, cy, r + 24, angle(t))
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="currentColor"/>')
        out.append(label(tx, ty + 4, number(t), SMALL, "middle"))
    shown = min(max(value, low), high)
    nx, ny = polar(cx, cy, r - 12, angle(shown))
    out.append(
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{ctx.theme.colours["strong"]}" stroke-width="5" stroke-linecap="round"/>'
    )
    out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="{ctx.theme.colours["strong"]}"/>')
    out.append(label(cx, cy + 40, f"{number(value)}{unit}", 30, "middle", 'font-weight="700"'))
    bottom = cy + 48
    if opts.get("label"):
        out.append(label(cx, cy + 64, opts["label"], SIZE, "middle", f'fill="{ctx.theme.colours["muted"]}"'))
        bottom += 22
    return _fig(opts, svg(WIDTH, bottom, "".join(out), opts.get("title", opts.get("label", "gauge")), "chart"))


# ---------------------------------------------------------------------------
# dial24: the hours of a day on a clock face
# ---------------------------------------------------------------------------


def _hour(text, ctx):
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", text.strip())
    if not m or int(m[1]) > 24 or (m[2] and int(m[2]) > 59):
        raise PosterError(f"{ctx.where}: '{text}' is not a time such as 18:00")
    return int(m[1]) + int(m[2] or 0) / 60


@block(
    "dial24",
    "start | end | label | colour lines, times as 18:00 (an end before the start runs past midnight)",
    "18:00 | 09:00 | Friendly hours | green\n00:00 | 05:00 | Off-peak | blue\n16:00 | 19:00 | Peak | red",
)
def dial24_html(code, opts, ctx):
    """A 24-hour clock face with a coloured ring for each label, and a legend beside it."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    rings: dict[str, list] = {}
    for line in _lines(code):
        cells = _cells(line)
        if len(cells) < 3:
            raise PosterError(f"{ctx.where}: a dial24 line is 'start | end | label', not '{line}'")
        start, end = _hour(cells[0], ctx), _hour(cells[1], ctx)
        colour = ctx.theme.colour(cells[3] if len(cells) > 3 and cells[3] else None, "secondary")
        rings.setdefault(cells[2], []).append((start, end, colour, f"{cells[0]} to {cells[1]}"))
    if not rings:
        raise PosterError(f"{ctx.where}: a dial24 block needs at least one 'start | end | label' line")
    cx, cy, outer = 190, 190, 150
    width = max(14, min(30, 90 / len(rings)))
    out = [f'<circle cx="{cx}" cy="{cy}" r="{outer + 6}" fill="none" stroke="currentColor" stroke-opacity=".3"/>']
    legend_y = 40
    for n, (name, parts) in enumerate(rings.items()):
        r1 = outer - n * (width + 4)
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r1 - width / 2:.1f}" fill="none" stroke="currentColor" stroke-opacity=".12" stroke-width="{width:.1f}"/>'
        )
        times = []
        for start, end, colour, written in parts:
            stop = end if end > start else end + 24
            out.append(f'<path d="{sector(cx, cy, r1 - width, r1, start * 15, stop * 15)}" fill="{colour}"/>')
            times.append(written)
        colour = parts[0][2]
        out.append(f'<rect x="400" y="{legend_y - 12}" width="16" height="16" fill="{colour}"/>')
        text, legend_y = _text_block(424, legend_y - 15, [name], SIZE, 210, extra='font-weight="700"')
        when, legend_y = _text_block(
            424, legend_y - 2, [", ".join(times)], SMALL, 210, extra=f'fill="{ctx.theme.colours["muted"]}"'
        )
        out += [text, when]
        legend_y += 18
    for h in range(24):
        x0, y0 = polar(cx, cy, outer + 6, h * 15)
        x1, y1 = polar(cx, cy, outer + (14 if h % 6 == 0 else 10), h * 15)
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="currentColor"/>')
        if h % 3 == 0:
            tx, ty = polar(cx, cy, outer + 28, h * 15)
            out.append(label(tx, ty + 4, f"{h:02d}", SMALL, "middle", 'font-weight="700"' if h % 6 == 0 else ""))
    return _fig(opts, svg(WIDTH, max(cy * 2, legend_y), "".join(out), opts.get("title", "24-hour dial"), "chart"))


# ---------------------------------------------------------------------------
# rating: A to G chevrons
# ---------------------------------------------------------------------------

RATING = (
    ("A", "#008054"), ("B", "#19b459"), ("C", "#8dce46"), ("D", "#ffd500"),
    ("E", "#fcaa65"), ("F", "#ef8023"), ("G", "#e9153b"),
)  # fmt: skip


@block(
    "rating",
    "Optional band | range | colour lines (default A to G); current=, potential=, and their labels with current-label=",
    "A | 92+\nB | 81-91\nC | 69-80\nD | 55-68\nE | 39-54\nF | 21-38\nG | 1-20",
)
def rating_html(code, opts, ctx):
    """Bands as chevrons of growing length, with arrows at the ``current`` and ``potential`` bands."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    bands = []
    for line in _lines(code):
        cells = _cells(line)
        default = dict(RATING).get(cells[0].upper())
        colour = (
            ctx.theme.colour(cells[2], "secondary")
            if len(cells) > 2 and cells[2]
            else default or ctx.theme.colours["secondary"]
        )
        bands.append((cells[0], cells[1] if len(cells) > 1 else "", colour))
    bands = bands or [(name, "", colour) for name, colour in RATING]
    pointers = [
        (opts.get(k, "").strip(), opts.get(f"{k}-label", k.title())) for k in ("current", "potential") if opts.get(k)
    ]
    for band_name, _ in pointers:
        if band_name.upper() not in {b[0].upper() for b in bands}:
            raise PosterError(f"{ctx.where}: rating {band_name} is not one of its bands")
    row, gap, top = 30, 4, 28
    out = []
    pointer_x = [420, 530]
    for n, (_, text) in enumerate(pointers):
        out.append(label(pointer_x[n] + 45, 18, text, SMALL, "middle", 'font-weight="700"'))
    for i, (name, rng, colour) in enumerate(bands):
        y = top + i * (row + gap)
        w = 140 + i * 30
        out.append(f'<path d="M0,{y} L{w},{y} L{w + 15},{y + row / 2} L{w},{y + row} L0,{y + row} Z" fill="{colour}"/>')
        out.append(label(8, y + row / 2 + 5, rng, SMALL, extra='fill="#fff" font-weight="700"'))
        out.append(label(w - 6, y + row / 2 + 7, name, 20, "end", 'fill="#fff" font-weight="700"'))
        for n, (band_name, _) in enumerate(pointers):
            if band_name.upper() == name.upper():
                x = pointer_x[n]
                out.append(
                    f'<path d="M{x},{y + row / 2} L{x + 15},{y} L{x + 90},{y} L{x + 90},{y + row} L{x + 15},{y + row} Z" fill="{colour}"/>'
                )
                out.append(label(x + 52, y + row / 2 + 7, name, 20, "middle", 'fill="#fff" font-weight="700"'))
    height = top + len(bands) * (row + gap)
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "rating"), "chart"))


# ---------------------------------------------------------------------------
# gradient-scale: a colour ruler with benchmarks
# ---------------------------------------------------------------------------


@block(
    "gradient-scale",
    "value | label lines as benchmarks; from=, to=, colours= (left to right), unit=, step=",
    "65 | Eggs set\n100 | Water boils\n150 | Maillard reaction\n170 | Caramel",
)
def gradient_scale_html(code, opts, ctx):
    """A bar shading from colour to colour between ``from`` and ``to``, with pinned benchmarks above and below."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    pins = []
    for line in _lines(code):
        cells = _cells(line)
        pins.append((_number_of(cells[0], "a benchmark", ctx), cells[1] if len(cells) > 1 else ""))
    values = [v for v, _ in pins]
    low = _number_of(opts["from"], "from", ctx) if "from" in opts else min(values + [0])
    high = _number_of(opts["to"], "to", ctx) if "to" in opts else max(values + [1])
    if high <= low:
        raise PosterError(f"{ctx.where}: gradient-scale to= must be above from=")
    names = (opts.get("colours") or "blue,green,amber,red").split(",")
    stops = [ctx.theme.colour(name.strip()) for name in names]
    gid = _id("g", code + opts.get("colours", ""))
    left, right = 20, WIDTH - 20
    x_of = Linear(low, high, left, right)
    bar_y, bar_h = 70, 22
    out = [
        f'<defs><linearGradient id="{gid}">'
        + "".join(f'<stop offset="{n / max(len(stops) - 1, 1):.3f}" stop-color="{c}"/>' for n, c in enumerate(stops))
        + "</linearGradient></defs>",
        f'<rect x="{left}" y="{bar_y}" width="{right - left}" height="{bar_h}" rx="4" fill="url(#{gid})"/>',
    ]
    step = _number_of(opts["step"], "step", ctx) if "step" in opts else (high - low) / 5
    unit = opts.get("unit", "")
    for v in Linear(low, high, left, right).ticks(step):
        out.append(
            f'<line x1="{x_of(v):.1f}" y1="{bar_y + bar_h}" x2="{x_of(v):.1f}" y2="{bar_y + bar_h + 6}" stroke="currentColor"/>'
        )
        out.append(label(x_of(v), bar_y + bar_h + 19, f"{number(round(v, 9))}{unit}", SMALL, "middle"))
    ups = spread([x_of(v) for v, _ in pins[::2]], 120, left + 50, right - 50)
    downs = spread([x_of(v) for v, _ in pins[1::2]], 120, left + 50, right - 50)
    for n, (value, text) in enumerate(pins):
        x = x_of(min(max(value, low), high))
        above = n % 2 == 0
        tx = (ups if above else downs)[n // 2]
        y_text = 16 if above else bar_y + bar_h + 46
        line_end = bar_y - 2 if above else bar_y + bar_h + 26
        out.append(
            f'<path d="M{tx:.1f},{y_text + (12 if above else -14):.1f} L{x:.1f},{line_end:.1f}" stroke="currentColor" fill="none"/>'
        )
        out.append(
            f'<circle cx="{x:.1f}" cy="{bar_y + bar_h / 2:.1f}" r="5" fill="#fff" stroke="currentColor" stroke-width="2"/>'
        )
        out.append(label(tx, y_text, f"{number(value)}{unit}", SMALL, "middle", 'font-weight="700"'))
        out.append(
            label(
                tx, y_text + 11 if above else y_text + 14, text, SMALL, "middle", f'fill="{ctx.theme.colours["muted"]}"'
            )
        )
    return _fig(opts, svg(WIDTH, bar_y + bar_h + 70, "".join(out), opts.get("title", "scale"), "chart"))


# ---------------------------------------------------------------------------
# logscale: orders of magnitude, each power of ten the same distance apart
# ---------------------------------------------------------------------------

_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


@block(
    "logscale",
    "value | label | colour lines, values such as 1e-9; from=, to= (powers of ten, such as 1e-9 and 1), unit=",
    "1e-9 | L1 cache\n1e-7 | Main memory\n1.5e-4 | SSD read\n1e-2 | Disk seek\n1.5e-1 | Packet to another continent",
)
def logscale_html(code, opts, ctx):
    """A ruler of powers of ten, with flags above and below it at each value."""
    WIDTH = _width(opts, ctx, 960)  # noqa: N806
    pins = []
    for line in _lines(code):
        cells = _cells(line)
        value = _number_of(cells[0], "a logscale value", ctx)
        if value <= 0:
            raise PosterError(f"{ctx.where}: a logscale value must be above zero, not '{cells[0]}'")
        colour = cells[2] if len(cells) > 2 and cells[2] else None
        pins.append((value, cells[1] if len(cells) > 1 else "", ctx.theme.colour(colour, "secondary")))
    if not pins:
        raise PosterError(f"{ctx.where}: a logscale block needs at least one 'value | label' line")
    values = [v for v, _, _ in pins]
    low = _number_of(opts["from"], "from", ctx) if "from" in opts else 10 ** math.floor(math.log10(min(values)))
    high = _number_of(opts["to"], "to", ctx) if "to" in opts else 10 ** math.ceil(math.log10(max(values)) + 1e-9)
    if high <= low:
        high = low * 10
    left, right, axis = 30, WIDTH - 30, 130
    x_of = Log10(low, high, left, right)
    unit = opts.get("unit", "")
    out = [f'<line x1="{left}" y1="{axis}" x2="{right}" y2="{axis}" stroke="currentColor" stroke-width="2"/>']
    for t in x_of.ticks():
        x = x_of(t)
        k = round(math.log10(t))
        out.append(f'<line x1="{x:.1f}" y1="{axis - 6}" x2="{x:.1f}" y2="{axis + 6}" stroke="currentColor"/>')
        out.append(label(x, axis + 21, f"10{str(k).translate(_SUPERSCRIPT)}{unit}", SMALL, "middle"))
    order = sorted(range(len(pins)), key=lambda i: pins[i][0])
    above = [i for n, i in enumerate(order) if n % 2 == 0]
    below = [i for n, i in enumerate(order) if n % 2 == 1]
    out_rows = {}
    for group, y_text, up in ((above, 18, True), (below, axis + 56, False)):
        xs = spread([x_of(pins[i][0]) for i in group], 118, left + 55, right - 55)
        for i, tx in zip(group, xs):
            out_rows[i] = (tx, y_text, up)
    for i, (value, text, colour) in enumerate(pins):
        x = x_of(min(max(value, low), high))
        tx, y_text, up = out_rows[i]
        lines = wrap(text, 112, SMALL)[:3]
        if up:
            join = y_text + len(lines) * 14 + 2
            out.append(f'<path d="M{tx:.1f},{join:.1f} L{x:.1f},{axis - 8}" stroke="{colour}" fill="none"/>')
        else:
            join = y_text - 12
            out.append(f'<path d="M{tx:.1f},{join:.1f} L{x:.1f},{axis + 8}" stroke="{colour}" fill="none"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{axis}" r="5" fill="{colour}"/>')
        for n, line in enumerate(lines):
            out.append(label(tx, y_text + 10 + n * 14, line, SMALL, "middle", 'font-weight="700"' if n == 0 else ""))
    return _fig(opts, svg(WIDTH, axis + 110, "".join(out), opts.get("title", "log scale"), "chart"))


# ---------------------------------------------------------------------------
# spectrum: light by wavelength, the whole electromagnetic spectrum, stars by colour, and radio channels
# ---------------------------------------------------------------------------


def wavelength_to_rgb(nm: float) -> str:
    """The colour of light of wavelength ``nm`` (380 to 750 nanometres), as ``#rrggbb``. Outside, black.

    The usual approximation of Dan Bruton: a hue by wavelength, dimmed towards both ends of what the eye sees.
    """
    if nm < 380 or nm > 750:
        return "#000000"
    if nm < 440:
        r, g, b = -(nm - 440) / 60, 0.0, 1.0
    elif nm < 490:
        r, g, b = 0.0, (nm - 440) / 50, 1.0
    elif nm < 510:
        r, g, b = 0.0, 1.0, -(nm - 510) / 20
    elif nm < 580:
        r, g, b = (nm - 510) / 70, 1.0, 0.0
    elif nm < 645:
        r, g, b = 1.0, -(nm - 645) / 65, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    fade = 0.3 + 0.7 * (nm - 380) / 40 if nm < 420 else 0.3 + 0.7 * (750 - nm) / 50 if nm > 700 else 1.0
    return "#" + "".join(f"{round(255 * (c * fade) ** 0.8):02x}" for c in (r, g, b))


def _rainbow(gid, low=380, high=750):
    stops = "".join(
        f'<stop offset="{(nm - low) / (high - low):.3f}" stop-color="{wavelength_to_rgb(nm)}"/>'
        for nm in range(low, high + 1, 10)
    )
    return f'<linearGradient id="{gid}">{stops}</linearGradient>'


EM_BANDS = (  # name, shortest and longest wavelength in metres, colour
    ("Gamma", 1e-14, 1e-11, "#5b2a86"), ("X-ray", 1e-11, 1e-8, "#3f74b8"), ("UV", 1e-8, 3.8e-7, "#6d28d9"),
    ("Visible", 3.8e-7, 7.5e-7, None), ("Infrared", 7.5e-7, 1e-3, "#b4540a"),
    ("Microwave", 1e-3, 1e-1, "#8a3d08"), ("Radio", 1e-1, 1e3, "#4a4f5c"),
)  # fmt: skip

STELLAR = (  # class, colour, temperature
    ("O", "#9bb0ff", "30,000 K+"), ("B", "#aabfff", "10,000 K"), ("A", "#cad7ff", "7,500 K"),
    ("F", "#f8f7ff", "6,000 K"), ("G", "#fff4ea", "5,200 K"), ("K", "#ffd2a1", "3,700 K"), ("M", "#ffcc6f", "2,400 K"),
)  # fmt: skip

SPECTRUM_MODES = ("visible", "absorption", "emission", "em", "stellar", "channels")


@block(
    "spectrum",
    "mode=visible|absorption|emission|em|stellar|channels; nm | label lines (channels: name | centre | width | colour); shift= (redshift z)",
    "656.3 | Hα\n589 | Na D\n486.1 | Hβ\n434 | Hγ",
)
def spectrum_html(code, opts, ctx):
    mode = opts.get("mode", "visible").lower()
    if mode not in SPECTRUM_MODES:
        raise PosterError(f"{ctx.where}: spectrum mode must be one of {', '.join(SPECTRUM_MODES)}, not '{mode}'")
    draw = {"em": _spectrum_em, "stellar": _spectrum_stellar, "channels": _spectrum_channels}.get(mode, _spectrum_light)
    return _fig(opts, draw(code, opts, ctx, mode))


def _spectrum_light(code, opts, ctx, mode):
    """The visible band, plain, with dark absorption lines, or with bright emission lines on black."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    lines = []
    for line in _lines(code):
        cells = _cells(line)
        nm = _number_of(cells[0], "a wavelength in nm", ctx)
        lines.append((nm, cells[1] if len(cells) > 1 else ""))
    low, high = 380, 750
    left, right = 20, WIDTH - 20
    x_of = Linear(low, high, left, right)
    gid = _id("s", code + mode)
    shift = _number_of(opts["shift"], "shift", ctx) if "shift" in opts else None
    tracks = [(0.0, "")] + ([(shift, f"z = {number(shift)}")] if shift is not None else [])
    out = [f"<defs>{_rainbow(gid)}</defs>"]
    top, strip = 44, 46
    for n, (z, name) in enumerate(tracks):
        y = top + n * (strip + 26)
        fill = "#000" if mode == "emission" else f"url(#{gid})"
        out.append(f'<rect x="{left}" y="{y}" width="{right - left}" height="{strip}" fill="{fill}"/>')
        if name:
            out.append(label(left, y - 6, name, SMALL, extra='font-weight="700"'))
        for nm, _ in lines:
            seen = nm * (1 + z)
            if not low <= seen <= high:
                continue
            x = x_of(seen)
            colour = wavelength_to_rgb(seen) if mode == "emission" else "#000"
            width = 3 if mode == "emission" else 2.2
            if mode != "visible" or n == 0:
                out.append(f'<rect x="{x - width / 2:.1f}" y="{y}" width="{width}" height="{strip}" fill="{colour}"/>')
    # Labels of the lines above the first strip
    xs = spread([x_of(nm) for nm, _ in lines], 64, left + 20, right - 20)
    for (nm, text), tx in zip(lines, xs):
        out.append(
            f'<path d="M{tx:.1f},{top - 13} L{x_of(nm):.1f},{top - 1}" stroke="currentColor" fill="none" stroke-opacity=".6"/>'
        )
        out.append(label(tx, top - 26, text, SMALL, "middle", 'font-weight="700"'))
        out.append(label(tx, top - 15, f"{number(nm)}", SMALL - 2, "middle", f'fill="{ctx.theme.colours["muted"]}"'))
    if shift is not None and lines:
        nm = lines[0][0]
        y0, y1 = top + strip + 2, top + strip + 24
        out.append(
            f'<path d="M{x_of(nm):.1f},{y0} L{x_of(min(nm * (1 + shift), high)):.1f},{y1}" stroke="currentColor" fill="none" marker-end="none" stroke-dasharray="3 2"/>'
        )
    bottom = top + len(tracks) * (strip + 26) - 26
    for nm in range(400, 751, 50):
        out.append(
            f'<line x1="{x_of(nm):.1f}" y1="{bottom}" x2="{x_of(nm):.1f}" y2="{bottom + 6}" stroke="currentColor"/>'
        )
        out.append(label(x_of(nm), bottom + 19, f"{nm} nm", SMALL, "middle"))
    return svg(WIDTH, bottom + 28, "".join(out), opts.get("title", "spectrum"), "chart")


def _spectrum_em(code, opts, ctx, mode):
    """The whole spectrum by wavelength on a log scale, with the visible band opened out under it."""
    WIDTH = _width(opts, ctx, 960)  # noqa: N806
    left, right, top, strip = 20, WIDTH - 20, 18, 40
    x_of = Log10(1e-14, 1e3, left, right)
    gid = _id("e", code)
    out = [f"<defs>{_rainbow(gid)}</defs>"]
    for name, lo, hi, colour in EM_BANDS:
        x0, x1 = x_of(lo), x_of(hi)
        fill = f"url(#{gid})" if colour is None else colour
        out.append(f'<rect x="{x0:.1f}" y="{top}" width="{x1 - x0:.1f}" height="{strip}" fill="{fill}"/>')
        if colour is not None:
            out.append(
                label((x0 + x1) / 2, top + strip / 2 + 5, name, SMALL, "middle", 'fill="#fff" font-weight="700"')
            )
    for k in range(-14, 4, 2):
        x = x_of(10.0**k)
        out.append(f'<line x1="{x:.1f}" y1="{top + strip}" x2="{x:.1f}" y2="{top + strip + 5}" stroke="currentColor"/>')
        out.append(label(x, top + strip + 18, f"10{str(k).translate(_SUPERSCRIPT)} m", SMALL - 1, "middle"))
    # The visible band, opened out: a wedge from its slit to a full-width rainbow
    v0, v1 = x_of(3.8e-7), x_of(7.5e-7)
    wedge_bottom = top + strip + 70
    out.append(
        f'<path d="M{v0:.1f},{top + strip} L{v1:.1f},{top + strip} L{right},{wedge_bottom} L{left},{wedge_bottom} Z" fill="currentColor" fill-opacity=".08"/>'
    )
    out.append(f'<rect x="{left}" y="{wedge_bottom}" width="{right - left}" height="30" fill="url(#{gid})"/>')
    x_nm = Linear(380, 750, left, right)
    for nm in range(400, 751, 50):
        out.append(label(x_nm(nm), wedge_bottom + 46, f"{nm} nm", SMALL - 1, "middle"))
    marks = []
    for line in _lines(code):
        cells = _cells(line)
        marks.append((_number_of(cells[0], "a wavelength in metres", ctx), cells[1] if len(cells) > 1 else ""))
    xs = spread([x_of(m) for m, _ in marks], 90, left + 40, right - 40)
    bottom = wedge_bottom + 56
    for (metres, text), tx in zip(marks, xs):
        out.append(
            f'<line x1="{x_of(metres):.1f}" y1="{top - 2}" x2="{x_of(metres):.1f}" y2="{top + strip}" stroke="#fff" stroke-width="2"/>'
        )
        out.append(label(tx, bottom + 12, text, SMALL, "middle", 'font-weight="700"'))
    if marks:
        bottom += 18
    return svg(WIDTH, bottom, "".join(out), opts.get("title", "electromagnetic spectrum"), "chart")


def _spectrum_stellar(code, opts, ctx, mode):
    """The colours of stars from O to M, with their surface temperatures."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    left, right, top, strip = 20, WIDTH - 20, 10, 46
    gid = _id("t", code)
    stops = "".join(
        f'<stop offset="{n / (len(STELLAR) - 1):.3f}" stop-color="{c}"/>' for n, (_, c, _) in enumerate(STELLAR)
    )
    out = [f'<defs><linearGradient id="{gid}">{stops}</linearGradient></defs>']
    out.append(
        f'<rect x="{left}" y="{top}" width="{right - left}" height="{strip}" fill="url(#{gid})" stroke="currentColor" stroke-opacity=".3"/>'
    )
    step = (right - left) / (len(STELLAR) - 1)
    for n, (name, _, temperature) in enumerate(STELLAR):
        x = left + n * step
        out.append(
            label(
                min(max(x, left + 12), right - 12),
                top + strip / 2 + 7,
                name,
                20,
                "middle",
                'fill="#1d1f27" font-weight="700"',
            )
        )
        out.append(label(min(max(x, left + 30), right - 30), top + strip + 18, temperature, SMALL, "middle"))
    return svg(WIDTH, top + strip + 28, "".join(out), opts.get("title", "stellar classes"), "chart")


def _spectrum_channels(code, opts, ctx, mode):
    """Radio channels as lobes on a frequency axis: ``name | centre | width | colour`` in the same unit."""
    WIDTH = _width(opts, ctx)  # noqa: N806
    rows = []
    for line in _lines(code):
        cells = _cells(line)
        if len(cells) < 3:
            raise PosterError(f"{ctx.where}: a channel line is 'name | centre | width', not '{line}'")
        centre, width = _number_of(cells[1], "a channel centre", ctx), _number_of(cells[2], "a channel width", ctx)
        rows.append(
            (cells[0], centre, width, ctx.theme.colour(cells[3] if len(cells) > 3 and cells[3] else None, "secondary"))
        )
    if not rows:
        raise PosterError(f"{ctx.where}: a channels spectrum needs at least one 'name | centre | width' line")
    low = _number_of(opts["from"], "from", ctx) if "from" in opts else min(c - w / 2 for _, c, w, _ in rows)
    high = _number_of(opts["to"], "to", ctx) if "to" in opts else max(c + w / 2 for _, c, w, _ in rows)
    unit = opts.get("unit", " MHz")
    ticks = Linear(low, high, 0, 1).ticks((high - low) / 5)
    # a tick's value is written centred under it, so the ends leave room for half of the widest one
    margin = max([20] + [text_width(f"{number(round(v, 6))}{unit}", SMALL) / 2 + 4 for v in ticks])
    left, right, base = margin, WIDTH - margin, 170
    x_of = Linear(low, high, left, right)
    out = []
    widest = max(w for _, _, w, _ in rows)
    for name, centre, width, colour in rows:
        x0, x1 = x_of(centre - width / 2), x_of(centre + width / 2)
        h = 40 + 110 * (width / widest)
        out.append(
            f'<path d="M{x0:.1f},{base} C{x0:.1f},{base - h:.1f} {x1:.1f},{base - h:.1f} {x1:.1f},{base} Z" fill="{colour}" fill-opacity=".45" stroke="{colour}" stroke-width="2"/>'
        )
        out.append(label((x0 + x1) / 2, base - h * 0.75 - 4, name, SMALL, "middle", 'font-weight="700"'))
    out.append(f'<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="currentColor" stroke-width="2"/>')
    for v in ticks:
        out.append(f'<line x1="{x_of(v):.1f}" y1="{base}" x2="{x_of(v):.1f}" y2="{base + 6}" stroke="currentColor"/>')
        out.append(label(x_of(v), base + 20, f"{number(round(v, 6))}{unit}", SMALL, "middle"))
    return svg(WIDTH, base + 30, "".join(out), opts.get("title", "channels"), "chart")
