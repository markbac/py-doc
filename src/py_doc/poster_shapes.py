"""Poster blocks that draw layers, rings and proportions as shapes: a pyramid or cone, a funnel, a stack, target
rings, a cutaway, objects to scale, vessels, a memory map, a tape of cells, a ring buffer, a cycle, a balance and
an iceberg. Each is SVG drawn with ``poster_svg``.
"""

from __future__ import annotations

import math
import re

from py_doc.poster_blocks import Fragment, PosterError, _whole, block, esc
from py_doc.poster_svg import Linear, arc, label, number, polar, sector, spread, svg, text_width, wrap

WIDTH = 640
SIZE = 13
SMALL = 11.5
WHITE = 'fill="#fff" font-weight="700"'


def _lines(code):
    return [line.strip() for line in code.splitlines() if line.strip()]


def _cells(line):
    return [cell.strip() for cell in line.split("|")]


def _fig(opts, picture):
    title = f'<div class="fig-title">{esc(opts["title"])}</div>' if opts.get("title") else ""
    return Fragment(f'<div class="fig">{title}{picture}</div>', picture)


def _value(text, ctx, what):
    m = re.match(r"\s*(-?[\d.,]+)", text or "")
    if not m:
        raise PosterError(f"{ctx.where}: {what} '{text}' does not start with a number")
    return float(m[1].replace(",", ""))


def _rows(code, ctx, what, least=1):
    rows = [_cells(line) for line in _lines(code)]
    if len(rows) < least:
        raise PosterError(f"{ctx.where}: a {what} block needs at least {least} line{'s' if least > 1 else ''}")
    return rows


def _colour(row, at, ctx, default="secondary"):
    return ctx.theme.colour(row[at] if len(row) > at and row[at] else None, default)


def _muted(ctx):
    return f'fill="{ctx.theme.colours["muted"]}"'


def _callouts(out, items, x_text, top, bottom, ctx, gap=34):
    """Text beside a shape, each joined to its place by a leader line: ``items`` are (x, y, heading, detail)."""
    ys = spread([y for _, y, _, _ in items], gap, top, bottom)
    for (x, y, head, detail), ty in zip(items, ys):
        out.append(
            f'<path d="M{x:.1f},{y:.1f} L{x_text - 8:.1f},{ty:.1f}" stroke="currentColor" stroke-opacity=".5" fill="none"/>'
        )
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="currentColor"/>')
        out.append(label(x_text, ty - 2, head, SIZE, extra='font-weight="700"'))
        for n, line in enumerate(wrap(detail, WIDTH - x_text - 6, SMALL)[:2]):
            out.append(label(x_text, ty + 12 + n * 13, line, SMALL, extra=_muted(ctx)))
    return max(ys, default=bottom) + 30


# ---------------------------------------------------------------------------
# pyramid and cone, funnel
# ---------------------------------------------------------------------------


@block(
    "pyramid",
    "label | value | detail | colour lines from the top; direction=up (a point at the top, default) or down",
    "End-to-end | 5 % | Real network and hardware | red\nHardware in the loop | 20 % | HIL rig | amber\nIntegration | 25 % | Simulated peripherals | blue\nUnit tests | 50 % | Fast, off target | green",
)
def pyramid_html(code, opts, ctx):
    """Tiers of a pyramid (or, ``direction=down``, a cone), with labels inside and details beside."""
    rows = _rows(code, ctx, "pyramid")
    down = opts.get("direction", "up").lower() == "down"
    n = len(rows)
    tier, gap, top = 46, 3, 10
    width, cx = 340, 180
    out, items = [], []
    for i, row in enumerate(rows):
        # half-widths at the tier's top and bottom: 0 at the point, `width / 2` at the base
        a, b = (i / n, (i + 1) / n) if not down else ((n - i) / n, (n - i - 1) / n)
        y0 = top + i * (tier + gap)
        w0, w1 = width / 2 * a, width / 2 * b
        colour = _colour(row, 3, ctx)
        out.append(
            f'<path d="M{cx - w0:.1f},{y0} L{cx + w0:.1f},{y0} L{cx + w1:.1f},{y0 + tier} L{cx - w1:.1f},{y0 + tier} Z" fill="{colour}"/>'
        )
        room = max(w0, w1) * 2 - 30
        name = wrap(row[0], room, SIZE, True)
        value = row[1] if len(row) > 1 else ""
        if room > 50:
            for k, part in enumerate(name[:2]):
                out.append(
                    label(cx, y0 + tier / 2 + 1 + (k - (len(name[:2]) - 1) / 2) * 14, part, SIZE, "middle", WHITE)
                )
            head = value
        else:  # too narrow at the point: the name goes beside it
            head = f"{row[0]} {value}".strip()
        items.append((cx + (w0 + w1) / 2 + 4, y0 + tier / 2, head, row[2] if len(row) > 2 else ""))
    bottom = top + n * (tier + gap)
    end = _callouts(out, items, cx + width / 2 + 30, top + 10, bottom - 10, ctx)
    return _fig(opts, svg(WIDTH, max(bottom, end), "".join(out), opts.get("title", "pyramid"), "chart"))


@block(
    "funnel",
    "stage | value | detail | colour lines; percent=no leaves out the share kept at each stage",
    "Candidates | 4,000 | Transit signals | blue\nVetted | 1,200 | Not false positives | navy\nConfirmed | 300 | Radial velocity | green",
)
def funnel_html(code, opts, ctx):
    """Stages narrowing in proportion to their values, with the share each keeps of the one before."""
    rows = _rows(code, ctx, "funnel")
    values = [_value(row[1] if len(row) > 1 else "", ctx, "a funnel value") for row in rows]
    if max(values) <= 0:
        raise PosterError(f"{ctx.where}: a funnel needs a value above zero")
    show = opts.get("percent", "yes").lower() not in ("no", "false")
    cx, full, tier, gap, top = 200, 380, 44, 4, 10
    out, items = [], []
    widths = [max(full * v / max(values), 40) for v in values]
    for i, (row, v) in enumerate(zip(rows, values)):
        y0 = top + i * (tier + gap)
        w0 = widths[i]
        w1 = widths[i + 1] if i + 1 < len(rows) else w0 * 0.8
        colour = _colour(row, 3, ctx)
        out.append(
            f'<path d="M{cx - w0 / 2:.1f},{y0} L{cx + w0 / 2:.1f},{y0} L{cx + w1 / 2:.1f},{y0 + tier} L{cx - w1 / 2:.1f},{y0 + tier} Z" fill="{colour}"/>'
        )
        out.append(label(cx, y0 + tier / 2 - 2, row[0], SIZE, "middle", WHITE))
        out.append(label(cx, y0 + tier / 2 + 13, row[1], SMALL, "middle", 'fill="#fff"'))
        head = f"{v / values[i - 1] * 100:.0f} % kept" if show and i and values[i - 1] else ""
        items.append((cx + w0 / 2 + 4, y0 + tier / 2, head, row[2] if len(row) > 2 else ""))
    bottom = top + len(rows) * (tier + gap)
    end = _callouts(out, items, cx + full / 2 + 26, top + 10, bottom - 10, ctx)
    return _fig(opts, svg(WIDTH, max(bottom, end), "".join(out), opts.get("title", "funnel"), "chart"))


# ---------------------------------------------------------------------------
# stack, target
# ---------------------------------------------------------------------------


@block(
    "stack",
    "layer | badge | detail | colour lines from the top; side: label | first-last | colour lines bracket layers",
    "Application | L7 | LwM2M objects | green\nTransport | L4 | CoAP over DTLS | blue\nNetwork | L3 | IPv6 / NIDD | navy\nRadio | L1-2 | NB-IoT | grey\nside: Secured | 2-2 | red",
)
def stack_html(code, opts, ctx):
    """Full-width layers in order, each with a badge and a detail, and brackets down the side over layers."""
    layers, sides = [], []
    for line in _lines(code):
        if line.lower().startswith("side:"):
            cells = _cells(line[5:])
            m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", cells[1] if len(cells) > 1 else "")
            if not m:
                raise PosterError(f"{ctx.where}: a stack side is 'side: label | first-last', not '{line}'")
            sides.append((cells[0], int(m[1]), int(m[2] or m[1]), _colour(cells, 2, ctx, "accent")))
        else:
            layers.append(_cells(line))
    if not layers:
        raise PosterError(f"{ctx.where}: a stack needs at least one layer")
    row, gap, top = 40, 4, 6
    right = WIDTH - (30 if sides else 6) - 30 * max(len(sides) - 1, 0)
    out = []
    for i, cells in enumerate(layers):
        y = top + i * (row + gap)
        colour = _colour(cells, 3, ctx)
        out.append(f'<rect x="6" y="{y}" width="{right - 6}" height="{row}" rx="4" fill="{colour}"/>')
        out.append(label(18, y + row / 2 + 5, cells[0], SIZE + 1, extra=WHITE))
        if len(cells) > 1 and cells[1]:
            bw = text_width(cells[1], SMALL, True) + 14
            out.append(
                f'<rect x="{200}" y="{y + 10}" width="{bw:.1f}" height="20" rx="10" fill="#fff" fill-opacity=".9"/>'
            )
            out.append(label(200 + bw / 2, y + 24, cells[1], SMALL, "middle", f'fill="{colour}" font-weight="700"'))
        if len(cells) > 2 and cells[2]:
            out.append(label(right - 12, y + row / 2 + 5, cells[2], SMALL + 0.5, "end", 'fill="#fff"'))
    for n, (name, first, last, colour) in enumerate(sides):
        if not 1 <= first <= last <= len(layers):
            raise PosterError(f"{ctx.where}: the stack side '{name}' names layers {first}-{last} of {len(layers)}")
        x = right + 12 + n * 30
        y0, y1 = top + (first - 1) * (row + gap), top + last * (row + gap) - gap
        out.append(
            f'<path d="M{x - 6},{y0} L{x},{y0} L{x},{y1} L{x - 6},{y1}" stroke="{colour}" stroke-width="3" fill="none"/>'
        )
        my = (y0 + y1) / 2
        out.append(
            f'<text x="{x + 14:.1f}" y="{my:.1f}" transform="rotate(-90 {x + 14:.1f} {my:.1f})" text-anchor="middle" font-size="{SMALL}" font-weight="700" fill="{colour}">{esc(name)}</text>'
        )
    height = top + len(layers) * (row + gap) + 2
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "stack"), "chart"))


@block(
    "target",
    "ring | detail | colour lines from the core outwards",
    "Domain | Entities and rules | navy\nUse cases | What the system does | blue\nAdapters | Controllers, gateways | green\nInfrastructure | Database, network | grey",
)
def target_html(code, opts, ctx):
    """Concentric rings from the core outward, each with a callout beside the rings."""
    rows = _rows(code, ctx, "target")
    cx, cy, outer = 170, 160, 150
    step = outer / len(rows)
    out, items = [], []
    for i in range(len(rows) - 1, -1, -1):
        r = step * (i + 1)
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{_colour(rows[i], 2, ctx)}" stroke="#fff" stroke-width="2"/>'
        )
    for i, row in enumerate(rows):
        r = step * (i + 0.5) if i else 0
        x, y = polar(cx, cy, r, 60)
        items.append((x, y, row[0], row[1] if len(row) > 1 else ""))
    end = _callouts(out, items[::-1], 360, 30, 300, ctx, gap=44)
    return _fig(opts, svg(WIDTH, max(cy * 2 + 10, end), "".join(out), opts.get("title", "target"), "chart"))


# ---------------------------------------------------------------------------
# cutaway: a sphere with a wedge cut out, or a column of altitude or depth
# ---------------------------------------------------------------------------


@block(
    "cutaway",
    "type=sphere: shell | outer radius | detail | colour lines from the core; type=column: from | to | label | detail | colour",
    "Core | 0.25 | 15 million K | amber\nRadiative zone | 0.7 | Light takes 170,000 years | red\nConvective zone | 1 | Rising plasma | brown",
    "type=sphere",
)
def cutaway_html(code, opts, ctx):
    kind = opts.get("type", "sphere").lower()
    if kind not in ("sphere", "column"):
        raise PosterError(f"{ctx.where}: cutaway type must be sphere or column, not '{kind}'")
    return _fig(opts, (_sphere if kind == "sphere" else _column)(code, opts, ctx))


def _sphere(code, opts, ctx):
    rows = _rows(code, ctx, "cutaway")
    radii = [_value(row[1] if len(row) > 1 else "", ctx, "a shell radius") for row in rows]
    if any(b <= a for a, b in zip(radii, radii[1:])):
        raise PosterError(f"{ctx.where}: the shells of a cutaway go from the core outwards, each larger than the last")
    cx, cy, size = 170, 170, 155
    scale = size / radii[-1]
    unit = opts.get("unit", "")
    out = [f'<circle cx="{cx}" cy="{cy}" r="{size}" fill="{_colour(rows[-1], 3, ctx)}"/>']
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{size}" fill="#000" fill-opacity=".12"/>')  # the outside, in shade
    items = []
    inner = 0.0
    for row, r in zip(rows, radii):
        colour = _colour(row, 3, ctx)
        out.append(
            f'<path d="{sector(cx, cy, inner * scale, r * scale, 0, 90)}" fill="{colour}" stroke="#fff" stroke-width="1"/>'
        )
        x, y = polar(cx, cy, (inner + r) / 2 * scale, 45)
        items.append((x, y, row[0], " ".join(c for c in (f"{number(r)}{unit}", row[2] if len(row) > 2 else "") if c)))
        inner = r
    out.append(f'<path d="M{cx},{cy - size} L{cx},{cy} L{cx + size},{cy}" stroke="#fff" stroke-width="2" fill="none"/>')
    end = _callouts(out, items, 370, 20, 320, ctx, gap=42)
    return svg(WIDTH, max(cy * 2 + 10, end), "".join(out), opts.get("title", "cutaway"), "chart")


def _column(code, opts, ctx):
    rows = _rows(code, ctx, "cutaway")
    bands = []
    for row in rows:
        if len(row) < 3:
            raise PosterError(f"{ctx.where}: a column band is 'from | to | label', not '{' | '.join(row)}'")
        a, b = _value(row[0], ctx, "a band edge"), _value(row[1], ctx, "a band edge")
        bands.append((min(a, b), max(a, b), row[2], row[3] if len(row) > 3 else "", _colour(row, 4, ctx)))
    low, high = min(b[0] for b in bands), max(b[1] for b in bands)
    top, height = 10, 360
    upward = opts.get("direction", "up").lower() != "down"  # altitude grows up; depth (direction=down) grows down
    y_of = Linear(low, high, top + height, top) if upward else Linear(low, high, top, top + height)
    unit = opts.get("unit", "")
    out, items = [], []
    for a, b, name, detail, colour in bands:
        y0, y1 = sorted((y_of(a), y_of(b)))
        out.append(f'<rect x="80" y="{y0:.1f}" width="180" height="{y1 - y0:.1f}" fill="{colour}" stroke="#fff"/>')
        if y1 - y0 > 18:
            out.append(label(170, (y0 + y1) / 2 + 5, name, SIZE, "middle", WHITE))
        items.append((262, (y0 + y1) / 2, name if y1 - y0 <= 18 else "", detail))
    for edge in sorted({e for band in bands for e in band[:2]}):
        y = y_of(edge)
        out.append(f'<line x1="70" y1="{y:.1f}" x2="80" y2="{y:.1f}" stroke="currentColor"/>')
        out.append(label(64, y + 4, f"{number(edge)}{unit}", SMALL, "end"))
    items = [i for i in items if i[2] or i[3]]
    end = _callouts(out, [(x, y, h or "", d) for x, y, h, d in items], 300, top + 10, top + height - 10, ctx)
    return svg(WIDTH, max(top + height + 10, end), "".join(out), opts.get("title", "column"), "chart")


# ---------------------------------------------------------------------------
# sizes, vessels
# ---------------------------------------------------------------------------


@block(
    "sizes",
    "label | size | detail | colour lines; shape=circle|hexagon|square, nested=yes centres them on each other, unit=",
    "ELT | 39 | Extremely Large Telescope | navy\nJWST | 6.5 | 18 hexagons | amber\nHubble | 2.4 | One mirror | blue",
    "shape=hexagon",
)
def sizes_html(code, opts, ctx):
    """Objects drawn to the same scale, side by side or (``nested=yes``) one inside the other."""
    rows = _rows(code, ctx, "sizes")
    values = [_value(row[1] if len(row) > 1 else "", ctx, "a size") for row in rows]
    if min(values) <= 0:
        raise PosterError(f"{ctx.where}: every size must be above zero")
    shape = opts.get("shape", "circle").lower()
    if shape not in ("circle", "hexagon", "square"):
        raise PosterError(f"{ctx.where}: sizes shape must be circle, hexagon or square, not '{shape}'")
    nested = opts.get("nested", "no").lower() in ("yes", "true")
    unit = opts.get("unit", " m")
    big = 220
    scale = big / max(values)
    out = []

    def draw(x, y, d, colour, outline=False):
        r = max(d / 2, 1.5)
        paint = f'fill="none" stroke="{colour}" stroke-width="3"' if outline else f'fill="{colour}"'
        if shape == "circle":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" {paint}/>')
        elif shape == "square":
            out.append(f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" {paint}/>')
        else:
            points = " ".join(f"{px:.1f},{py:.1f}" for px, py in (polar(x, y, r, a) for a in range(0, 360, 60)))
            out.append(f'<polygon points="{points}" {paint}/>')

    if nested:
        cx, cy = 140, 20 + big / 2
        order = sorted(range(len(rows)), key=lambda i: -values[i])
        for i in order:
            draw(cx, cy, values[i] * scale, _colour(rows[i], 3, ctx), outline=True)
        items = [
            (
                cx + values[i] * scale / 2 * 0.7071,
                cy - values[i] * scale / 2 * 0.7071,
                rows[i][0],
                f"{number(values[i])}{unit}",
            )
            for i in order
        ]
        end = _callouts(out, items, 300, 20, 20 + big, ctx)
        return _fig(opts, svg(WIDTH, max(big + 40, end), "".join(out), opts.get("title", "sizes"), "chart"))
    total = sum(v * scale for v in values) + 30 * (len(values) - 1)
    if total > WIDTH - 20:  # side by side they must fit: shrink the scale
        scale *= (WIDTH - 20 - 30 * (len(values) - 1)) / (total - 30 * (len(values) - 1))
    base = 20 + max(values) * scale
    x = 10
    for row, v in zip(rows, values):
        d = v * scale
        draw(x + d / 2, base - d / 2, d, _colour(row, 3, ctx))
        lx = x + max(d, 4) / 2
        out.append(label(lx, base + 18, row[0], SIZE, "middle", 'font-weight="700"'))
        out.append(label(lx, base + 32, f"{number(v)}{unit}", SMALL, "middle", _muted(ctx)))
        if len(row) > 2 and row[2]:
            out.append(label(lx, base + 45, row[2], SMALL - 1, "middle", _muted(ctx)))
        x += max(d, 2) + 30
    return _fig(opts, svg(WIDTH, base + 54, "".join(out), opts.get("title", "sizes"), "chart"))


LAYER = re.compile(r"^\s*([\d.]+)\s*([A-Za-zµ%]*)\s+(.*?)\s*(?:\(([^)]+)\))?\s*$")


@block(
    "vessels",
    "Name | 30 ml Espresso (amber) + 60 ml Milk (cream) lines: layers from the bottom; shape=glass|cup|beaker; cols=",
    "Espresso | 30 ml Espresso (amber)\nCortado | 30 ml Espresso (amber) + 30 ml Steamed milk (#f3e3c3)\nFlat white | 60 ml Ristretto (amber) + 120 ml Microfoam (#f3e3c3)",
)
def vessels_html(code, opts, ctx):
    """Containers side by side, each filled with its layers in proportion, on the same scale."""
    vessels = []
    for row in _rows(code, ctx, "vessels"):
        if len(row) < 2:
            raise PosterError(f"{ctx.where}: a vessels line is 'Name | amount label (colour) + ...'")
        layers = []
        for part in row[1].split("+"):
            m = LAYER.match(part)
            if not m:
                raise PosterError(f"{ctx.where}: a layer is 'amount unit label (colour)', not '{part.strip()}'")
            layers.append(
                (
                    float(m[1]),
                    m[2],
                    m[3],
                    ctx.theme.colour(m[4], "secondary") if m[4] else ctx.theme.colours["secondary"],
                )
            )
        vessels.append((row[0], layers))
    shape = opts.get("shape", "glass").lower()
    if shape not in ("glass", "cup", "beaker"):
        raise PosterError(f"{ctx.where}: vessels shape must be glass, cup or beaker, not '{shape}'")
    cols = _whole(opts, "cols", len(vessels), ctx)
    slot = WIDTH / cols
    most = max(sum(layer[0] for layer in layers) for _, layers in vessels)
    body_h, top = 160, 12
    out, bottom = [], 0
    for n, (name, layers) in enumerate(vessels):
        col, row_n = n % cols, n // cols
        x, y = slot * col + slot / 2, top + row_n * (body_h + 70)
        w_top, w_bot = (
            min(slot * 0.62, 120),
            min(slot * 0.62, 120) * (0.72 if shape == "glass" else 1 if shape == "beaker" else 0.82),
        )
        y_bot = y + body_h
        level = y_bot
        for amount, unit, name_layer, colour in layers:
            h = body_h * amount / most
            frac0, frac1 = (y_bot - level) / body_h, (y_bot - level + h) / body_h
            wa, wb = w_bot + (w_top - w_bot) * frac0, w_bot + (w_top - w_bot) * frac1
            out.append(
                f'<path d="M{x - wa / 2:.1f},{level:.1f} L{x + wa / 2:.1f},{level:.1f} L{x + wb / 2:.1f},{level - h:.1f} L{x - wb / 2:.1f},{level - h:.1f} Z" fill="{colour}"/>'
            )
            if h > 14:
                out.append(
                    label(
                        x,
                        level - h / 2 + 4,
                        f"{number(amount)} {unit} {name_layer}".replace("  ", " ").strip(),
                        SMALL - 1,
                        "middle",
                        'fill="#1d1f27"',
                    )
                )
            level -= h
        out.append(
            f'<path d="M{x - w_top / 2:.1f},{y} L{x - w_bot / 2:.1f},{y_bot} L{x + w_bot / 2:.1f},{y_bot} L{x + w_top / 2:.1f},{y}" fill="none" stroke="currentColor" stroke-width="2.5"/>'
        )
        if shape == "cup":
            out.append(
                f'<path d="M{x + w_top / 2 - 4:.1f},{y + 30} C{x + w_top / 2 + 34:.1f},{y + 30} {x + w_top / 2 + 34:.1f},{y + 90} {x + w_bot / 2 + 2:.1f},{y + 100}" fill="none" stroke="currentColor" stroke-width="2.5"/>'
            )
        out.append(label(x, y_bot + 20, name, SIZE, "middle", 'font-weight="700"'))
        total = sum(layer[0] for layer in layers)
        out.append(label(x, y_bot + 35, f"{number(total)} {layers[0][1]}".strip(), SMALL, "middle", _muted(ctx)))
        bottom = max(bottom, y_bot + 44)
    return _fig(opts, svg(WIDTH, bottom, "".join(out), opts.get("title", "vessels"), "chart"))


# ---------------------------------------------------------------------------
# memory, tape, ring
# ---------------------------------------------------------------------------


def _address(text, ctx):
    try:
        return int(text.replace("_", "").replace("'", ""), 0)
    except ValueError:
        raise PosterError(f"{ctx.where}: '{text}' is not an address such as 0x0800_0000") from None


def _bytes(text, ctx):
    m = re.fullmatch(r"\s*([\d.]+)\s*([KMG]?)i?B?\s*", text, re.I)
    if not m:
        raise PosterError(f"{ctx.where}: '{text}' is not a size such as 32 KB")
    return int(float(m[1]) * {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[m[2].upper()])


def _size_text(size):
    for unit, factor in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if size >= factor and size % (factor // 8 or 1) == 0:
            return f"{number(size / factor)} {unit}"
    return f"{size} B"


@block(
    "memory",
    "start | size | region | colour | grow (up or down) lines, such as 0x0800_0000 | 32 KB | Bootloader | navy",
    "0x0800_0000 | 32 KB | Bootloader | navy\n0x0800_8000 | 224 KB | Application | blue\n0x2000_0000 | 8 KB | Heap | green | up\n0x2000_E000 | 8 KB | Stack | amber | down",
)
def memory_html(code, opts, ctx):
    """A vertical address map, the highest address at the top, with each region's start, end and size, gaps
    between regions shaded, and arrows for a stack or heap that grows."""
    regions = []
    for row in _rows(code, ctx, "memory"):
        if len(row) < 3:
            raise PosterError(f"{ctx.where}: a memory line is 'start | size | region', not '{' | '.join(row)}'")
        start, size = _address(row[0], ctx), _bytes(row[1], ctx)
        grow = row[4].lower() if len(row) > 4 and row[4] else ""
        regions.append((start, size, row[2], _colour(row, 3, ctx), grow))
    regions.sort(key=lambda r: -r[0])
    box_h, gap_h, top = 46, 22, 8
    out, y = [], top
    width = 30 if max(r[0] + r[1] for r in regions) <= 0xFFFFFFFF else 22
    hexes = (lambda a: f"0x{a >> 16:04X}_{a & 0xFFFF:04X}") if width == 30 else (lambda a: f"0x{a:X}")
    for n, (start, size, name, colour, grow) in enumerate(regions):
        end = start + size
        if n and end < regions[n - 1][0]:  # a gap above this region
            out.append(
                f'<rect x="150" y="{y}" width="260" height="{gap_h}" fill="currentColor" fill-opacity=".06" stroke="currentColor" stroke-opacity=".2" stroke-dasharray="4 3"/>'
            )
            out.append(
                label(
                    280,
                    y + gap_h / 2 + 4,
                    f"unused, {_size_text(regions[n - 1][0] - end)}",
                    SMALL - 1,
                    "middle",
                    _muted(ctx),
                )
            )
            y += gap_h
        out.append(f'<rect x="150" y="{y}" width="260" height="{box_h}" fill="{colour}" stroke="#fff"/>')
        out.append(label(280, y + box_h / 2 + 5, name, SIZE + 1, "middle", WHITE))
        out.append(
            label(
                142,
                y + 10,
                hexes(end - 1),
                SMALL - 1,
                "end",
                f'font-family="{esc(ctx.theme.fonts["mono"])}" {_muted(ctx)}',
            )
        )
        out.append(
            label(142, y + box_h - 2, hexes(start), SMALL - 1, "end", f'font-family="{esc(ctx.theme.fonts["mono"])}"')
        )
        out.append(label(420, y + box_h / 2 + 5, _size_text(size), SMALL))
        if grow in ("up", "down"):
            ax = 520
            y0, y1 = (y + box_h - 6, y + 6) if grow == "up" else (y + 6, y + box_h - 6)
            out.append(f'<line x1="{ax}" y1="{y0}" x2="{ax}" y2="{y1}" stroke="{colour}" stroke-width="3"/>')
            tip = y1
            sign = -1 if grow == "up" else 1
            out.append(
                f'<path d="M{ax - 6},{tip - sign * 8} L{ax},{tip} L{ax + 6},{tip - sign * 8}" fill="none" stroke="{colour}" stroke-width="3"/>'
            )
            out.append(label(ax + 12, y + box_h / 2 + 4, f"grows {grow}", SMALL, extra=f'fill="{colour}"'))
        y += box_h
    return _fig(opts, svg(WIDTH, y + 6, "".join(out), opts.get("title", "memory map"), "chart"))


@block(
    "tape",
    "cells: A U G G C U lines (cells split by spaces), then first-last | label | colour lines grouping cells (from 1)",
    "cells: A U G G C U U A A\n1-3 | Met (start) | green\n4-6 | Ala | blue\n7-9 | Stop | red",
)
def tape_html(code, opts, ctx):
    """A row of cells, with groups of them bracketed and labelled under the row."""
    cells, groups = [], []
    for line in _lines(code):
        if line.lower().startswith("cells:"):
            cells += line[6:].split()
            continue
        row = _cells(line)
        m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", row[0])
        if not m:
            raise PosterError(f"{ctx.where}: a tape group starts 'first-last', not '{row[0]}'")
        groups.append((int(m[1]), int(m[2] or m[1]), row[1] if len(row) > 1 else "", _colour(row, 2, ctx)))
    if not cells:
        raise PosterError(f"{ctx.where}: a tape needs a 'cells:' line")
    size = min(48, (WIDTH - 20) / len(cells))
    left, top = (WIDTH - size * len(cells)) / 2, 8
    colour_of = {}
    for first, last, name, colour in groups:
        if not 1 <= first <= last <= len(cells):
            raise PosterError(f"{ctx.where}: the tape group '{name}' is cells {first}-{last} of {len(cells)}")
        for n in range(first, last + 1):
            colour_of[n] = colour
    out = []
    for n, cell in enumerate(cells, 1):
        x = left + (n - 1) * size
        colour = colour_of.get(n)
        paint = (
            f'fill="{colour}" fill-opacity=".22" stroke="{colour}"'
            if colour
            else f'fill="{ctx.theme.colours["surface"]}" stroke="{ctx.theme.colours["border"]}"'
        )
        out.append(f'<rect x="{x + 1:.1f}" y="{top}" width="{size - 2:.1f}" height="{size - 2:.1f}" rx="4" {paint}/>')
        out.append(
            label(
                x + size / 2,
                top + size / 2 + 5,
                cell,
                min(SIZE + 4, size * 0.45),
                "middle",
                f'font-family="{esc(ctx.theme.fonts["mono"])}" font-weight="700"',
            )
        )
    y = top + size + 6
    for first, last, name, colour in groups:
        x0, x1 = left + (first - 1) * size + 3, left + last * size - 3
        out.append(
            f'<path d="M{x0:.1f},{y} L{x0:.1f},{y + 6} L{x1:.1f},{y + 6} L{x1:.1f},{y}" stroke="{colour}" stroke-width="2" fill="none"/>'
        )
        bw = max(text_width(name, SMALL, True) + 14, 30)
        cx = (x0 + x1) / 2
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y + 12}" width="{bw:.1f}" height="20" rx="10" fill="{colour}"/>')
        out.append(label(cx, y + 26, name, SMALL, "middle", WHITE))
    return _fig(opts, svg(WIDTH, y + 40, "".join(out), opts.get("title", "tape"), "chart"))


@block(
    "ring",
    "fill: first-last | label | colour and pointer: cell | label | colour lines; cells= (default 16)",
    "fill: 3-9 | Waiting samples | blue\npointer: 3 | TAIL (read) | green\npointer: 10 | HEAD (write) | red",
    "cells=16",
)
def ring_html(code, opts, ctx):
    """A circular buffer of ``cells`` slots, the filled ones coloured (a range may wrap), with labelled pointers."""
    count = _whole(opts, "cells", 16, ctx, low=3)
    fills, pointers = [], []
    for line in _lines(code):
        kind, _, rest = line.partition(":")
        kind = kind.strip().lower()
        row = _cells(rest)
        if kind == "fill":
            m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", row[0])
            if not m:
                raise PosterError(f"{ctx.where}: a ring fill is 'fill: first-last | label', not '{line}'")
            fills.append((int(m[1]), int(m[2]), row[1] if len(row) > 1 else "", _colour(row, 2, ctx)))
        elif kind == "pointer":
            if not row[0].isdigit():
                raise PosterError(f"{ctx.where}: a ring pointer is 'pointer: cell | label', not '{line}'")
            pointers.append((int(row[0]), row[1] if len(row) > 1 else "", _colour(row, 2, ctx, "strong")))
        else:
            raise PosterError(f"{ctx.where}: a ring line starts fill: or pointer:, not '{line}'")
    cx, cy, outer, inner = 170, 170, 130, 86
    step = 360 / count
    colour_of = {}
    for first, last, _, colour in fills:
        n = first
        while True:
            colour_of[n % count] = colour
            if n % count == last % count:
                break
            n += 1
    out = []
    for n in range(count):
        colour = colour_of.get(n)
        fill = colour or ctx.theme.colours["surface"]
        out.append(
            f'<path d="{sector(cx, cy, inner, outer, n * step + 1, (n + 1) * step - 1)}" fill="{fill}" stroke="{ctx.theme.colours["border"]}"/>'
        )
        tx, ty = polar(cx, cy, (inner + outer) / 2, (n + 0.5) * step)
        out.append(label(tx, ty + 4, str(n), SMALL - 1, "middle", 'fill="#fff"' if colour else _muted(ctx)))
    items = []
    for cell, name, colour in pointers:
        angle = (cell % count + 0.5) * step
        x0, y0 = polar(cx, cy, inner - 26, angle)
        x1, y1 = polar(cx, cy, inner - 4, angle)
        out.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{colour}" stroke-width="4"/>'
        )
        out.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="5" fill="{colour}"/>')
        ox, oy = polar(cx, cy, outer + 4, angle)
        items.append((ox, oy, name, ""))
    legend_y = 30
    for first, last, name, colour in fills:
        out.append(f'<rect x="360" y="{legend_y - 12}" width="16" height="16" fill="{colour}"/>')
        out.append(label(384, legend_y + 1, f"{name} ({first}-{last})", SIZE))
        legend_y += 26
    end = _callouts(out, [i for i in items if i[2]], 360, legend_y + 20, 320, ctx, gap=30)
    return _fig(opts, svg(WIDTH, max(cy * 2, end), "".join(out), opts.get("title", "ring buffer"), "chart"))


# ---------------------------------------------------------------------------
# cycle, balance, iceberg
# ---------------------------------------------------------------------------


@block(
    "cycle",
    "stage | detail | colour lines, 3 to 8, in order round a circle",
    "Evaporation | Sun heats the sea | amber\nCondensation | Clouds form | blue\nPrecipitation | Rain and snow | navy\nCollection | Rivers and lakes | green",
)
def cycle_html(code, opts, ctx):
    """Stages round a circle, joined by curved arrows from each to the next."""
    rows = _rows(code, ctx, "cycle", least=3)
    if len(rows) > 8:
        raise PosterError(f"{ctx.where}: a cycle has at most 8 stages")
    cx, cy, r = WIDTH / 2, 190, 140
    n = len(rows)
    box_w, box_h = 150, 54
    out = [
        f'<defs><marker id="cyc-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="{ctx.theme.colours["muted"]}"/></marker></defs>'
    ]
    half = math.degrees(math.atan2(box_w / 2 + 8, r)) * 0.9
    for i in range(n):
        a0, a1 = i * 360 / n + half, (i + 1) * 360 / n - half
        out.append(
            f'<path d="{arc(cx, cy, r, a0, a1)}" fill="none" stroke="{ctx.theme.colours["muted"]}" stroke-width="3" marker-end="url(#cyc-arrow)"/>'
        )
    for i, row in enumerate(rows):
        x, y = polar(cx, cy, r, i * 360 / n)
        colour = _colour(row, 2, ctx)
        out.append(
            f'<rect x="{x - box_w / 2:.1f}" y="{y - box_h / 2:.1f}" width="{box_w}" height="{box_h}" rx="10" fill="{colour}"/>'
        )
        out.append(label(x, y - 4, row[0], SIZE, "middle", WHITE))
        if len(row) > 1 and row[1]:
            for k, part in enumerate(wrap(row[1], box_w - 12, SMALL - 1)[:2]):
                out.append(label(x, y + 12 + k * 12, part, SMALL - 1, "middle", 'fill="#fff"'))
    return _fig(opts, svg(WIDTH, cy * 2 + 10, "".join(out), opts.get("title", "cycle"), "chart"))


@block(
    "balance",
    "left: label | weight | colour and right: label | weight | colour lines; the beam tips to the heavier side",
    "left: Generation | 52 | green\nright: Demand | 50 | red\nright: Losses | 1.5 | grey",
)
def balance_html(code, opts, ctx):
    """A beam on a fulcrum, tipped by the weights on its two pans, each pan's items stacked on it."""
    sides = {"left": [], "right": []}
    for line in _lines(code):
        side, _, rest = line.partition(":")
        side = side.strip().lower()
        if side not in sides:
            raise PosterError(f"{ctx.where}: a balance line starts left: or right:, not '{line}'")
        row = _cells(rest)
        sides[side].append((row[0], _value(row[1] if len(row) > 1 else "1", ctx, "a weight"), _colour(row, 2, ctx)))
    left, right = (sum(w for _, w, _ in sides[s]) for s in ("left", "right"))
    if left + right <= 0:
        raise PosterError(f"{ctx.where}: a balance needs weights above zero")
    tilt = max(-12.0, min(12.0, (right - left) / (left + right) * 60))
    cx, cy, half = WIDTH / 2, 190, 230
    rad = math.radians(tilt)
    ends = {
        "left": (cx - half * math.cos(rad), cy - half * math.sin(rad)),
        "right": (cx + half * math.cos(rad), cy + half * math.sin(rad)),
    }
    out = [
        f'<path d="M{cx - 40},{cy + 110} L{cx},{cy} L{cx + 40},{cy + 110} Z" fill="{ctx.theme.colours["primary"]}"/>',
        f'<line x1="{ends["left"][0]:.1f}" y1="{ends["left"][1]:.1f}" x2="{ends["right"][0]:.1f}" y2="{ends["right"][1]:.1f}" stroke="currentColor" stroke-width="6" stroke-linecap="round"/>',
        f'<circle cx="{cx}" cy="{cy}" r="8" fill="currentColor"/>',
    ]
    for side, (x, y) in ends.items():
        pan_y = y + 50
        out.append(
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{pan_y:.1f}" stroke="currentColor" stroke-width="2"/>'
        )
        out.append(
            f'<path d="M{x - 70:.1f},{pan_y:.1f} L{x + 70:.1f},{pan_y:.1f} L{x + 55:.1f},{pan_y + 10:.1f} L{x - 55:.1f},{pan_y + 10:.1f} Z" fill="currentColor"/>'
        )
        stack_y = pan_y
        total = left if side == "left" else right
        for name, weight, colour in sides[side]:
            h = max(18, 70 * weight / max(left, right))
            out.append(
                f'<rect x="{x - 55:.1f}" y="{stack_y - h:.1f}" width="110" height="{h:.1f}" rx="3" fill="{colour}" stroke="#fff"/>'
            )
            out.append(
                label(x, stack_y - h / 2 + 4, f"{name} {number(weight)}{opts.get('unit', '')}", SMALL, "middle", WHITE)
            )
            stack_y -= h
        out.append(label(x, pan_y + 30, f"{number(total)}{opts.get('unit', '')}", SIZE, "middle", 'font-weight="700"'))
    return _fig(opts, svg(WIDTH, cy + 120, "".join(out), opts.get("title", "balance"), "chart"))


@block(
    "iceberg",
    "above: item and below: item lines; waterline= names the line",
    "above: Features the user sees\nbelow: Device management\nbelow: Security and keys\nbelow: Power budget\nbelow: Firmware updates",
)
def iceberg_html(code, opts, ctx):
    """A small tip above a waterline and a large body below, with the items of each part on it."""
    parts = {"above": [], "below": []}
    for line in _lines(code):
        side, _, rest = line.partition(":")
        if side.strip().lower() not in parts or not rest.strip():
            raise PosterError(f"{ctx.where}: an iceberg line starts above: or below:, not '{line}'")
        parts[side.strip().lower()].append(rest.strip())
    water = 110
    height = water + 50 + max(len(parts["below"]), 3) * 34
    out = [
        f'<rect x="0" y="{water}" width="{WIDTH}" height="{height - water}" fill="{ctx.theme.colours["secondary"]}" fill-opacity=".25"/>',
        f'<path d="M260,{water} L300,20 L335,48 L380,{water} Z" fill="#ffffff" stroke="{ctx.theme.colours["secondary"]}" stroke-width="2"/>',
        f'<path d="M260,{water} L380,{water} L470,{water + 60} L430,{height - 20} L210,{height - 10} L150,{water + 80} Z" fill="#ffffff" fill-opacity=".85" stroke="{ctx.theme.colours["secondary"]}" stroke-width="2"/>',
        f'<line x1="0" y1="{water}" x2="{WIDTH}" y2="{water}" stroke="{ctx.theme.colours["secondary"]}" stroke-width="3"/>',
    ]
    if opts.get("waterline"):
        out.append(
            label(
                WIDTH - 10,
                water - 8,
                opts["waterline"],
                SMALL,
                "end",
                f'fill="{ctx.theme.colours["secondary"]}" font-weight="700"',
            )
        )
    for n, item in enumerate(parts["above"]):
        out.append(label(420 + 0, 40 + n * 22, item, SIZE, extra='font-weight="700"'))
    for n, item in enumerate(parts["below"]):
        out.append(
            label(
                310,
                water + 50 + n * 34,
                item,
                SIZE,
                "middle",
                f'fill="{ctx.theme.colours["strong"]}" font-weight="700"',
            )
        )
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "iceberg"), "chart"))


# Aliases: a cone is a pyramid upside down, an onion is a target
block(
    "cone",
    "As pyramid, wide at the top: label | value | detail | colour lines",
    "Ideas | 400 | Every request | blue\nScoped | 120 | Fits the plan | navy\nBuilt | 30 | Shipped | green",
)(lambda code, opts, ctx: pyramid_html(code, {**opts, "direction": "down"}, ctx))
block(
    "onion",
    "As target: ring | detail | colour lines from the core outwards",
    "Core | The kernel | navy\nShell | The commands | blue",
)(lambda code, opts, ctx: target_html(code, opts, ctx))
