"""Poster blocks for space, optics, atomic, nuclear and particle physics: orbits, telescope ray paths,
interferometers, spacetime diagrams, energy levels, Feynman diagrams, the standard model, element tiles and a chart
of nuclides. Each is SVG drawn with ``poster_svg``.
"""

from __future__ import annotations

import math
import re

from py_doc.poster_blocks import Fragment, PosterError, _whole, block, esc, mark_colour
from py_doc.poster_elements import BY_NUMBER, CATEGORIES, ELEMENTS, configuration_text, shells
from py_doc.poster_scales import wavelength_to_rgb
from py_doc.poster_svg import Linear, label, number, polar, spread, svg, wrap

WIDTH = 640
SIZE = 13
SMALL = 11.5
WHITE = 'fill="#fff" font-weight="700"'


def _lines(code):
    return [line.strip() for line in code.splitlines() if line.strip()]


def _cells(text):
    return [cell.strip() for cell in text.split("|")]


def _fig(opts, picture):
    title = f'<div class="fig-title">{esc(opts["title"])}</div>' if opts.get("title") else ""
    return Fragment(f'<div class="fig">{title}{picture}</div>', picture)


def _num(text, ctx, what):
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        raise PosterError(f"{ctx.where}: {what} '{text}' is not a number") from None


def _kinds(code, ctx, allowed, what):
    """``kind: cells`` lines, each kind one of ``allowed``."""
    out = []
    for line in _lines(code):
        kind, _, rest = line.partition(":")
        kind = kind.strip().lower()
        if kind not in allowed:
            raise PosterError(f"{ctx.where}: a {what} line starts {', '.join(k + ':' for k in allowed)} not '{line}'")
        out.append((kind, _cells(rest)))
    return out


def _arrow_defs(ident, colour, size=7):
    return (
        f'<marker id="{ident}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="{size}" markerHeight="{size}" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 Z" fill="{colour}"/></marker>'
    )


# ---------------------------------------------------------------------------
# orbits
# ---------------------------------------------------------------------------


@block(
    "orbits",
    "orbit: name | radius | colour | e=, transfer: from | to | label, lagrange: name, comet: a | e | label lines; star=, unit=, habitable=from-to, scale=sqrt",
    "orbit: Earth | 1 | blue\norbit: Mars | 1.52 | red\ntransfer: 1 | 1.52 | Hohmann transfer\nlagrange: Earth",
    'star=Sun unit=" AU" habitable=0.95-1.67',
)
def orbits_html(code, opts, ctx):
    """A central body with orbits around it, to scale (or, ``scale=sqrt``, with the inner ones spread out)."""
    items = _kinds(code, ctx, ("orbit", "transfer", "lagrange", "comet"), "orbits")
    orbits = {}
    for kind, cells in items:
        if kind == "orbit":
            e = 0.0
            for cell in cells[3:]:
                if cell.startswith("e="):
                    e = _num(cell[2:], ctx, "an eccentricity")
            orbits[cells[0]] = (
                _num(cells[1], ctx, "a radius"),
                e,
                ctx.theme.colour(
                    cells[2] if len(cells) > 2 and cells[2] and not cells[2].startswith("e=") else None, "secondary"
                ),
            )
    radii = [r * (1 + e) for r, e, _ in orbits.values()]
    for kind, cells in items:
        if kind == "transfer":
            radii += [_num(cells[0], ctx, "a radius"), _num(cells[1], ctx, "a radius")]
        if kind == "comet":
            a, e = _num(cells[0], ctx, "a semi-major axis"), _num(cells[1], ctx, "an eccentricity")
            radii.append(a * (1 + e))
    if opts.get("habitable"):
        m = re.fullmatch(r"\s*([\d.]+)\s*-\s*([\d.]+)\s*", opts["habitable"])
        if not m:
            raise PosterError(f"{ctx.where}: habitable= is 'from-to', such as 0.95-1.67")
        radii.append(float(m[2]))
    if not radii:
        raise PosterError(f"{ctx.where}: an orbits block needs at least one orbit: line")
    sqrt = opts.get("scale", "").lower() == "sqrt"
    big = 190
    top = max(radii)

    def px(r):
        return big * (math.sqrt(r / top) if sqrt else r / top)

    cx, cy = 230, 220
    unit = opts.get("unit", "")
    out = [f"<defs>{_arrow_defs('orb-dv', ctx.theme.colours['bad'])}</defs>"]
    if opts.get("habitable"):
        r0, r1 = px(float(m[1])), px(float(m[2]))
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{(r0 + r1) / 2:.1f}" fill="none" stroke="{ctx.theme.colours["good"]}" stroke-opacity=".2" stroke-width="{r1 - r0:.1f}"/>'
        )
        out.append(
            label(
                cx,
                cy - r1 - 6,
                "Habitable zone",
                SMALL,
                "middle",
                f'fill="{ctx.theme.colours["good"]}" font-weight="700"',
            )
        )
    out.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="#f2a541"/>')
    if opts.get("star"):
        out.append(label(cx, cy + 26, opts["star"], SMALL, "middle", 'font-weight="700"'))
    legend = []
    for n, (name, (r, e, colour)) in enumerate(orbits.items()):
        a = px(r)
        b = a * math.sqrt(1 - e * e)
        out.append(
            f'<ellipse cx="{cx - a * e:.1f}" cy="{cy}" rx="{a:.1f}" ry="{b:.1f}" fill="none" stroke="{colour}" stroke-width="2"/>'
        )
        angle = -40 - n * 37
        x, y = cx - a * e + a * math.cos(math.radians(angle)), cy + b * math.sin(math.radians(angle))
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{colour}"/>')
        out.append(label(x + 9, y - 8, name, SMALL, extra=f'fill="{colour}" font-weight="700"'))
        legend.append((name, f"{number(r)}{unit}" + (f", e = {number(e)}" if e else ""), colour))
    for kind, cells in items:
        if kind == "transfer":
            r1, r2 = px(_num(cells[0], ctx, "a radius")), px(_num(cells[1], ctx, "a radius"))
            a, c = (r1 + r2) / 2, (r2 - r1) / 2
            b = math.sqrt(max(a * a - c * c, 0))
            # the half ellipse from periapsis (right, at r1) to apoapsis (left, at r2), the star at a focus
            out.append(
                f'<path d="M{cx + r1:.1f},{cy} A{a:.1f},{b:.1f} 0 0 0 {cx - r2:.1f},{cy}" fill="none" stroke="{ctx.theme.colours["bad"]}" stroke-width="2" stroke-dasharray="7 4"/>'
            )
            out.append(
                f'<line x1="{cx + r1:.1f}" y1="{cy}" x2="{cx + r1:.1f}" y2="{cy - 36}" stroke="{ctx.theme.colours["bad"]}" stroke-width="3" marker-end="url(#orb-dv)"/>'
            )
            out.append(
                label(cx + r1 + 6, cy - 26, "Δv₁", SIZE, extra=f'fill="{ctx.theme.colours["bad"]}" font-weight="700"')
            )
            out.append(
                f'<line x1="{cx - r2:.1f}" y1="{cy}" x2="{cx - r2:.1f}" y2="{cy + 36}" stroke="{ctx.theme.colours["bad"]}" stroke-width="3" marker-end="url(#orb-dv)"/>'
            )
            out.append(
                label(cx - r2 - 6, cy + 32, "Δv₂", SIZE, "end", f'fill="{ctx.theme.colours["bad"]}" font-weight="700"')
            )
            if len(cells) > 2 and cells[2]:
                legend.append((cells[2], "dashed, burns Δv₁ and Δv₂", ctx.theme.colours["bad"]))
        elif kind == "lagrange":
            if cells[0] not in orbits:
                raise PosterError(f"{ctx.where}: lagrange: {cells[0]} names no orbit")
            r = px(orbits[cells[0]][0])
            points = {"L1": (r * 0.85, 0), "L2": (r * 1.15, 0), "L3": (r, 180), "L4": (r, 60), "L5": (r, -60)}
            for name, (rr, angle) in points.items():
                x, y = cx + rr * math.cos(math.radians(angle)), cy - rr * math.sin(math.radians(angle))
                out.append(
                    f'<path d="M{x - 5:.1f},{y:.1f} L{x + 5:.1f},{y:.1f} M{x:.1f},{y - 5:.1f} L{x:.1f},{y + 5:.1f}" stroke="currentColor" stroke-width="2"/>'
                )
                out.append(label(x + 6, y + 14, name, SMALL - 1, extra='font-weight="700"'))
        elif kind == "comet":
            a_au, e = _num(cells[0], ctx, "a semi-major axis"), _num(cells[1], ctx, "an eccentricity")
            a = px(a_au)
            b = a * math.sqrt(max(1 - e * e, 0))
            ox = cx - a * e
            out.append(
                f'<ellipse cx="{ox:.1f}" cy="{cy}" rx="{a:.1f}" ry="{b:.1f}" fill="none" stroke="currentColor" stroke-dasharray="2 4"/>'
            )
            px_, py_ = ox + a * math.cos(math.radians(30)), cy + b * math.sin(math.radians(30))
            # the ion tail points straight away from the star; the dust tail curves behind
            dx, dy = px_ - cx, py_ - cy
            d = math.hypot(dx, dy) or 1
            out.append(
                f'<line x1="{px_:.1f}" y1="{py_:.1f}" x2="{px_ + dx / d * 60:.1f}" y2="{py_ + dy / d * 60:.1f}" stroke="#4cc9f0" stroke-width="3"/>'
            )
            out.append(
                f'<path d="M{px_:.1f},{py_:.1f} Q{px_ + dx / d * 30 + 20:.1f},{py_ + dy / d * 30 - 20:.1f} {px_ + dx / d * 50 + 30:.1f},{py_ + dy / d * 50 - 35:.1f}" stroke="#f2c27a" stroke-width="5" fill="none" stroke-linecap="round"/>'
            )
            out.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="5" fill="#fff" stroke="currentColor"/>')
            legend.append(
                (
                    cells[2] if len(cells) > 2 and cells[2] else "Comet",
                    "ion tail (blue) away from the star, dust tail (gold) curved",
                    "#4cc9f0",
                )
            )
    y = 30
    for name, text, colour in legend:
        out.append(f'<rect x="460" y="{y - 11}" width="14" height="14" rx="7" fill="{colour}"/>')
        out.append(label(482, y, name, SIZE, extra='font-weight="700"'))
        for k, part in enumerate(wrap(text, 150, SMALL)[:2]):
            out.append(label(482, y + 14 + k * 13, part, SMALL, extra=f'fill="{ctx.theme.colours["muted"]}"'))
        y += 46
    return _fig(opts, svg(WIDTH, cy * 2, "".join(out), opts.get("title", "orbits"), "chart"))


# ---------------------------------------------------------------------------
# optics and interferometer
# ---------------------------------------------------------------------------

OPTICS = ("refractor", "newtonian", "cassegrain", "tma")


@block(
    "optics",
    "type=refractor|newtonian|cassegrain|tma: the ray path of a telescope, with its parts labelled",
    "",
    "type=cassegrain",
)
def optics_html(code, opts, ctx):
    kind = opts.get("type", "refractor").lower()
    if kind not in OPTICS:
        raise PosterError(f"{ctx.where}: optics type must be one of {', '.join(OPTICS)}, not '{kind}'")
    ray = ctx.theme.colours["accent"]
    glass = ctx.theme.colours["secondary"]
    out = []
    tube = ctx.theme.colours["muted"]
    top, bottom, h = 60, 180, 240
    ys = (75, 120, 165)  # three rays of a distant star

    def rays(points_for):
        for y in ys:
            pts = " ".join(f"{x:.1f},{yy:.1f}" for x, yy in points_for(y))
            out.append(f'<polyline points="{pts}" fill="none" stroke="{ray}" stroke-width="2"/>')

    out.append(
        f'<rect x="90" y="{top}" width="440" height="{bottom - top}" fill="none" stroke="{tube}" stroke-width="2" rx="4"/>'
    )
    parts = []
    if kind == "refractor":
        out.append(
            f'<ellipse cx="100" cy="120" rx="10" ry="62" fill="{glass}" fill-opacity=".45" stroke="{glass}" stroke-width="2"/>'
        )
        rays(lambda y: [(10, y), (100, y), (500, 120), (560, 120 + (120 - y) * 0.3)])
        parts = [(100, 52, "Objective lens"), (500, 196, "Focus"), (560, 52, "Eyepiece")]
        out.append(f'<rect x="540" y="105" width="22" height="30" rx="4" fill="{tube}"/>')
    elif kind == "newtonian":
        out.append(f'<path d="M525,62 Q512,120 525,178" fill="none" stroke="{glass}" stroke-width="6"/>')
        out.append(f'<line x1="180" y1="105" x2="210" y2="135" stroke="{glass}" stroke-width="6"/>')
        rays(lambda y: [(10, y), (520, y), (195, 120), (195, 20)])
        out.append(f'<rect x="183" y="10" width="24" height="18" rx="3" fill="{tube}"/>')
        parts = [(525, 196, "Primary mirror"), (195, 150, "Flat secondary"), (230, 22, "Eyepiece at the side")]
    elif kind == "cassegrain":
        out.append(
            f'<path d="M500,62 Q488,120 500,178 M500,108 L500,132" fill="none" stroke="{glass}" stroke-width="6"/>'
        )
        out.append(f'<path d="M210,105 Q216,120 210,135" fill="none" stroke="{glass}" stroke-width="6"/>')
        rays(lambda y: [(10, y), (495, y), (213, 120 + (y - 120) * 0.15), (600, 120)])
        out.append(f'<rect x="590" y="108" width="24" height="24" rx="3" fill="{tube}"/>')
        parts = [
            (500, 196, "Primary mirror, with a hole"),
            (210, 196, "Convex secondary"),
            (560, 52, "Focus, behind it"),
        ]
    else:  # tma: three mirrors, folded
        out.append(f'<path d="M500,62 Q488,120 500,178" fill="none" stroke="{glass}" stroke-width="6"/>')
        out.append(f'<path d="M210,100 Q216,120 210,140" fill="none" stroke="{glass}" stroke-width="6"/>')
        out.append(f'<path d="M420,190 Q440,205 460,190" fill="none" stroke="{glass}" stroke-width="6"/>')
        rays(lambda y: [(10, y), (495, y), (213, 120 + (y - 120) * 0.2), (440, 197), (560, 225)])
        out.append(f'<rect x="555" y="215" width="40" height="18" rx="3" fill="{tube}"/>')
        parts = [(500, 52, "Primary"), (210, 196, "Secondary"), (440, 232, "Tertiary"), (575, 205, "Detector")]
    for x, y, text in parts:
        out.append(label(x, y, text, SMALL, "middle", 'font-weight="700"'))
    out.append(label(20, 70, "Starlight", SMALL, extra=f'fill="{ray}" font-weight="700"'))
    return _fig(opts, svg(WIDTH, h, "".join(out), opts.get("title", f"{kind} telescope"), "chart"))


@block(
    "interferometer",
    "type=michelson|fabry-perot: the beam paths, with the arms and detector labelled; arm= names the arms",
    "",
    'type=michelson arm="4 km"',
)
def interferometer_html(code, opts, ctx):
    kind = opts.get("type", "michelson").lower()
    if kind not in ("michelson", "fabry-perot"):
        raise PosterError(f"{ctx.where}: interferometer type must be michelson or fabry-perot, not '{kind}'")
    beam = "#d62828"
    out = [f"<defs>{_arrow_defs('ifo-arrow', beam)}</defs>"]
    if kind == "michelson":
        out += [
            f'<rect x="20" y="180" width="60" height="30" rx="4" fill="{ctx.theme.colours["primary"]}"/>',
            label(50, 230, "Laser", SMALL, "middle", 'font-weight="700"'),
            f'<line x1="80" y1="195" x2="230" y2="195" stroke="{beam}" stroke-width="3" marker-end="url(#ifo-arrow)"/>',
            '<line x1="225" y1="170" x2="265" y2="220" stroke="#4a7fc1" stroke-width="6"/>',
            label(245, 245, "Beam splitter", SMALL, "middle", 'font-weight="700"'),
            f'<line x1="245" y1="195" x2="560" y2="195" stroke="{beam}" stroke-width="3" stroke-opacity=".8"/>',
            f'<line x1="245" y1="195" x2="245" y2="30" stroke="{beam}" stroke-width="3" stroke-opacity=".8"/>',
            f'<rect x="560" y="170" width="14" height="50" fill="{ctx.theme.colours["muted"]}"/>',
            f'<rect x="220" y="16" width="50" height="14" fill="{ctx.theme.colours["muted"]}"/>',
            label(567, 238, "Test mass", SMALL, "middle"),
            label(290, 27, "Test mass", SMALL),
            f'<line x1="245" y1="195" x2="245" y2="300" stroke="{beam}" stroke-width="3" marker-end="url(#ifo-arrow)" stroke-dasharray="6 3"/>',
            f'<rect x="225" y="300" width="40" height="22" rx="4" fill="{ctx.theme.colours["strong"]}"/>',
            label(275, 316, "Photodetector: the arms interfere here", SMALL, extra='font-weight="700"'),
        ]
        arm = opts.get("arm", "")
        if arm:
            out.append(label(400, 185, arm, SMALL, "middle", f'fill="{ctx.theme.colours["muted"]}"'))
            out.append(label(232, 110, arm, SMALL, "end", f'fill="{ctx.theme.colours["muted"]}"'))
        height = 340
    else:
        out += [
            f'<rect x="20" y="90" width="60" height="30" rx="4" fill="{ctx.theme.colours["primary"]}"/>',
            label(50, 140, "Laser", SMALL, "middle", 'font-weight="700"'),
            '<rect x="200" y="50" width="10" height="110" fill="#4a7fc1"/>',
            '<rect x="420" y="50" width="10" height="110" fill="#4a7fc1"/>',
            label(
                315, 40, "Partly silvered mirrors: the light bounces between them", SMALL, "middle", 'font-weight="700"'
            ),
            f'<line x1="80" y1="105" x2="200" y2="105" stroke="{beam}" stroke-width="3" marker-end="url(#ifo-arrow)"/>',
        ]
        for k in range(6):
            y = 70 + k * 12
            out.append(
                f'<line x1="210" y1="{y}" x2="420" y2="{y + 6}" stroke="{beam}" stroke-width="1.5" stroke-opacity=".7"/>'
            )
        out += [
            f'<line x1="430" y1="105" x2="560" y2="105" stroke="{beam}" stroke-width="3" marker-end="url(#ifo-arrow)"/>',
            f'<rect x="560" y="92" width="40" height="26" rx="4" fill="{ctx.theme.colours["strong"]}"/>',
            label(580, 140, "Detector", SMALL, "middle", 'font-weight="700"'),
        ]
        height = 170
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", f"{kind} interferometer"), "chart"))


# ---------------------------------------------------------------------------
# spacetime
# ---------------------------------------------------------------------------


@block(
    "spacetime",
    "mode=lightcone: worldline: label | speed (fraction of c) | colour and event: x | ct | label lines; mode=well: body | depth | colour lines; mode=penrose",
    "worldline: At rest | 0 | navy\nworldline: Half light speed | 0.5 | blue\nevent: 1.5 | 0.6 | Outside the cone: no cause can reach it",
    "mode=lightcone",
)
def spacetime_html(code, opts, ctx):
    mode = opts.get("mode", "lightcone").lower()
    if mode not in ("lightcone", "well", "penrose"):
        raise PosterError(f"{ctx.where}: spacetime mode must be lightcone, well or penrose, not '{mode}'")
    return _fig(opts, {"lightcone": _lightcone, "well": _well, "penrose": _penrose}[mode](code, opts, ctx))


def _lightcone(code, opts, ctx):
    cx, cy, s = 250, 200, 170
    out = [f"<defs>{_arrow_defs('st-arrow', 'currentColor')}</defs>"]
    future, past = ctx.theme.colours["secondary"], ctx.theme.colours["accent"]
    out.append(f'<path d="M{cx},{cy} L{cx - s},{cy - s} L{cx + s},{cy - s} Z" fill="{future}" fill-opacity=".18"/>')
    out.append(f'<path d="M{cx},{cy} L{cx - s},{cy + s} L{cx + s},{cy + s} Z" fill="{past}" fill-opacity=".18"/>')
    out.append(
        f'<path d="M{cx - s},{cy - s} L{cx + s},{cy + s} M{cx + s},{cy - s} L{cx - s},{cy + s}" stroke="currentColor" stroke-opacity=".5"/>'
    )
    out.append(
        f'<line x1="{cx - s - 10}" y1="{cy}" x2="{cx + s + 14}" y2="{cy}" stroke="currentColor" marker-end="url(#st-arrow)"/>'
    )
    out.append(
        f'<line x1="{cx}" y1="{cy + s + 10}" x2="{cx}" y2="{cy - s - 14}" stroke="currentColor" marker-end="url(#st-arrow)"/>'
    )
    out.append(label(cx + s + 18, cy + 4, "x", SIZE, extra='font-weight="700"'))
    out.append(label(cx + 6, cy - s - 14, "ct", SIZE, extra='font-weight="700"'))
    out.append(label(cx, cy - s + 26, "Future", SIZE, "middle", f'fill="{future}" font-weight="700"'))
    out.append(label(cx, cy + s - 14, "Past", SIZE, "middle", f'fill="{past}" font-weight="700"'))
    out.append(label(cx + s - 30, cy - 10, "Elsewhere", SMALL, "middle", f'fill="{ctx.theme.colours["muted"]}"'))
    unit = s / 2  # ct and x in the same unit: light lines are at 45 degrees
    for kind, cells in _kinds(code, ctx, ("worldline", "event"), "lightcone"):
        if kind == "worldline":
            v = _num(cells[1] if len(cells) > 1 else "0", ctx, "a speed")
            if not -1 < v < 1:
                raise PosterError(
                    f"{ctx.where}: a worldline speed is a fraction of c between -1 and 1, not {number(v)}"
                )
            colour = ctx.theme.colour(cells[2] if len(cells) > 2 and cells[2] else None, "primary")
            out.append(
                f'<line x1="{cx - v * s:.1f}" y1="{cy + s}" x2="{cx + v * s:.1f}" y2="{cy - s}" stroke="{colour}" stroke-width="3"/>'
            )
            out.append(label(cx + v * s + 6, cy - s + 12, cells[0], SMALL, extra=f'fill="{colour}" font-weight="700"'))
        else:
            x, t = _num(cells[0], ctx, "an x"), _num(cells[1], ctx, "a ct")
            ex, ey = cx + x * unit, cy - t * unit
            out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5" fill="{ctx.theme.colours["bad"]}"/>')
            for k, part in enumerate(wrap(cells[2] if len(cells) > 2 else "", 140, SMALL)[:3]):
                out.append(label(ex + 8, ey + 4 + k * 13, part, SMALL, extra=f'fill="{ctx.theme.colours["bad"]}"'))
    return svg(WIDTH, cy * 2, "".join(out), opts.get("title", "light cone"), "chart")


def _well(code, opts, ctx):
    rows = [_cells(line) for line in _lines(code)]
    if not rows:
        raise PosterError(f"{ctx.where}: a potential well needs 'body | depth' lines")
    depths = [_num(r[1] if len(r) > 1 else "1", ctx, "a depth") for r in rows]
    log = opts.get("scale", "").lower() == "log"
    shown = [math.log10(d + 1) for d in depths] if log else depths
    deepest = max(shown) or 1
    slot = WIDTH / len(rows)
    top, depth_px, lines, samples = 34, 220, 15, 60
    out = []
    for n, (row, d) in enumerate(zip(rows, shown)):
        cx = slot * (n + 0.5)
        h = depth_px * d / deepest
        colour = ctx.theme.colour(row[2] if len(row) > 2 and row[2] else None, "secondary")
        half = slot * 0.46
        # a sheet seen from above and in front, sagging under the body: the deeper the well, the narrower its
        # throat, as a compact body's is
        throat = 0.5 - 0.26 * d / deepest

        def point(u, v, cx=cx, half=half, h=h, throat=throat):
            sag = h * throat**2 / (u * u + v * v + throat**2)
            sag -= h * throat**2 / (2 + throat**2)  # the corners stay on the flat sheet
            scale = 0.82 + 0.18 * (v + 1) / 2  # nearer is wider
            return cx + u * half * scale, top + 22 + v * 20 + max(sag, 0)

        steps = [-1 + 2 * k / samples for k in range(samples + 1)]
        for k in range(lines):
            g = -1 + 2 * k / (lines - 1)
            for curve in ([point(t, g) for t in steps], [point(g, t) for t in steps]):
                path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in curve)
                out.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-opacity=".75" stroke-width="1.2"/>')
        x, y = point(0, 0)
        out.append(f'<circle cx="{x:.1f}" cy="{y - 7:.1f}" r="8" fill="{colour}" stroke="#fff" stroke-width="1.5"/>')
        out.append(label(cx, top + depth_px + 60, row[0], SIZE, "middle", 'font-weight="700"'))
    return svg(WIDTH, top + depth_px + 72, "".join(out), opts.get("title", "potential wells"), "chart")


def _penrose(code, opts, ctx):
    cx, cy, s = 220, 200, 170
    muted = f'fill="{ctx.theme.colours["muted"]}"'
    out = [
        f'<path d="M{cx},{cy - s} L{cx + s},{cy} L{cx},{cy + s} L{cx - s},{cy} Z" fill="{ctx.theme.colours["secondary"]}" fill-opacity=".12" stroke="currentColor" stroke-width="2"/>',
        label(cx, cy - s - 8, "i⁺ future timelike infinity", SMALL, "middle", 'font-weight="700"'),
        label(cx, cy + s + 18, "i⁻ past timelike infinity", SMALL, "middle", 'font-weight="700"'),
        label(cx + s + 8, cy + 4, "i⁰ spatial infinity", SMALL, extra='font-weight="700"'),
        label(cx + s / 2 + 14, cy - s / 2 - 4, "ℐ⁺ future null infinity", SMALL, extra=muted),
        label(cx + s / 2 + 14, cy + s / 2 + 12, "ℐ⁻ past null infinity", SMALL, extra=muted),
    ]
    if opts.get("blackhole", "no").lower() in ("yes", "true"):
        bad = ctx.theme.colours["bad"]
        out += [
            f'<path d="M{cx - s / 2:.1f},{cy - s / 2:.1f} L{cx + s / 2:.1f},{cy - s / 2:.1f}" stroke="{bad}" stroke-width="5" stroke-dasharray="2 5" stroke-linecap="round"/>',
            label(cx, cy - s / 2 - 10, "Singularity, r = 0", SMALL, "middle", f'fill="{bad}" font-weight="700"'),
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + s / 2:.1f}" y2="{cy - s / 2:.1f}" stroke="{bad}" stroke-width="2.5"/>',
            label(cx + 20, cy - 34, "Event horizon", SMALL, extra=f'fill="{bad}" font-weight="700"'),
            label(cx - 30, cy - s / 2 + 30, "Inside", SMALL, "middle", muted),
        ]
    out.append(
        f'<line x1="{cx}" y1="{cy + s}" x2="{cx}" y2="{cy - s}" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="4 4"/>'
    )
    return svg(WIDTH, cy * 2 + 28, "".join(out), opts.get("title", "Penrose diagram"), "chart")


# ---------------------------------------------------------------------------
# energy levels
# ---------------------------------------------------------------------------


@block(
    "energy-levels",
    "level: name | energy in eV lines, and jump: from | to | label lines (up absorbs, down emits, coloured by wavelength)",
    "level: n=1 | -13.6\nlevel: n=2 | -3.4\nlevel: n=3 | -1.51\nlevel: n=4 | -0.85\njump: n=3 | n=2 | Hα\njump: n=4 | n=2 | Hβ\njump: n=1 | n=2 | Lyman α",
)
def energy_levels_html(code, opts, ctx):
    """Energy levels as rungs, with absorption arrows straight up and emission arrows wavy down, each in the colour
    of its light (ΔE in eV gives λ = 1239.84 / ΔE nm) or grey outside what the eye sees."""
    levels, jumps = {}, []
    for kind, cells in _kinds(code, ctx, ("level", "jump"), "energy-levels"):
        if kind == "level":
            levels[cells[0]] = _num(cells[1] if len(cells) > 1 else "", ctx, "an energy")
        else:
            if len(cells) < 2:
                raise PosterError(f"{ctx.where}: a jump is 'jump: from | to | label'")
            jumps.append((cells[0], cells[1], cells[2] if len(cells) > 2 else ""))
    if len(levels) < 2:
        raise PosterError(f"{ctx.where}: energy-levels needs at least two level: lines")
    for a, b, _ in jumps:
        for name in (a, b):
            if name not in levels:
                raise PosterError(f"{ctx.where}: the jump names the level '{name}', which no level: line has")
    low, high = min(levels.values()), max(levels.values())
    top, height = 20, 300
    y_of = Linear(low, high if high > low else low + 1, top + height, top)
    out = []
    left, right = 120, 420
    names = list(levels)
    # levels close in energy (hydrogen's upper ones) get their labels spread apart, joined by short leaders
    spots = spread([y_of(levels[name]) for name in names], 16, top, top + height)
    for name, ty in zip(names, spots):
        y = y_of(levels[name])
        out.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="currentColor" stroke-width="2.5"/>'
        )
        if abs(ty - y) > 1:
            out.append(
                f'<path d="M{left - 2},{y:.1f} L{left - 10},{ty:.1f} M{right + 2},{y:.1f} L{right + 10},{ty:.1f}" stroke="currentColor" stroke-opacity=".4" fill="none"/>'
            )
        out.append(label(left - 14, ty + 4, name, SIZE, "end", 'font-weight="700"'))
        out.append(
            label(right + 14, ty + 4, f"{number(levels[name])} eV", SMALL, extra=f'fill="{ctx.theme.colours["muted"]}"')
        )
    xs = [left + 30 + n * (right - left - 60) / max(len(jumps) - 1, 1) for n in range(len(jumps))]
    key = set()  # the kinds of arrow drawn, explained in the key
    for x, (a, b, text) in zip(xs, jumps):
        ya, yb = y_of(levels[a]), y_of(levels[b])
        delta = abs(levels[b] - levels[a])
        nm = 1239.84 / delta if delta else 0
        colour = wavelength_to_rgb(nm) if 380 <= nm <= 750 else ctx.theme.colours["muted"]
        key.add(0 if levels[b] > levels[a] else 1)
        if not 380 <= nm <= 750:
            key.add(2)
        if levels[b] > levels[a]:  # absorption: a straight arrow up
            out.append(
                f'<line x1="{x:.1f}" y1="{ya:.1f}" x2="{x:.1f}" y2="{yb + 8:.1f}" stroke="{colour}" stroke-width="3"/>'
            )
            out.append(
                f'<path d="M{x - 6:.1f},{yb + 10:.1f} L{x:.1f},{yb:.1f} L{x + 6:.1f},{yb + 10:.1f}" fill="{colour}"/>'
            )
        else:  # emission: a wavy arrow down
            steps = max(int(abs(yb - ya) / 8), 2)
            path = f"M{x:.1f},{ya:.1f}"
            for k in range(1, steps + 1):
                yk = ya + (yb - 8 - ya) * k / steps
                path += (
                    f" Q{x + (5 if k % 2 else -5):.1f},{ya + (yb - 8 - ya) * (k - 0.5) / steps:.1f} {x:.1f},{yk:.1f}"
                )
            out.append(f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
            out.append(
                f'<path d="M{x - 6:.1f},{yb - 10:.1f} L{x:.1f},{yb:.1f} L{x + 6:.1f},{yb - 10:.1f}" fill="{colour}"/>'
            )
        tag = f"{text} {number(round(nm, 1))} nm".strip() if nm else text
        out.append(
            label(
                x,
                min(ya, yb) + abs(yb - ya) / 2,
                tag,
                SMALL - 1,
                "middle",
                'font-weight="700" paint-order="stroke" stroke="#fff" stroke-width="3"',
            )
        )
    out += _energy_key(key, ctx, x=500, y=top + 4)
    return _fig(opts, svg(WIDTH, top + height + 20, "".join(out), opts.get("title", "energy levels"), "chart"))


def _energy_key(kinds, ctx, x, y):
    """The key of an energy-level diagram, beside it: a sample of each kind of arrow drawn (0 absorbed, 1 emitted)
    with what it means, then the colours: a strip of the visible spectrum, and grey for light that is not."""
    muted = ctx.theme.colours["muted"]
    out = [label(x, y + 10, "Key", SMALL, extra='font-weight="700"')]
    y += 30
    if 0 in kinds:
        out.append(f'<line x1="{x + 8}" y1="{y + 10}" x2="{x + 8}" y2="{y - 6}" stroke="{muted}" stroke-width="2.5"/>')
        out.append(f'<path d="M{x + 3},{y - 4} L{x + 8},{y - 12} L{x + 13},{y - 4}" fill="{muted}"/>')
        out.append(label(x + 24, y + 4, "Absorbed: up, straight", SMALL - 1))
        y += 30
    if 1 in kinds:
        wave = f"M{x + 8},{y - 12}" + "".join(f" q{4 if k % 2 else -4},3 0,6" for k in range(3))
        out.append(f'<path d="{wave}" fill="none" stroke="{muted}" stroke-width="2"/>')
        out.append(f'<path d="M{x + 3},{y + 4} L{x + 8},{y + 12} L{x + 13},{y + 4}" fill="{muted}"/>')
        out.append(label(x + 24, y + 4, "Emitted: down, wavy", SMALL - 1))
        y += 30
    stops = "".join(
        f'<stop offset="{(nm - 380) / 370:.2f}" stop-color="{wavelength_to_rgb(nm)}"/>' for nm in range(380, 751, 30)
    )
    out.append(f'<defs><linearGradient id="energy-spectrum">{stops}</linearGradient></defs>')
    out.append(f'<rect x="{x}" y="{y - 8}" width="120" height="10" fill="url(#energy-spectrum)"/>')
    out.append(label(x, y + 14, "380 nm", SMALL - 3, extra=f'fill="{muted}"'))
    out.append(label(x + 120, y + 14, "750 nm", SMALL - 3, "end", f'fill="{muted}"'))
    out.append(label(x, y + 30, "The colour of its light", SMALL - 1))
    if 2 in kinds:
        y += 52
        out.append(f'<rect x="{x}" y="{y - 8}" width="16" height="10" fill="{muted}"/>')
        out.append(label(x + 24, y + 2, "Ultraviolet or infrared,", SMALL - 1))
        out.append(label(x + 24, y + 16, "not visible", SMALL - 1))
    return out


# ---------------------------------------------------------------------------
# Feynman diagrams, from preset topologies
# ---------------------------------------------------------------------------

# Each topology: its vertices, and its lines as (from, to, kind, slot); a slot is what a label line names
TOPOLOGIES = {
    "s-channel": ({"a": (80, 60), "b": (80, 260), "v1": (220, 160), "v2": (420, 160), "c": (560, 60), "d": (560, 260)},
                  [("a", "v1", "fermion", "in1"), ("b", "v1", "antifermion", "in2"), ("v1", "v2", "photon", "mid"),
                   ("v2", "c", "fermion", "out1"), ("v2", "d", "antifermion", "out2")]),
    "t-channel": ({"a": (80, 60), "b": (80, 260), "v1": (320, 80), "v2": (320, 240), "c": (560, 60), "d": (560, 260)},
                  [("a", "v1", "fermion", "in1"), ("v1", "c", "fermion", "out1"), ("v1", "v2", "photon", "mid"),
                   ("b", "v2", "fermion", "in2"), ("v2", "d", "fermion", "out2")]),
    "u-channel": ({"a": (80, 60), "b": (80, 260), "v1": (320, 80), "v2": (320, 240), "c": (560, 60), "d": (560, 260)},
                  [("a", "v1", "fermion", "in1"), ("v1", "d", "fermion", "out2"), ("v1", "v2", "photon", "mid"),
                   ("b", "v2", "fermion", "in2"), ("v2", "c", "fermion", "out1")]),
    "decay": ({"a": (80, 160), "v1": (300, 160), "c": (540, 60), "d": (540, 260)},
              [("a", "v1", "scalar", "in1"), ("v1", "c", "fermion", "out1"), ("v1", "d", "antifermion", "out2")]),
    "beta-decay": ({"a": (80, 230), "v1": (260, 230), "c": (560, 280), "v2": (400, 110), "e": (560, 50), "n": (560, 170)},
                   [("a", "v1", "fermion", "in1"), ("v1", "c", "fermion", "out1"), ("v1", "v2", "boson", "mid"),
                    ("v2", "e", "fermion", "out2"), ("n", "v2", "fermion", "out3")]),
    "compton": ({"a": (80, 230), "b": (80, 60), "v1": (230, 200), "v2": (410, 120), "c": (560, 260), "d": (560, 60)},
                [("a", "v1", "fermion", "in1"), ("b", "v1", "photon", "in2"), ("v1", "v2", "fermion", "mid"),
                 ("v2", "c", "fermion", "out1"), ("v2", "d", "photon", "out2")]),
    "annihilation": ({"a": (80, 60), "b": (80, 260), "v1": (300, 100), "v2": (300, 220), "c": (560, 60), "d": (560, 260)},
                     [("a", "v1", "fermion", "in1"), ("v1", "v2", "fermion", "mid"), ("v2", "b", "fermion", "in2"),
                      ("v1", "c", "photon", "out1"), ("v2", "d", "photon", "out2")]),
    "loop": ({"a": (60, 160), "v1": (220, 160), "v2": (420, 160), "c": (580, 160)},
             [("a", "v1", "photon", "in1"), ("v1", "v2", "loop", "mid"), ("v2", "c", "photon", "out1")]),
    "penguin": ({"a": (60, 270), "v1": (200, 270), "v2": (440, 270), "c": (580, 270), "v3": (320, 150), "d": (320, 40)},
                [("a", "v1", "fermion", "in1"), ("v1", "v2", "fermion", "mid"), ("v2", "c", "fermion", "out1"),
                 ("v1", "v3", "boson", "loop1"), ("v3", "v2", "boson", "loop2"), ("v3", "d", "gluon", "out2")]),
    "box": ({"a": (60, 60), "b": (60, 260), "v1": (220, 80), "v2": (420, 80), "v3": (420, 240), "v4": (220, 240), "c": (580, 60), "d": (580, 260)},
            [("a", "v1", "fermion", "in1"), ("v1", "v2", "boson", "top"), ("v2", "c", "fermion", "out1"),
             ("b", "v4", "fermion", "in2"), ("v4", "v3", "boson", "bottom"), ("v3", "d", "fermion", "out2"),
             ("v1", "v4", "fermion", "left"), ("v2", "v3", "fermion", "right")]),
}  # fmt: skip
LINE_KINDS = ("fermion", "antifermion", "photon", "boson", "gluon", "scalar", "loop")


def _wave(x0, y0, x1, y1, amplitude=6, period=14):
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(int(length / period), 2)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    path = f"M{x0:.1f},{y0:.1f}"
    for k in range(1, n + 1):
        mx, my = x0 + ux * length * (k - 0.5) / n, y0 + uy * length * (k - 0.5) / n
        side = amplitude if k % 2 else -amplitude
        ex, ey = x0 + ux * length * k / n, y0 + uy * length * k / n
        path += f" Q{mx - uy * side * 2:.1f},{my + ux * side * 2:.1f} {ex:.1f},{ey:.1f}"
    return path


def _coil(x0, y0, x1, y1, radius=6):
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(int(length / (radius * 1.6)), 3)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    points = []
    for k in range(n * 12 + 1):
        t = k / (n * 12)
        angle = t * n * 2 * math.pi
        along = t * length - radius * math.cos(angle) + radius
        across = radius * math.sin(angle)
        along = along * (length / (length + 2 * radius))
        points.append(f"{x0 + ux * along - uy * across:.1f},{y0 + uy * along + ux * across:.1f}")
    return "M" + " L".join(points)


def _crossed(p, q, segments):
    """Whether another of ``segments`` crosses the segment p-q in its middle third."""
    (x0, y0), (x1, y1) = p, q
    for (x2, y2), (x3, y3) in segments:
        den = (x1 - x0) * (y3 - y2) - (y1 - y0) * (x3 - x2)
        if not den or {p, q} & {(x2, y2), (x3, y3)}:
            continue
        t = ((x2 - x0) * (y3 - y2) - (y2 - y0) * (x3 - x2)) / den
        u = ((x2 - x0) * (y1 - y0) - (y2 - y0) * (x1 - x0)) / den
        if 1 / 3 < t < 2 / 3 and 0 < u < 1:
            return True
    return False


@block(
    "feynman",
    "topology= s-channel|t-channel|u-channel|decay|beta-decay|compton|annihilation|loop|penguin|box; slot: label | line kind lines (in1, in2, mid, out1, out2...)",
    "in1: e⁻\nin2: e⁺\nmid: γ\nout1: μ⁻\nout2: μ⁺",
    "topology=s-channel",
)
def feynman_html(code, opts, ctx):
    """A Feynman diagram of a preset topology: fermions with arrows, photons and W/Z bosons as waves, gluons as
    coils, scalars dashed, and each line labelled by its slot."""
    topology = opts.get("topology", "s-channel").lower()
    if topology not in TOPOLOGIES:
        raise PosterError(f"{ctx.where}: feynman topology must be one of {', '.join(TOPOLOGIES)}, not '{topology}'")
    vertices, lines = TOPOLOGIES[topology]
    labels, kinds = {}, {}
    slots = {slot for *_, slot in lines}
    for line in _lines(code):
        slot, _, rest = line.partition(":")
        slot = slot.strip().lower()
        if slot not in slots:
            raise PosterError(
                f"{ctx.where}: the {topology} topology has the slots {', '.join(sorted(slots))}, not '{slot}'"
            )
        cells = _cells(rest)
        labels[slot] = cells[0]
        if len(cells) > 1 and cells[1]:
            if cells[1].lower() not in LINE_KINDS:
                raise PosterError(f"{ctx.where}: a line kind is one of {', '.join(LINE_KINDS)}, not '{cells[1]}'")
            kinds[slot] = cells[1].lower()
    colour = ctx.theme.colours["strong"]
    accent = mark_colour(ctx.theme)  # the print theme's secondary is a pale box colour, unseen as a line
    out = [f"<defs>{_arrow_defs('fey-arrow', colour)}</defs>"]
    for a, b, kind, slot in lines:
        kind = kinds.get(slot, kind)
        (x0, y0), (x1, y1) = vertices[a], vertices[b]
        # where along the line its arrow and label go: half way, unless another line crosses it there, as the
        # outgoing lines of the u-channel do, when they go three quarters of the way, clear of the crossing
        at = 0.78 if _crossed((x0, y0), (x1, y1), [(vertices[c], vertices[d]) for c, d, *_ in lines]) else 0.5
        if kind in ("fermion", "antifermion"):
            out.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{colour}" stroke-width="2.5"/>')
            mx, my = x0 + (x1 - x0) * at, y0 + (y1 - y0) * at
            dx, dy = (x1 - x0), (y1 - y0)
            if kind == "antifermion":  # the arrow against the line: an antiparticle forward in time
                dx, dy = -dx, -dy
            d = math.hypot(dx, dy) or 1
            out.append(
                f'<line x1="{mx - dx / d * 8:.1f}" y1="{my - dy / d * 8:.1f}" x2="{mx + dx / d * 4:.1f}" y2="{my + dy / d * 4:.1f}" stroke="{colour}" stroke-width="2.5" marker-end="url(#fey-arrow)"/>'
            )
        elif kind in ("photon", "boson"):
            out.append(f'<path d="{_wave(x0, y0, x1, y1)}" fill="none" stroke="{accent}" stroke-width="2.5"/>')
        elif kind == "gluon":
            out.append(
                f'<path d="{_coil(x0, y0, x1, y1)}" fill="none" stroke="{ctx.theme.colours["good"]}" stroke-width="2"/>'
            )
        elif kind == "scalar":
            out.append(
                f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{colour}" stroke-width="2.5" stroke-dasharray="8 5"/>'
            )
        else:  # loop: a circle between the two vertices
            r = math.hypot(x1 - x0, y1 - y0) / 2
            out.append(
                f'<circle cx="{(x0 + x1) / 2:.1f}" cy="{(y0 + y1) / 2:.1f}" r="{r:.1f}" fill="none" stroke="{colour}" stroke-width="2.5"/>'
            )
        if slot in labels:
            mx, my = x0 + (x1 - x0) * at, y0 + (y1 - y0) * at
            dx, dy = x1 - x0, y1 - y0
            d = math.hypot(dx, dy) or 1
            offset = 18 if kind != "loop" else math.hypot(dx, dy) / 2 + 16
            out.append(
                label(
                    mx - dy / d * offset,
                    my + dx / d * offset + 5,
                    labels[slot],
                    SIZE + 2,
                    "middle",
                    'font-weight="700"',
                )
            )
    for name, (x, y) in vertices.items():
        if name.startswith("v"):
            out.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{colour}"/>')
    out.append(label(WIDTH / 2, 312, "time →", SMALL, "middle", f'fill="{ctx.theme.colours["muted"]}"'))
    return _fig(opts, svg(WIDTH, 320, "".join(out), opts.get("title", f"{topology} Feynman diagram"), "chart"))


# ---------------------------------------------------------------------------
# the standard model, element tiles
# ---------------------------------------------------------------------------

PARTICLES = [  # symbol, name, mass, charge, spin, kind, column, row
    ("u", "up", "2.2 MeV", "+2/3", "1/2", "quark", 0, 0), ("c", "charm", "1.27 GeV", "+2/3", "1/2", "quark", 1, 0),
    ("t", "top", "172.7 GeV", "+2/3", "1/2", "quark", 2, 0), ("d", "down", "4.7 MeV", "-1/3", "1/2", "quark", 0, 1),
    ("s", "strange", "93 MeV", "-1/3", "1/2", "quark", 1, 1), ("b", "bottom", "4.18 GeV", "-1/3", "1/2", "quark", 2, 1),
    ("e", "electron", "0.511 MeV", "-1", "1/2", "lepton", 0, 2), ("μ", "muon", "105.7 MeV", "-1", "1/2", "lepton", 1, 2),
    ("τ", "tau", "1.777 GeV", "-1", "1/2", "lepton", 2, 2), ("νₑ", "e neutrino", "< 0.8 eV", "0", "1/2", "lepton", 0, 3),
    ("νμ", "μ neutrino", "< 0.17 MeV", "0", "1/2", "lepton", 1, 3), ("ντ", "τ neutrino", "< 18.2 MeV", "0", "1/2", "lepton", 2, 3),
    ("g", "gluon", "0", "0", "1", "gauge boson", 3, 0), ("γ", "photon", "0", "0", "1", "gauge boson", 3, 1),
    ("Z", "Z boson", "91.19 GeV", "0", "1", "gauge boson", 3, 2), ("W", "W boson", "80.37 GeV", "±1", "1", "gauge boson", 3, 3),
    ("H", "Higgs", "125.2 GeV", "0", "0", "scalar boson", 4, 0),
]  # fmt: skip
PARTICLE_COLOURS = {"quark": "#6b4bb4", "lepton": "#2e6b3a", "gauge boson": "#b4540a", "scalar boson": "#a3322b"}


@block("standard-model", "No lines; highlight= names particles to stand out, such as highlight=t,H", "")
def standard_model_html(code, opts, ctx):
    """The particles of the standard model in their grid: three generations of quarks and leptons, the gauge
    bosons and the Higgs, each with its mass, charge and spin."""
    marked = {p.strip() for p in opts.get("highlight", "").split(",") if p.strip()}
    w, h, gap, left, top = 112, 84, 8, 10, 26
    out = []
    for n, head in enumerate(("I", "II", "III")):
        out.append(label(left + n * (w + gap) + w / 2, 16, f"Generation {head}", SMALL, "middle", 'font-weight="700"'))
    for symbol, name, mass, charge, spin, kind, col, row in PARTICLES:
        x, y = left + col * (w + gap), top + row * (h + gap)
        colour = PARTICLE_COLOURS[kind]
        strong = symbol in marked or name in marked
        out.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{colour}" fill-opacity="{1 if strong else 0.14}" stroke="{colour}" stroke-width="2"/>'
        )
        ink = 'fill="#fff"' if strong else f'fill="{colour}"'
        out.append(label(x + 8, y + 16, mass, SMALL - 2, extra=ink))
        out.append(label(x + w - 8, y + 16, f"{charge} · {spin}", SMALL - 2, "end", ink))
        out.append(label(x + w / 2, y + 52, symbol, 30, "middle", f'{ink} font-weight="700"'))
        out.append(label(x + w / 2, y + 74, name, SMALL - 1, "middle", ink))
    y = top + 4 * (h + gap) + 14
    x = left
    for kind, colour in PARTICLE_COLOURS.items():
        out.append(f'<rect x="{x}" y="{y - 11}" width="14" height="14" rx="3" fill="{colour}"/>')
        out.append(label(x + 20, y, kind, SMALL))
        x += 30 + len(kind) * 7
    out.append(label(WIDTH - 10, y, "mass, charge · spin", SMALL, "end", f'fill="{ctx.theme.colours["muted"]}"'))
    return _fig(opts, svg(WIDTH, y + 10, "".join(out), opts.get("title", "the standard model"), "chart"))


@block(
    "elements",
    "Element symbols or numbers, on lines or split by spaces; cols=, or layout=table for the periodic table "
    "with those elements picked out (all of them when none is named); show= name, weight, shells, config, groups",
    "H He C N O Fe Au U",
)
def elements_html(code, opts, ctx):
    """Periodic-table tiles for the elements named: number, symbol, name and atomic weight, coloured by category.
    ``layout=table`` puts them in their places in the whole periodic table instead."""
    wanted = [token for token in re.split(r"[\s,]+", code.strip()) if token]
    layout = opts.get("layout", "tiles").lower()
    if layout not in ("tiles", "table"):
        raise PosterError(f"{ctx.where}: elements layout must be tiles or table, not '{layout}'")
    if not wanted and layout == "tiles":
        raise PosterError(f"{ctx.where}: an elements block needs element symbols or numbers")
    found = []
    for token in wanted:
        element = BY_NUMBER.get(int(token)) if token.isdigit() else ELEMENTS.get(token[:1].upper() + token[1:].lower())
        if element is None:
            raise PosterError(f"{ctx.where}: '{token}' is not an element symbol or number")
        found.append(element)
    shown = [part.strip().lower() for part in opts.get("show", "").split(",") if part.strip()]
    for part in shown:
        if part not in TILE_FIELDS + ("groups",):
            raise PosterError(f"{ctx.where}: elements show= takes {', '.join(TILE_FIELDS)} and groups, not '{part}'")
    if not shown:  # tiles have room for the weight, the table's smaller tiles only for the name
        shown = ["name"] if layout == "table" else ["name", "weight"]
    fields = [part for part in TILE_FIELDS if part in shown]
    if layout == "table":
        return _fig(opts, _periodic_table(found, fields, "groups" in shown, opts, ctx))
    cols = _whole(opts, "cols", min(len(found), 8), ctx)
    gap = 6
    size = min(76, (WIDTH - 10 - gap * (cols - 1)) / cols)
    height = _tile_height(size, fields)
    out = []
    for n, element in enumerate(found):
        x, y = 5 + (n % cols) * (size + gap), 5 + (n // cols) * (height + gap)
        out += _tile(x, y, size, element, fields, True, ctx)
    rows = (len(found) + cols - 1) // cols
    y = _legend(out, [e[4] for e in found], 5 + rows * (height + gap) + 12, WIDTH)
    return _fig(opts, svg(WIDTH, y + 8, "".join(out), opts.get("title", "elements"), "chart"))


TILE_FIELDS = ("name", "weight", "shells", "config")  # what a tile may show under its symbol, in this order
TILE_KEY = {
    "name": "Name",
    "weight": "Atomic weight",
    "shells": "Electrons per shell",
    "config": "Electron configuration",
}


def _tile_height(size, fields):
    return size * (0.66 + 0.17 * len(fields) + 0.06)


def _tile_lines(element, fields):
    number_, symbol, name, weight, _ = element
    values = {
        "name": name,
        "weight": weight,
        "shells": "-".join(map(str, shells(number_))),
        "config": configuration_text(number_),
    }
    return [values[field] for field in fields]


def _tile(x, y, size, element, fields, solid, ctx):
    """An element's tile: its number, its symbol large, and under it the ``fields`` asked for. A tile not
    ``solid`` is a pale tint of its category's colour, with grey text."""
    number_, symbol, _, _, category = element
    colour, height = CATEGORIES[category], _tile_height(size, fields)
    if solid:
        out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{height:.1f}" rx="4" fill="{colour}"/>']
        ink, strong = 'fill="#fff"', WHITE
    else:
        out = [
            f'<rect x="{x + 0.5:.1f}" y="{y + 0.5:.1f}" width="{size - 1:.1f}" height="{height - 1:.1f}" rx="4" '
            f'fill="{colour}" fill-opacity=".14" stroke="{colour}" stroke-opacity=".45"/>'
        ]
        ink = strong = f'fill="{ctx.theme.colours["muted"]}"'
    out.append(label(x + size * 0.07, y + size * 0.2, str(number_), size * 0.16, extra=ink))
    out.append(label(x + size / 2, y + size * 0.58, symbol, size * 0.36, "middle", strong))
    for k, text in enumerate(_tile_lines(element, fields)):
        fit = min(size * 0.15, (size - 6) / max(len(text), 1) / 0.5)  # shrunk to fit the tile's width
        out.append(label(x + size / 2, y + size * (0.82 + 0.17 * k), text, fit, "middle", ink))
    return out


def _legend(out, categories, y, width):
    """The key of the categories drawn, in the order of CATEGORIES, in lines across ``width``; returns its foot."""
    x = 5
    for category in dict.fromkeys(sorted(categories, key=list(CATEGORIES).index)):
        step = 30 + len(category) * 6.5
        if x > 5 and x + step - 12 > width:  # the legend goes on to another line rather than off the edge
            x, y = 5, y + 20
        out.append(f'<rect x="{x}" y="{y - 10}" width="12" height="12" rx="2" fill="{CATEGORIES[category]}"/>')
        out.append(label(x + 17, y, category, SMALL - 1))
        x += step
    return y


def _table_place(z):
    """The row and column of element ``z`` in the periodic table: periods 1 to 7 in rows 0 to 6, and the
    lanthanides and actinides in rows 7 and 8, under the table, from the third column."""
    if z <= 2:
        return 0, 0 if z == 1 else 17
    for start, row in ((3, 1), (11, 2)):  # periods 2 and 3: the s-block, then a gap, then the p-block
        if z < start + 8:
            k = z - start
            return row, k if k < 2 else k + 10
    if z <= 54:
        return (3, z - 19) if z <= 36 else (4, z - 37)
    for first, row, f_row in ((55, 5, 7), (87, 6, 8)):  # periods 6 and 7, their f-block on a row of its own
        if z < first + 32:
            k = z - first
            if k < 2:
                return row, k
            if k < 17:
                return f_row, k + 1
            return row, k - 14
    raise ValueError(z)


def _periodic_table(found, fields, groups, opts, ctx):
    """Every element in its place, in its category's colour: solid for those in ``found`` (or all, when it is
    empty), a pale tint for the rest. ``groups`` numbers the groups along the top and the periods down the side.
    When the tiles show more than the name, a large tile in the gap at the top says what each line is."""
    width = 960 if fields == ["name"] else 1200  # more lines need wider tiles
    gap = 3
    left, top = (22, 18) if groups else (5, 5)
    size = (width - left - 5 - gap * 17) / 18
    height = _tile_height(size, fields)
    picked = {e[0] for e in found} or set(BY_NUMBER)
    muted = f'fill="{ctx.theme.colours["muted"]}"'
    out = []

    def at(row, col):
        return left + col * (size + gap), top + row * (height + gap) + (height * 0.4 if row >= 7 else 0)

    for z, element in sorted(BY_NUMBER.items()):
        out += _tile(*at(*_table_place(z)), size, element, fields, z in picked, ctx)
    for row, text in ((5, "57-71"), (6, "89-103")):  # where the lanthanides and actinides belong
        x, y = at(row, 2)
        out.append(label(x + size / 2, y + height / 2 + 4, text, 9, "middle", muted))
    if groups:
        for col in range(18):
            row = 0 if col in (0, 17) else 1 if col == 1 or col >= 12 else 3
            x, y = at(row, col)
            out.append(label(x + size / 2, y - 5, str(col + 1), 10, "middle", f'{muted} font-weight="700"'))
        for row in range(7):
            x, y = at(row, 0)
            out.append(label(x - 8, y + height / 2 + 4, str(row + 1), 10, "middle", f'{muted} font-weight="700"'))
    if fields != ["name"]:
        sample = found[0] if found else ELEMENTS["C"]
        big = size * 2.2
        x, y = at(0, 3)
        y += (3 * (height + gap) - _tile_height(big, fields)) / 2
        out += _tile(x, y, big, sample, fields, True, ctx)
        parts = [("Atomic number", big * 0.14), ("Symbol", big * 0.48)]
        parts += [(TILE_KEY[field], big * (0.78 + 0.17 * k)) for k, field in enumerate(fields)]
        for text, dy in parts:
            out.append(
                f'<line x1="{x + big + 4:.1f}" y1="{y + dy:.1f}" x2="{x + big + 26:.1f}" y2="{y + dy:.1f}" '
                f'stroke="currentColor" stroke-opacity=".5"/>'
            )
            out.append(label(x + big + 30, y + dy + 4, text, SMALL - 1))
    y = _legend(out, [e[4] for z, e in BY_NUMBER.items()], at(8, 0)[1] + height + 18, width)
    return svg(width, y + 8, "".join(out), opts.get("title", "the periodic table"), "chart")


# ---------------------------------------------------------------------------
# atom: the structure of an atom, its nucleus and its electrons
# ---------------------------------------------------------------------------

ATOM_STYLES = ("shells", "orbits")
NUCLEONS_DRAWN = 60  # a larger nucleus is one disc, with its counts written on it


def _particles(kind):
    """The shaded sphere of a proton, a neutron or an electron, as a radial gradient."""
    light, dark = {"p": ("#f0a070", "#a8431a"), "n": ("#e6e6e6", "#7f8590"), "e": ("#9cc4f2", "#2c5fa8")}[kind]
    return (
        f'<radialGradient id="atom-{kind}" cx=".35" cy=".35" r=".7">'
        f'<stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="{dark}"/></radialGradient>'
    )


def _sphere(x, y, r, kind):
    sign = {"p": "+", "e": "−"}.get(kind)
    out = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="url(#atom-{kind})" stroke="#fff" stroke-width=".8"/>'
    if sign:
        out += label(x, y + r * 0.42, sign, r * 1.3, "middle", 'fill="#fff" font-weight="700"')
    return out


def _nucleus(cx, cy, protons, neutrons, max_r):
    """The protons and neutrons packed in a ball, mixed evenly, or one disc with its counts if there are many."""
    total = protons + neutrons
    if total > NUCLEONS_DRAWN:
        r = max_r
        return [
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="url(#atom-p)" stroke="#fff"/>',
            label(cx, cy - 2, f"{protons} p⁺", SMALL - 2, "middle", 'fill="#fff" font-weight="700"'),
            label(cx, cy + 11, f"{neutrons} n", SMALL - 2, "middle", 'fill="#fff" font-weight="700"'),
        ]
    r = min(9.0, max_r / (math.sqrt(total) * 1.05 + 0.5))
    spots, kinds, placed = [], [], 0
    for i in range(total):  # a sunflower's spiral: even packing in a disc, the first at the centre
        radius, angle = r * 1.05 * math.sqrt(i), i * 137.508
        spots.append((cx + radius * math.cos(math.radians(angle)), cy + radius * math.sin(math.radians(angle))))
        proton = placed < protons and (placed + 0.5) / protons <= (i + 1) / total if protons else False
        kinds.append("p" if proton else "n")
        placed += proton
    return [_sphere(x, y, r, k) for (x, y), k in reversed(list(zip(spots, kinds)))]  # the centre drawn last, on top


def _atom(cx, cy, element, neutrons, style, ctx):
    z = element[0]
    counts, out = shells(z), []
    line = ctx.theme.colours["muted"]
    if style == "shells":
        inner, step = 34, min(18.0, 92 / max(len(counts), 1))
        for k, count in enumerate(counts):
            radius = inner + k * step
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{radius:.1f}" fill="none" stroke="{line}" stroke-width="1.2"/>')
            size = min(4.5, math.pi * radius / count * 0.8)
            for j in range(count):
                x, y = polar(cx, cy, radius, j * 360 / count)
                out.append(_sphere(x, y, size, "e"))
            out.append(
                label(cx + radius * 0.71 + 4, cy - radius * 0.71 - 2, str(count), SMALL - 3, extra=f'fill="{line}"')
            )
        out[:0] = _nucleus(cx, cy, z, neutrons, inner - 8)
    else:  # orbits: three tilted ellipses with the electrons shared out along them, as the atom is often drawn
        rx, ry = 120, 42
        for tilt in (0, 60, 120):
            out.append(
                f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{line}" stroke-width="2" '
                f'transform="rotate({tilt} {cx} {cy})"/>'
            )
        out += _nucleus(cx, cy, z, neutrons, 30)
        for j in range(z):
            tilt, turn = (0, 60, 120)[j % 3], math.radians(200 + 137.5 * j)
            x, y = rx * math.cos(turn), ry * math.sin(turn)
            t = math.radians(tilt)
            out.append(_sphere(cx + x * math.cos(t) - y * math.sin(t), cy + x * math.sin(t) + y * math.cos(t), 7, "e"))
    out.append(label(cx, cy + 148, f"{element[2]} ({element[1]})", SIZE, "middle", 'font-weight="700"'))
    detail = f"{z} p⁺, {neutrons} n, {z} e⁻ · shells {'-'.join(map(str, counts))}"
    out.append(label(cx, cy + 166, detail, SMALL - 1, "middle", f'fill="{line}"'))
    out.append(label(cx, cy + 182, configuration_text(z), SMALL - 1, "middle", f'fill="{line}"'))
    return out


@block(
    "atom",
    "element | neutrons lines, one atom each (neutrons optional: the most common isotope's, near the atomic weight); "
    "style=shells (default) or orbits, key=no",
    "C\nNa",
)
def atom_html(code, opts, ctx):
    """Atoms side by side: the nucleus of protons and neutrons, and the electrons on their shells (``shells``,
    the Bohr model) or round three tilted orbits (``orbits``, for a small atom), with a key to the particles."""
    style = opts.get("style", "shells").lower()
    if style not in ATOM_STYLES:
        raise PosterError(f"{ctx.where}: atom style must be shells or orbits, not '{style}'")
    atoms = []
    for line in _lines(code):
        cells = _cells(line)
        token = cells[0]
        element = BY_NUMBER.get(int(token)) if token.isdigit() else ELEMENTS.get(token[:1].upper() + token[1:].lower())
        if element is None:
            raise PosterError(f"{ctx.where}: '{token}' is not an element symbol or number")
        if style == "orbits" and element[0] > 12:
            raise PosterError(
                f"{ctx.where}: {element[2]} has {element[0]} electrons, too many to draw as orbits: use style=shells"
            )
        if len(cells) > 1 and cells[1]:
            neutrons = int(_num(cells[1], ctx, "a number of neutrons"))
        else:
            neutrons = round(float(element[3].strip("[]"))) - element[0]
        atoms.append((element, neutrons))
    if not atoms:
        raise PosterError(f"{ctx.where}: an atom block needs an element on a line")
    slot = 300
    out = [f"<defs>{_particles('p')}{_particles('n')}{_particles('e')}</defs>"]
    for n, (element, neutrons) in enumerate(atoms):
        out += _atom(slot * n + slot / 2, 140, element, neutrons, style, ctx)
    width = slot * len(atoms)
    if opts.get("key", "yes").lower() not in ("no", "false"):
        x = width + 10
        out.append(label(x, 70, "Key", SIZE, extra='font-weight="700"'))
        for k, (kind, name) in enumerate((("p", "Proton"), ("n", "Neutron"), ("e", "Electron"))):
            out.append(_sphere(x + 9, 98 + k * 30, 9, kind))
            out.append(label(x + 26, 103 + k * 30, name, SIZE))
        width += 120
    return _fig(opts, svg(width, 330, "".join(out), opts.get("title", "atomic structure"), "chart"))


# ---------------------------------------------------------------------------
# chart of nuclides
# ---------------------------------------------------------------------------

MAGIC = (2, 8, 20, 28, 50, 82, 126)
DECAY = {
    "stable": "#1d1f27",
    "beta-": "#3f74b8",
    "beta+": "#a3322b",
    "alpha": "#d9a400",
    "fission": "#2e6b3a",
    "other": "#9aa0ab",
}


@block(
    "nuclide-chart",
    "Z | N | label | stable, beta-, beta+, alpha, fission or other lines; valley=yes, magic=yes, path: Z,N Z,N ... | label | colour",
    "1 | 0 | ¹H | stable\n1 | 1 | ²H | stable\n1 | 2 | ³H | beta-\n2 | 2 | ⁴He | stable\n3 | 4 | ⁷Li | stable\n4 | 5 | ⁹Be | stable\n6 | 6 | ¹²C | stable\n6 | 8 | ¹⁴C | beta-\n8 | 8 | ¹⁶O | stable",
    "magic=yes",
)
def nuclide_chart_html(code, opts, ctx):
    """Nuclides on a grid of proton number Z against neutron number N, each square coloured by how it decays,
    with the line of stability, the magic numbers and paths such as the s-process when asked for."""
    nuclides, paths = [], []
    for line in _lines(code):
        if line.lower().startswith("path:"):
            cells = _cells(line[5:])
            points = []
            for pair in cells[0].split():
                z, _, n = pair.partition(",")
                points.append((_num(z, ctx, "a Z"), _num(n, ctx, "an N")))
            paths.append(
                (
                    points,
                    cells[1] if len(cells) > 1 else "",
                    ctx.theme.colour(cells[2] if len(cells) > 2 and cells[2] else None, "accent"),
                )
            )
            continue
        cells = _cells(line)
        if len(cells) < 2:
            raise PosterError(f"{ctx.where}: a nuclide line is 'Z | N | label | decay', not '{line}'")
        decay = cells[3].lower() if len(cells) > 3 and cells[3] else "other"
        if decay not in DECAY:
            raise PosterError(f"{ctx.where}: a decay is one of {', '.join(DECAY)}, not '{cells[3]}'")
        nuclides.append(
            (
                int(_num(cells[0], ctx, "a Z")),
                int(_num(cells[1], ctx, "an N")),
                cells[2] if len(cells) > 2 else "",
                decay,
            )
        )
    if not nuclides and not paths:
        raise PosterError(f"{ctx.where}: a nuclide chart needs 'Z | N | label | decay' lines")
    zmax = max([z for z, *_ in nuclides] + [z for pts, *_ in paths for z, _ in pts] + [1])
    nmax = max([n for _, n, *_ in nuclides] + [n for pts, *_ in paths for _, n in pts] + [1])
    left, top = 40, 10
    cell = min((WIDTH - left - 10) / (nmax + 1), 420 / (zmax + 1), 48)
    height = top + (zmax + 1) * cell

    def at(z, n):
        return left + n * cell, top + (zmax - z) * cell

    out = [
        f'<rect x="{left}" y="{top}" width="{(nmax + 1) * cell:.1f}" height="{(zmax + 1) * cell:.1f}" fill="none" stroke="currentColor" stroke-opacity=".3"/>'
    ]
    if opts.get("magic", "no").lower() in ("yes", "true"):
        for m in MAGIC:
            if m <= nmax:
                x = left + (m + 0.5) * cell
                out.append(
                    f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height:.1f}" stroke="{ctx.theme.colours["accent"]}" stroke-opacity=".5" stroke-dasharray="4 3"/>'
                )
            if m <= zmax:
                y = top + (zmax - m + 0.5) * cell
                out.append(
                    f'<line x1="{left}" y1="{y:.1f}" x2="{left + (nmax + 1) * cell:.1f}" y2="{y:.1f}" stroke="{ctx.theme.colours["accent"]}" stroke-opacity=".5" stroke-dasharray="4 3"/>'
                )
    if opts.get("valley", "no").lower() in ("yes", "true"):
        points = []
        for z in range(1, zmax + 1):  # N for the most stable A at each Z: N = Z (1 + 0.0075 A^(2/3)), solved for A
            a = 2 * z
            for _ in range(20):
                a = z + z * (1 + 0.0075 * a ** (2 / 3))
            n = a - z
            if n <= nmax:
                x, y = at(z, n)
                points.append(f"{x + cell / 2:.1f},{y + cell / 2:.1f}")
        if points:
            out.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{ctx.theme.colours["good"]}" stroke-width="3" stroke-opacity=".7"/>'
            )
    for z, n, text, decay in nuclides:
        x, y = at(z, n)
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 1:.1f}" height="{cell - 1:.1f}" fill="{DECAY[decay]}"/>'
        )
        if cell >= 24 and text:
            out.append(label(x + cell / 2, y + cell / 2 + 4, text, min(SMALL, cell / 3), "middle", 'fill="#fff"'))
    for k, (points, _, colour) in enumerate(paths):
        # each step an arrow, stopping short of the squares' centres so their labels stay readable
        out.append(f"<defs>{_arrow_defs(f'nuc-path{k}', colour, 4)}</defs>")
        centres = [(left + (n + 0.5) * cell, top + (zmax - z + 0.5) * cell) for z, n in points]
        for (x0, y0), (x1, y1) in zip(centres, centres[1:]):
            d = math.hypot(x1 - x0, y1 - y0) or 1
            trim = min(cell * 0.3, d / 3)
            ux, uy = (x1 - x0) / d * trim, (y1 - y0) / d * trim
            ends = f'x1="{x0 + ux:.1f}" y1="{y0 + uy:.1f}" x2="{x1 - ux:.1f}" y2="{y1 - uy:.1f}"'
            out.append(f'<line {ends} stroke="#fff" stroke-width="6" stroke-linecap="round"/>')  # clear of the squares
            out.append(f'<line {ends} stroke="{colour}" stroke-width="3" marker-end="url(#nuc-path{k})"/>')
    out.append(label(left + (nmax + 1) * cell / 2, height + 18, "Neutrons, N", SMALL, "middle", 'font-weight="700"'))
    out.append(
        f'<text x="14" y="{(top + height) / 2:.1f}" transform="rotate(-90 14 {(top + height) / 2:.1f})" text-anchor="middle" font-size="{SMALL}" font-weight="700" fill="currentColor">Protons, Z</text>'
    )
    y = height + 40
    x = left
    for decay in dict.fromkeys(d for *_, d in nuclides):
        out.append(f'<rect x="{x}" y="{y - 10}" width="12" height="12" fill="{DECAY[decay]}"/>')
        out.append(label(x + 17, y, decay, SMALL - 1))
        x += 40 + len(decay) * 6.5
    for _, text, colour in paths:  # a path is named in the key, not on the chart, where it would cover squares
        if text:
            out.append(f'<line x1="{x}" y1="{y - 4}" x2="{x + 18}" y2="{y - 4}" stroke="{colour}" stroke-width="2.5"/>')
            out.append(label(x + 24, y, text, SMALL - 1))
            x += 44 + len(text) * 6.5
    return _fig(opts, svg(WIDTH, y + 8, "".join(out), opts.get("title", "chart of nuclides"), "chart"))
