"""The blocks of a poster: fenced code that becomes something other than code.

Diagram fences are drawn by the tool container. ``cards``, ``lcd``, ``segments``, ``flow``, ``lanes``,
``figure``, ``timeline``, ``chart`` and ``qr`` are HTML and SVG made here, in the theme's colours.
"""

from __future__ import annotations

import base64
import html
import json
import logging
import math
import mimetypes
import re
import shlex
from pathlib import Path

import segno
from markdown_it import MarkdownIt

from py_doc.diagrams import BY_FENCE, DiagramError
from py_doc.diagrams.render import draw_cached, with_mermaid_config
from py_doc import poster_barcode, poster_qr
from py_doc.errors import ConversionError, ToolFailed
from py_doc.poster_themes import Theme

logger = logging.getLogger(__name__)

MD = MarkdownIt("commonmark").enable("table")
_validate_link = MD.validateLink
# markdown-it allows only GIF, PNG, JPEG and WebP data addresses. An SVG picture is embedded as one too, and
# shown in an <img>, where it cannot run scripts.
MD.validateLink = lambda url: url.strip().lower().startswith("data:image/svg+xml;") or _validate_link(url)
CHART_KINDS = ("column", "bar", "line")
SERIES_COLOURS = ("secondary", "accent", "primary", "good", "bad", "muted")


class PosterError(ConversionError):
    """The Markdown cannot be made into a poster."""


def mermaid_init(theme):
    """Front matter that gives Mermaid the poster's theme. Skipped if the diagram has its own configuration.

    Front matter, not a ``%%{init}%%`` line: Mermaid drops an init line whose font list has quotes in it.
    """
    c = theme.colours
    variables = {
        "fontFamily": theme.fonts["body"], "fontSize": "16px", "primaryColor": c["diagram-fill"],
        "primaryBorderColor": c["primary"], "primaryTextColor": "#1d1f27", "lineColor": c["primary"],
        "secondaryColor": "#f3f3f7", "tertiaryColor": "#ffffff", "clusterBkg": "#f3f6fb",
        "clusterBorder": c["secondary"], "edgeLabelBackground": "#ffffff",
    }  # fmt: skip
    return "---\nconfig: " + json.dumps({"theme": "base", "themeVariables": variables}) + "\n---\n"

TOK = re.compile(r"\[([^\]|]+)(?:\|([^\]]+))?\]|-(?:([^>\[\]]*?)-)?>")



class Ctx:
    """Per-build state shared by all blocks."""

    def __init__(self, base, runtime, theme=None, render=None, where=""):
        self.base = base
        self.theme = theme or Theme()
        self.render = render  # Markdown to HTML, for the notes under a figure
        self.where = where  # the Markdown file, for messages
        self._connect, self._runtime = runtime, None
        self.n = 0
        self.failed = 0
        self.mermaid = None  # diagrams.mermaid of py-doc.yml
        self.stylesheet = None  # the web fonts the page links, not embedded

    def runtime(self):
        """The tool container, started on the first diagram, so a poster without one needs no Docker."""
        if self._runtime is None:
            self._runtime = self._connect()
        return self._runtime


def esc(s):
    return html.escape(s, quote=True)


def inline(s):
    return MD.renderInline(s)


def parse_opts(info):
    try:
        toks = shlex.split(info)
    except ValueError:
        toks = info.split()
    return {k.lower(): v for k, _, v in (t.partition("=") for t in toks)}


# ---------------------------------------------------------------------------
# Diagram fences -> the tool container -> embedded image
# ---------------------------------------------------------------------------

def render_diagram(lang, code, ctx):
    ctx.n += 1
    if lang == "mermaid" and "%%{init" not in code and not code.lstrip().startswith("---"):
        code = mermaid_init(ctx.theme) + code
    if lang == "mermaid":
        code = with_mermaid_config(code, ctx.mermaid)
    renderer = BY_FENCE[lang]
    kind = "svg" if "svg" in renderer.kinds else "png"  # SVG where the tool can write it: it prints sharp at any size
    return draw_cached(ctx.runtime(), renderer, code, kind, False, ctx.base)


def diagram_html(lang, code, opts, ctx):
    try:
        path = render_diagram(lang, code, ctx)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode()
        return f'<img alt="{esc(opts.get("alt", lang + " diagram"))}" src="data:{mime};base64,{data}">'
    except (ToolFailed, DiagramError) as exc:  # a broken diagram must not stop the poster
        ctx.failed += 1
        lines = (getattr(exc, "output", None) or str(exc) or type(exc).__name__).strip().splitlines()
        errs = [line.strip() for line in lines if "error" in line.lower()]
        msg = (errs or lines or [type(exc).__name__])[0 if errs else -1].strip()[:160]
        logger.warning(f"{lang} diagram not rendered: {msg}")
        return (f'<pre><code>{esc(code)}</code></pre>'
                f'<p class="caption">{esc(lang)} diagram could not be rendered: {esc(msg)}</p>')


# ---------------------------------------------------------------------------
# Poster blocks: cards, lcd, and the figure kinds (segments, flow, lanes)
# ---------------------------------------------------------------------------

def cards_html(code, opts, ctx):
    rows = [[c.strip() for c in line.split("|")] for line in code.splitlines() if line.strip()]
    style = opts.get("style", "title")
    cols = int(opts.get("cols", min(len(rows), 4) or 1))
    out = ""
    for r in rows:
        head, text, colour = ("", r[0], None) if len(r) == 1 else (r[0], r[1], r[2] if len(r) > 2 else None)
        top = f' style="border-top:4px solid {ctx.theme.colour(colour, "secondary")}"' if style == "top" else ""
        h = f'<div class="ch">{inline(head)}</div>' if head else ""
        out += f'<div class="card {esc(style)}"{top}>{h}<div class="ct">{inline(text)}</div></div>'
    return f'<div class="cards" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


def lcd_html(code, opts, ctx):
    """Screens separated by blank lines, in ``cols=`` columns (default: up to 3) and as many rows as they need.
    A line starting ``--`` is the screen's caption."""
    screens = [[]]
    for line in code.splitlines():
        if line.strip():
            screens[-1].append(line)
        elif screens[-1]:
            screens.append([])
    out = ""
    for s in screens:
        if not s:
            continue
        shown = "".join(f"<div>{esc(x)}</div>" for x in s if not x.startswith("--"))
        cap = " ".join(x[2:].strip() for x in s if x.startswith("--"))
        out += (f'<div class="lcd"><div class="scr">{shown}</div>'
                + (f'<div class="cap">{esc(cap)}</div>' if cap else "") + "</div>")
    count = sum(1 for s in screens if s)
    cols = _whole(opts, "cols", min(count, 3) or 1, ctx)
    return f'<div class="lcds" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


def kv_split(code):
    meta, rest = {}, []
    for line in code.splitlines():
        m = re.match(r"^(title|height):\s*(.*)$", line.strip(), re.I)
        if m:
            meta[m.group(1).lower()] = m.group(2)
        else:
            rest.append(line)
    return meta, rest


def segments_part(code, ctx):
    meta, lines = kv_split(code)
    rows, notes = [], []
    for line in lines:
        (rows if re.match(r"^\s*\d+(\.\d+)?\s*\|", line) else notes).append(line)
    cells, detailed = "", False
    for r in (c for c in ([x.strip() for x in line.split("|")] for line in rows)):
        label = r[1] if len(r) > 1 else ""
        det = r[2] if len(r) > 2 else ""
        detailed = detailed or bool(det)
        cells += (f'<div style="flex:{r[0]};background:{ctx.theme.colour(r[3] if len(r) > 3 else None)}">{inline(label)}'
                  + (f"<small>{inline(det)}</small>" if det else "") + "</div>")
    h = meta.get("height") or ("64" if detailed else "36")
    return meta.get("title"), f'<div class="bar" style="min-height:{h}px">{cells}</div>', "\n".join(notes).strip()


def flow_part(code, ctx):
    meta, lines = kv_split(code)
    rows, notes = "", []
    for line in lines:
        if "->" not in line or "[" not in line:
            notes.append(line)
            continue
        parts = ""
        for m in TOK.finditer(line):
            if m.group(1) is not None:
                if m.group(2):
                    parts += f'<div class="node" style="background:{ctx.theme.colour(m.group(2))}">{inline(m.group(1))}</div>'
                else:
                    parts += f'<div class="node out">{inline(m.group(1))}</div>'
            else:
                label = (m.group(3) or "").strip()
                parts += f'<div class="arr">{inline(label) + "<br>" if label else ""}<i>→</i></div>'
        rows += f'<div class="flow">{parts}</div>'
    return meta.get("title"), rows, "\n".join(notes).strip()


def lanes_part(code, ctx):
    meta, lines = kv_split(code)
    lanes, notes = "", []
    for line in lines:
        if "|" not in line:
            notes.append(line)
            continue
        label, *cells = [c.strip() for c in line.split("|")]
        cells = [c.replace("-", "‑") for c in cells]  # non-breaking hyphen keeps "wake-up" whole
        inner = "".join(
            f'<div class="cell fill">{inline(c[1:].strip())}</div>' if c.startswith("*")
            else f'<div class="cell dash">{inline(c)}</div>' for c in cells)
        lanes += f'<div class="lane"><b>{esc(label)}</b><div class="cells">{inner}</div></div>'
    return meta.get("title"), f'<div class="lanes">{lanes}</div>', "\n".join(notes).strip()


FIG_KINDS = {"segments": segments_part, "flow": flow_part, "lanes": lanes_part}


def figure_html(parts, ctx):
    out = ""
    for title, inner, notes in parts:
        out += f'<div class="fig-title">{esc(title)}</div>' if title else ""
        out += inner
        out += f'<div class="fig-notes">{ctx.render(notes, ctx)}</div>' if notes else ""
    return f'<div class="fig">{out}</div>'


def timeline_html(code, opts, ctx):
    """``date | label | detail | colour`` lines as milestones, in a row or (``vertical``) a column."""
    items = ""
    for line in (line for line in code.splitlines() if line.strip()):
        cells = [c.strip() for c in line.split("|")]
        date, label = cells[0], cells[1] if len(cells) > 1 else ""
        detail = cells[2] if len(cells) > 2 else ""
        colour = ctx.theme.colour(cells[3] if len(cells) > 3 else None, "accent")
        items += (f'<div class="tl-item"><i style="background:{colour}"></i><b>{inline(date)}</b><span>{inline(label)}</span>'
                  + (f"<small>{inline(detail)}</small>" if detail else "") + "</div>")
    return f'<div class="timeline{" vertical" if "vertical" in opts else ""}">{items}</div>'


def _number(value):
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:g}"


def _nice(value):
    """The round number (1, 2, 2.5 or 5 times a power of ten) at or above ``value``, for an axis."""
    if value <= 0:
        return 0.0
    power = 10 ** math.floor(math.log10(value))
    return next(m * power for m in (1, 2, 2.5, 5, 10) if value <= m * power + 1e-9)


def _option(opts, name, choices, default, ctx):
    value = opts.get(name, default).lower()
    if value not in choices:
        raise PosterError(f"{ctx.where}: chart {name} must be one of {', '.join(choices)}, not '{value}'")
    return value


def _float(opts, name, ctx):
    try:
        return float(opts[name])
    except ValueError:
        raise PosterError(f"{ctx.where}: chart {name} must be a number") from None


def chart_html(code, opts, ctx):
    """A ``column``, ``bar`` or ``line`` chart as SVG: ``label | value | value ...`` lines, ``series:`` names them."""
    kind = opts.get("type", "column").lower()
    if kind not in CHART_KINDS:
        raise PosterError(f"{ctx.where}: chart type must be one of {', '.join(CHART_KINDS)}, not '{kind}'")
    line_only = [name for name in ("min", "markers", "area", "dashed") if name in opts and kind != "line"]
    if line_only:
        reason = " (a bar that does not start at zero misleads)" if line_only[0] == "min" else ""
        raise PosterError(f"{ctx.where}: chart {line_only[0]} is only for a line chart{reason}")
    shown = _option(opts, "values", ("all", "last", "none"), "none" if kind == "line" else "all", ctx)
    markers = _option(opts, "markers", ("yes", "no"), "yes", ctx) == "yes"
    area = _option(opts, "area", ("yes", "no"), "no", ctx) == "yes"
    series, rows = [], []
    for line in (line.strip() for line in code.splitlines() if line.strip()):
        if line.lower().startswith("series:"):
            series = [name.strip() for name in line.split(":", 1)[1].split(",")]
            continue
        label, *values = [c.strip() for c in line.split("|")]
        try:
            rows.append((label, [float(v) for v in values]))
        except ValueError:
            raise PosterError(f"{ctx.where}: chart line '{line}' needs numbers after the label") from None
        if not values:
            raise PosterError(f"{ctx.where}: chart line '{line}' has no value")
    if not rows:
        raise PosterError(f"{ctx.where}: a chart needs at least one 'label | value' line")
    count = max(len(values) for _, values in rows)
    names = opts.get("colours", "").split(",") if opts.get("colours") else SERIES_COLOURS
    colours = [ctx.theme.colour(names[i % len(names)].strip()) for i in range(count)]
    unit = opts.get("unit", "")
    dashed = {name.strip().lower() for name in opts.get("dashed", "").split(",") if name.strip()}
    dashed = {j for j in range(count) if (series[j].lower() if j < len(series) else str(j + 1)) in dashed or str(j + 1) in dashed}
    values = [v for _, vs in rows for v in vs]
    low = _float(opts, "min", ctx) if "min" in opts else -_nice(-min(values)) if min(values) < 0 else 0.0
    high = _float(opts, "max", ctx) if "max" in opts else _nice(max(values)) or 1.0
    if high <= low:
        raise PosterError(f"{ctx.where}: chart max ({_number(high)}) must be above min ({_number(low)})")
    span = high - low
    step = _float(opts, "step", ctx) if "step" in opts else span / 4
    if step <= 0 or span / step > 20:
        raise PosterError(f"{ctx.where}: chart step must be above zero, with no more than 20 steps from min to max")
    axis = opts.get("axis", "")
    legend = 24 if len(series) > 1 else 0
    width = 640
    natural = 16 + legend + len(rows) * max(30, 16 * count + 12) if kind == "bar" else 300
    height = int(opts["height"]) if opts.get("height", "").isdigit() else natural
    text = 'font-size="13" fill="currentColor"'
    out = []
    if kind == "bar":
        left, top, right, bottom = 140, 8 + legend, 60, 8 + (20 if axis else 0)
        plot_w, band = width - left - right, (height - top - bottom) / len(rows)
        x0 = left + (0 - low) / span * plot_w
        for i, (label, vs) in enumerate(rows):
            y = top + i * band
            out.append(f'<text x="{left - 8}" y="{y + band / 2 + 4:.1f}" text-anchor="end" {text}>{esc(label)}</text>')
            thick = band * 0.7 / len(vs)
            for j, v in enumerate(vs):
                x1 = left + (v - low) / span * plot_w
                yy = y + band * 0.15 + j * thick
                out.append(f'<rect x="{min(x0, x1):.1f}" y="{yy:.1f}" width="{abs(x1 - x0):.1f}" height="{thick:.1f}" fill="{colours[j]}"/>')
                if shown == "all" or shown == "last" and i == len(rows) - 1:
                    out.append(f'<text x="{max(x0, x1) + 4:.1f}" y="{yy + thick / 2 + 4:.1f}" {text}>{_number(v)}{esc(unit)}</text>')
        out.append(f'<line x1="{x0:.1f}" y1="{top}" x2="{x0:.1f}" y2="{height - bottom}" stroke="currentColor"/>')
        if axis:
            out.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 2}" text-anchor="middle" {text}>{esc(axis)}</text>')
    else:
        left, top, right, bottom = 52 + (22 if axis else 0), 12 + legend, 12, 30
        plot_w, plot_h = width - left - right, height - top - bottom

        def y_of(v):
            return top + plot_h - (v - low) / span * plot_h

        for n in range(round(span / step) + 1):
            v = low + step * n
            out.append(f'<line x1="{left}" y1="{y_of(v):.1f}" x2="{width - right}" y2="{y_of(v):.1f}" stroke="currentColor" stroke-opacity=".25"/>')
            out.append(f'<text x="{left - 6}" y="{y_of(v) + 4:.1f}" text-anchor="end" {text}>{_number(round(v, 9))}</text>')
        if axis:
            middle = top + plot_h / 2
            out.append(f'<text x="14" y="{middle:.1f}" transform="rotate(-90 14 {middle:.1f})" text-anchor="middle" {text}>{esc(axis)}</text>')
        band = plot_w / len(rows)
        for i, (label, _) in enumerate(rows):
            out.append(f'<text x="{left + band * (i + 0.5):.1f}" y="{height - 10}" text-anchor="middle" {text}>{esc(label)}</text>')
        if kind == "column":
            for i, (_, vs) in enumerate(rows):
                thick = band * 0.7 / len(vs)
                for j, v in enumerate(vs):
                    x = left + band * i + band * 0.15 + j * thick
                    y1, y0 = y_of(v), y_of(0)
                    out.append(f'<rect x="{x:.1f}" y="{min(y0, y1):.1f}" width="{thick:.1f}" height="{abs(y0 - y1):.1f}" fill="{colours[j]}"/>')
                    if shown == "all" or shown == "last" and i == len(rows) - 1:
                        out.append(f'<text x="{x + thick / 2:.1f}" y="{min(y0, y1) - 4:.1f}" text-anchor="middle" {text}>{_number(v)}{esc(unit)}</text>')
        else:
            placed: dict[float, list[float]] = {}  # the value labels at each point across, so two do not overlap
            for j in range(count):
                points = [(left + band * (i + 0.5), y_of(vs[j]), vs[j]) for i, (_, vs) in enumerate(rows) if j < len(vs)]
                path = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
                if area:
                    base = y_of(max(low, 0)) if low < 0 < high else y_of(low)
                    out.append(f'<polygon points="{points[0][0]:.1f},{base:.1f} {path} {points[-1][0]:.1f},{base:.1f}" fill="{colours[j]}" fill-opacity=".15"/>')
                dash = ' stroke-dasharray="10 6"' if j in dashed else ""
                out.append(f'<polyline points="{path}" fill="none" stroke="{colours[j]}" stroke-width="3"{dash}/>')
                if markers:
                    out += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colours[j]}"/>' for x, y, _ in points]
                for n, (x, y, v) in enumerate(points):
                    if shown == "all" or shown == "last" and n == len(points) - 1:
                        at = y - 9 if all(abs(y - 9 - other) >= 16 for other in placed.get(x, [])) else y + 21
                        placed.setdefault(x, []).append(at)
                        out.append(f'<text x="{x:.1f}" y="{at:.1f}" text-anchor="middle" {text}>{_number(v)}{esc(unit)}</text>')
        zero = y_of(min(max(0, low), high))  # the zero line, or the bottom of the axis when zero is not on it
        out.append(f'<line x1="{left}" y1="{zero:.1f}" x2="{width - right}" y2="{zero:.1f}" stroke="currentColor"/>')
    for j, name in enumerate(series[:count] if legend else []):
        x = 12 + j * 150
        out.append(f'<rect x="{x}" y="4" width="14" height="14" fill="{colours[j]}"/><text x="{x + 20}" y="16" {text}>{esc(name)}</text>')
    title = f'<div class="fig-title">{esc(opts["title"])}</div>' if opts.get("title") else ""
    svg = (f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(opts.get("title", "chart"))}">'
           + "".join(out) + "</svg>")
    return f'<div class="fig">{title}{svg}</div>'


def qr_svg(text, colour, size=140, error="m"):
    """A QR code for ``text`` as inline SVG, about ``size`` pixels wide, at error correction level ``error``."""
    try:
        code = segno.make(text.strip(), error=error, micro=False)
    except segno.DataOverflowError:
        raise PosterError(f"'{text.strip()[:60]}...' is too long for a QR code; use shorter text, or a lower ecc=") from None
    # SVG needs no whole pixels, so every code is the size asked for, however many modules it has
    scale = round(size / code.symbol_size(scale=1, border=2)[0], 4)
    return code.svg_inline(scale=scale, border=2, dark=colour, light=None)


def qr_html(code, opts, ctx):
    """A QR code of the block's text, or with ``type=`` of a contact card, calendar entry, Wi-Fi network,
    e-mail, phone number, text message or place written as ``key: value`` lines (see ``poster_qr``).
    ``file=`` encodes a file instead, such as a .vcf or .ics, its type from its extension."""
    text = code
    kind_given = opts.get("type")
    if opts.get("file"):
        path = Path(opts["file"])
        path = path if path.is_absolute() else Path(ctx.base) / path
        if not path.is_file():
            raise PosterError(f"{ctx.where}: the qr file {opts['file']} is not there")
        text = path.read_text(encoding="utf-8-sig")
        kind_given = kind_given or poster_qr.EXTENSIONS.get(path.suffix.lower(), "text")
    ecc = opts.get("ecc", "m").lower()
    if ecc not in ("l", "m", "q", "h"):
        raise PosterError(f"{ctx.where}: ecc must be L, M, Q or H, not '{opts['ecc']}'")
    try:
        kind = poster_qr.kind_of(kind_given)
        target = poster_qr.payload(kind, text)
    except poster_qr.QrError as exc:
        raise PosterError(f"{ctx.where}: {exc}") from None
    size = _whole(opts, "size", 140, ctx)
    label = f'<div class="cap">{inline(opts["label"])}</div>' if opts.get("label") else ""
    return f'<div class="qr">{qr_svg(target, ctx.theme.colours["strong"], size, ecc)}{label}</div>'


def barcode_html(code, opts, ctx):
    """A linear barcode of the block's first line: ``type=`` code128 (default), code39, ean13, ean8, upca or
    itf14, ``width=`` and ``height=`` in pixels, ``text=no`` to leave out the digits, ``check=yes`` for a
    Code 39 check character, and ``label=``. A GS1 code takes its digits with or without the check digit."""
    data = next((line.strip() for line in code.splitlines() if line.strip()), "")
    try:
        kind = poster_barcode.kind_of(opts.get("type"))
        data = poster_barcode.checked(kind, data)
    except poster_barcode.BarcodeError as exc:
        raise PosterError(f"{ctx.where}: {exc}") from None
    flags = {}
    for name in ("text", "check"):
        value = opts.get(name, "yes" if name == "text" else "no").lower()
        if value not in ("yes", "no", "true", "false"):
            raise PosterError(f"{ctx.where}: {name} must be yes or no, not '{opts[name]}'")
        flags[name] = value in ("yes", "true")
    if flags["check"] and kind != "code39":
        raise PosterError(f"{ctx.where}: check=yes is for code39; {kind} always has its check digit")
    width, height = _whole(opts, "width", 240, ctx), _whole(opts, "height", 70, ctx)
    svg = poster_barcode.barcode_svg(kind, data, ctx.theme.colours["strong"], width, height, flags["text"], flags["check"])
    label = f'<div class="cap">{inline(opts["label"])}</div>' if opts.get("label") else ""
    return f'<div class="barcode">{svg}{label}</div>'


def _whole(opts, name, default, ctx, low=1):
    value = opts.get(name, str(default))
    if not value.isdigit() or int(value) < low:
        raise PosterError(f"{ctx.where}: {name} must be a whole number of at least {low}, not '{value}'")
    return int(value)


def steps_html(code, opts, ctx):
    """``Heading | text | colour`` lines as numbered steps, in one column or ``cols=`` columns, from ``start=``."""
    rows = [[c.strip() for c in line.split("|")] for line in code.splitlines() if line.strip()]
    if not rows:
        raise PosterError(f"{ctx.where}: a steps block needs at least one 'Heading | text' line")
    cols, start = _whole(opts, "cols", 1, ctx), _whole(opts, "start", 1, ctx, low=0)
    out = ""
    for n, row in enumerate(rows, start):
        head, text = row[0], row[1] if len(row) > 1 else ""
        colour = ctx.theme.colour(row[2] if len(row) > 2 else None, "primary")
        body = f'<div class="ct">{inline(text)}</div>' if text else ""
        out += f'<li class="step"><b class="num" style="background:{colour}">{n}</b><div><div class="ch">{inline(head)}</div>{body}</div></li>'
    return f'<ol class="steps" start="{start}" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</ol>'


def gallery_html(code, opts, ctx):
    """``picture | caption`` lines as a grid of embedded pictures. ``height=`` crops them all to one height."""
    out, rows = "", [line.strip() for line in code.splitlines() if line.strip()]
    if not rows:
        raise PosterError(f"{ctx.where}: a gallery needs at least one 'picture | caption' line")
    cols = _whole(opts, "cols", min(len(rows), 3), ctx)
    height = f' style="height:{_whole(opts, "height", 0, ctx)}px;object-fit:cover"' if "height" in opts else ""
    for row in rows:
        src, _, caption = (part.strip() for part in row.partition("|"))
        path = ctx.base / src
        if not path.is_file():
            raise PosterError(f"{ctx.where}: the gallery picture {src} is not there (looked in {ctx.base})")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = base64.b64encode(path.read_bytes()).decode()
        note = f"<figcaption>{inline(caption)}</figcaption>" if caption else ""
        alt = re.sub(r"[*_`]", "", caption) or path.stem  # the caption's words, without its Markdown
        out += f'<figure><img alt="{esc(alt)}" src="data:{mime};base64,{data}"{height}>{note}</figure>'
    return f'<div class="gallery" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


def _rows(code):
    return [[cell.strip() for cell in line.split("|")] for line in code.splitlines() if line.strip()]


def _value(text, what, ctx):
    try:
        return float(text.replace(",", "").replace(" ", ""))
    except ValueError:
        raise PosterError(f"{ctx.where}: {what} '{text}' is not a number") from None


def progress_html(code, opts, ctx):
    """``Label | value | target | colour`` lines as bars towards their targets. ``better=lower`` for a ceiling."""
    rows = _rows(code)
    if not rows or any(len(row) < 3 for row in rows):
        raise PosterError(f"{ctx.where}: each line of a progress block is 'Label | value | target'")
    lower = _option(opts, "better", ("higher", "lower"), "higher", ctx) == "lower"
    unit, shown = opts.get("unit", ""), _option(opts, "show", ("values", "percent"), "values", ctx)
    out = ""
    for row in rows:
        value, target = _value(row[1], "a progress value", ctx), _value(row[2], "a progress target", ctx)
        if target <= 0:
            raise PosterError(f"{ctx.where}: the progress target of '{row[0]}' must be above zero")
        met = value <= target if lower else value >= target
        # met is good news; short of a target is work in progress, and over a ceiling is bad news
        default = "good" if met else "bad" if lower else "accent"
        colour = ctx.theme.colour(row[3] if len(row) > 3 else None, default)
        share = min(value / target, 1.0)
        text = f"{value / target * 100:.0f} %" if shown == "percent" else f"{esc(row[1])}{esc(unit)} of {esc(row[2])}{esc(unit)}"
        mark = " &#10003;" if met else ""
        out += (f'<div class="prog"><div class="pl"><span>{inline(row[0])}</span><b>{text}{mark}</b></div>'
                f'<div class="pt"><i style="width:{share * 100:.1f}%;background:{colour}"></i></div></div>')
    return f'<div class="progress">{out}</div>'


CHECKS = {"x": ("done", "&#10003;"), " ": ("open", ""), "!": ("failed", "&#10007;")}


def checklist_html(code, opts, ctx):
    """``[x] done``, ``[ ] open`` and ``[!] failed`` lines as a list of boxes, in ``cols=`` columns."""
    items = ""
    for line in (line.strip() for line in code.splitlines() if line.strip()):
        m = re.match(r"^\[([xX !])\]\s*(.+)$", line)
        if not m:
            raise PosterError(f"{ctx.where}: a checklist line starts [x], [ ] or [!], not '{line}'")
        kind, sign = CHECKS[m[1].lower()]
        items += f'<li class="{kind}"><span class="box">{sign}</span><span>{inline(m[2])}</span></li>'
    if not items:
        raise PosterError(f"{ctx.where}: a checklist needs at least one line")
    cols = _whole(opts, "cols", 1, ctx)
    return f'<ul class="checklist" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{items}</ul>'


def compare_html(code, opts, ctx):
    """A ``| Before | After`` header, then ``Label | before | after`` lines. The last column is the one to see."""
    rows = _rows(code)
    if len(rows) < 2 or rows[0][0] or len(rows[0]) < 3:
        raise PosterError(f"{ctx.where}: a compare block starts with a header such as '| Before | After', then 'Label | before | after' lines")
    heads, width = rows[0][1:], len(rows[0])
    grid = f"grid-template-columns:minmax(0,1.2fr) repeat({len(heads)},minmax(0,1fr))"
    out = '<div class="cmp-h"></div>' + "".join(f'<div class="cmp-h{" last" if n == len(heads) - 1 else ""}">{inline(h)}</div>' for n, h in enumerate(heads))
    for row in rows[1:]:
        if len(row) != width:
            raise PosterError(f"{ctx.where}: the compare line '{' | '.join(row)}' needs {width} cells, as its header has")
        out += f'<div class="cmp-l">{inline(row[0])}</div>'
        out += "".join(f'<div class="cmp-v{" last" if n == len(heads) - 1 else ""}">{inline(v)}</div>' for n, v in enumerate(row[1:]))
    return f'<div class="compare" style="{grid}">{out}</div>'


def people_html(code, opts, ctx):
    """``Name | role | contact | photo`` lines as cards. Without a photo, the initials stand in a circle."""
    rows = _rows(code)
    if not rows:
        raise PosterError(f"{ctx.where}: a people block needs at least one 'Name | role' line")
    out = ""
    for row in rows:
        name, role, contact, photo = (row + ["", "", ""])[:4]
        if photo:
            path = ctx.base / photo
            if not path.is_file():
                raise PosterError(f"{ctx.where}: the photo {photo} of {name} is not there (looked in {ctx.base})")
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            face = f'<img alt="{esc(name)}" src="data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}">'
        else:
            initials = "".join(word[0] for word in re.findall(r"[^\W\d_][\w'-]*", name)[:2]).upper()
            face = f'<b style="background:{ctx.theme.colour(None, "primary")}">{esc(initials)}</b>'
        lines = "".join(f"<div>{inline(text)}</div>" for text in (role, contact) if text)
        out += f'<div class="person">{face}<div><div class="ch">{inline(name)}</div>{lines}</div></div>'
    cols = _whole(opts, "cols", min(len(rows), 2), ctx)
    return f'<div class="people" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


def highlight_html(code, opts, ctx):
    """``value | label | detail | colour`` lines as figures in large type, side by side."""
    rows = _rows(code)
    if not rows:
        raise PosterError(f"{ctx.where}: a highlight block needs at least one 'value | label' line")
    out = ""
    for row in rows:
        value, label, detail = (row + ["", ""])[:3]
        colour = ctx.theme.colour(row[3] if len(row) > 3 else None, "accent")
        note = f"<small>{inline(detail)}</small>" if detail else ""
        out += f'<div class="hl" style="border-color:{colour}"><b style="color:{colour}">{inline(value)}</b><span>{inline(label)}</span>{note}</div>'
    cols = _whole(opts, "cols", len(rows), ctx)
    return f'<div class="highlights" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


def block_html(lang, opts, code, ctx):
    """HTML for a fence we handle, or None to leave it as an ordinary code block."""
    if lang in BY_FENCE:
        return diagram_html(lang, code, opts, ctx)
    if lang == "cards":
        return cards_html(code, opts, ctx)
    if lang == "lcd":
        return lcd_html(code, opts, ctx)
    if lang == "timeline":
        return timeline_html(code, opts, ctx)
    if lang == "chart":
        return chart_html(code, opts, ctx)
    if lang == "qr":
        return qr_html(code, opts, ctx)
    if lang == "barcode":
        return barcode_html(code, opts, ctx)
    if lang == "steps":
        return steps_html(code, opts, ctx)
    if lang == "gallery":
        return gallery_html(code, opts, ctx)
    if lang == "progress":
        return progress_html(code, opts, ctx)
    if lang == "checklist":
        return checklist_html(code, opts, ctx)
    if lang == "compare":
        return compare_html(code, opts, ctx)
    if lang == "people":
        return people_html(code, opts, ctx)
    if lang == "highlight":
        return highlight_html(code, opts, ctx)
    if lang in FIG_KINDS:
        return figure_html([FIG_KINDS[lang](code, ctx)], ctx)
    if lang == "figure":  # several kinds in one box, split by +++ lines, each starting with @kind
        parts = []
        for sub in re.split(r"(?m)^\+\+\+\s*$", code):
            kind, _, body = sub.strip("\n").partition("\n")
            kind = kind.strip().lstrip("@").lower()
            if kind not in FIG_KINDS:
                logger.warning(f"unknown figure part '{kind}'")
                continue
            parts.append(FIG_KINDS[kind](body, ctx))
        return figure_html(parts, ctx)
    return None
