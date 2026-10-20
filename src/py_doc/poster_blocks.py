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

import segno
from markdown_it import MarkdownIt

from py_doc.diagrams import BY_FENCE, DiagramError
from py_doc.diagrams.render import draw_cached
from py_doc.errors import ConversionError, ToolFailed
from py_doc.poster_themes import Theme

logger = logging.getLogger(__name__)

MD = MarkdownIt("commonmark").enable("table")
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


def lcd_html(code):
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
    return f'<div class="lcds">{out}</div>'


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


def chart_html(code, opts, ctx):
    """A ``column``, ``bar`` or ``line`` chart as SVG: ``label | value | value ...`` lines, ``series:`` names them."""
    kind = opts.get("type", "column").lower()
    if kind not in CHART_KINDS:
        raise PosterError(f"{ctx.where}: chart type must be one of {', '.join(CHART_KINDS)}, not '{kind}'")
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
    values = [v for _, vs in rows for v in vs]
    low = -_nice(-min(values)) if min(values) < 0 else 0.0
    try:
        high = float(opts["max"]) if "max" in opts else _nice(max(values)) or 1.0
    except ValueError:
        raise PosterError(f"{ctx.where}: chart max must be a number") from None
    span = (high - low) or 1.0
    legend = 24 if len(series) > 1 else 0
    width = 640
    natural = 16 + legend + len(rows) * max(30, 16 * count + 12) if kind == "bar" else 300
    height = int(opts["height"]) if opts.get("height", "").isdigit() else natural
    text = 'font-size="13" fill="currentColor"'
    out = []
    if kind == "bar":
        left, top, right, bottom = 140, 8 + legend, 60, 8
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
                out.append(f'<text x="{max(x0, x1) + 4:.1f}" y="{yy + thick / 2 + 4:.1f}" {text}>{_number(v)}{esc(unit)}</text>')
        out.append(f'<line x1="{x0:.1f}" y1="{top}" x2="{x0:.1f}" y2="{height - bottom}" stroke="currentColor"/>')
    else:
        left, top, right, bottom = 52, 12 + legend, 12, 30
        plot_w, plot_h = width - left - right, height - top - bottom

        def y_of(v):
            return top + plot_h - (v - low) / span * plot_h

        for step in range(5):
            v = low + span * step / 4
            out.append(f'<line x1="{left}" y1="{y_of(v):.1f}" x2="{width - right}" y2="{y_of(v):.1f}" stroke="currentColor" stroke-opacity=".25"/>')
            out.append(f'<text x="{left - 6}" y="{y_of(v) + 4:.1f}" text-anchor="end" {text}>{_number(v)}</text>')
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
                    out.append(f'<text x="{x + thick / 2:.1f}" y="{min(y0, y1) - 4:.1f}" text-anchor="middle" {text}>{_number(v)}{esc(unit)}</text>')
        else:
            for j in range(count):
                points = [(left + band * (i + 0.5), y_of(vs[j])) for i, (_, vs) in enumerate(rows) if j < len(vs)]
                path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
                out.append(f'<polyline points="{path}" fill="none" stroke="{colours[j]}" stroke-width="3"/>')
                out += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colours[j]}"/>' for x, y in points]
        out.append(f'<line x1="{left}" y1="{y_of(0):.1f}" x2="{width - right}" y2="{y_of(0):.1f}" stroke="currentColor"/>')
    for j, name in enumerate(series[:count] if legend else []):
        x = 12 + j * 150
        out.append(f'<rect x="{x}" y="4" width="14" height="14" fill="{colours[j]}"/><text x="{x + 20}" y="16" {text}>{esc(name)}</text>')
    title = f'<div class="fig-title">{esc(opts["title"])}</div>' if opts.get("title") else ""
    svg = (f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(opts.get("title", "chart"))}">'
           + "".join(out) + "</svg>")
    return f'<div class="fig">{title}{svg}</div>'


def qr_svg(text, colour, size=140):
    """A QR code for ``text`` as inline SVG, about ``size`` pixels wide."""
    try:
        code = segno.make(text.strip(), error="m")
    except segno.DataOverflowError:
        raise PosterError(f"'{text.strip()[:60]}...' is too long for a QR code; use a shorter address") from None
    scale = max(1, round(size / code.symbol_size(scale=1, border=2)[0]))
    return code.svg_inline(scale=scale, border=2, dark=colour, light=None)


def qr_html(code, opts, ctx):
    target = next((line.strip() for line in code.splitlines() if line.strip()), "")
    if not target:
        raise PosterError(f"{ctx.where}: a qr block needs the text or address to encode")
    size = int(opts["size"]) if opts.get("size", "").isdigit() else 140
    label = f'<div class="cap">{inline(opts["label"])}</div>' if opts.get("label") else ""
    return f'<div class="qr">{qr_svg(target, ctx.theme.colours["strong"], size)}{label}</div>'


def block_html(lang, opts, code, ctx):
    """HTML for a fence we handle, or None to leave it as an ordinary code block."""
    if lang in BY_FENCE:
        return diagram_html(lang, code, opts, ctx)
    if lang == "cards":
        return cards_html(code, opts, ctx)
    if lang == "lcd":
        return lcd_html(code)
    if lang == "timeline":
        return timeline_html(code, opts, ctx)
    if lang == "chart":
        return chart_html(code, opts, ctx)
    if lang == "qr":
        return qr_html(code, opts, ctx)
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
