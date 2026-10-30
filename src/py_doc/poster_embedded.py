"""Poster blocks for protocols, embedded systems and explanations: annotated bytes and strings, code side by side,
chip pinouts, bench instruments, pros and cons, a glossary, pictures with numbered pins and zoom chains, and inline
sparklines. The pictures are SVG drawn with ``poster_svg``; the text blocks are HTML in the poster's styles.
"""

from __future__ import annotations

import base64
import mimetypes
import re

from py_doc.poster_blocks import Fragment, PosterError, _whole, block, esc, inline
from py_doc.poster_svg import label, spread, svg, text_width, wrap

WIDTH = 640
SIZE = 13
SMALL = 11.5


def _mono(ctx):
    """The font attribute of the theme's monospace font, for bytes and code."""
    return f'font-family="{esc(ctx.theme.fonts["mono"])}"'


def _lines(code):
    return [line for line in code.splitlines() if line.strip()]


def _cells(line):
    return [cell.strip() for cell in line.split("|")]


def _fig(opts, picture):
    title = f'<div class="fig-title">{esc(opts["title"])}</div>' if opts.get("title") else ""
    return Fragment(f'<div class="fig">{title}{picture}</div>', picture)


def _picture(path_text, ctx, what):
    path = ctx.base / path_text.strip()
    if not path.is_file():
        raise PosterError(f"{ctx.where}: the {what} picture {path_text.strip()} is not there (looked in {ctx.base})")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


# ---------------------------------------------------------------------------
# hex-dissect: bytes with their fields
# ---------------------------------------------------------------------------


def _range(text, ctx):
    m = re.fullmatch(r"\s*(\d+)\s*(?:([-+])\s*(\d+))?\s*", text)
    if not m:
        raise PosterError(f"{ctx.where}: a byte range is 'start', 'start-end' or 'start+length', not '{text}'")
    start = int(m[1])
    if not m[2]:
        return start, start
    end = int(m[3]) if m[2] == "-" else start + int(m[3]) - 1
    if end < start:
        raise PosterError(f"{ctx.where}: the byte range '{text}' ends before it starts")
    return start, end


@block(
    "hex-dissect",
    "bytes: hex lines, then start-end (or start+length) | field | value | colour lines; cols=, ascii=no",
    "bytes: 44 01 84 a1 b3 72 64\n0 | Ver, type, token length | 1, CON, 4 | blue\n1 | Code | 0.01 GET | navy\n2-3 | Message ID | 0x84a1 | green\n4-6 | Option | Uri-Path rd | amber",
)
def hex_dissect_html(code, opts, ctx):
    """A hex dump with each field's bytes in its colour, and the fields decoded beside their colour."""
    data, fields = [], []
    for line in _lines(code):
        if line.strip().lower().startswith("bytes:") or not fields and re.fullmatch(r"[\s0-9a-fA-F]+", line):
            text = line.split(":", 1)[1] if ":" in line else line
            pairs = re.findall(r"[0-9a-fA-F]{2}", text.replace(" ", "")) if " " not in text.strip() else text.split()
            for pair in pairs:
                if not re.fullmatch(r"[0-9a-fA-F]{2}", pair):
                    raise PosterError(f"{ctx.where}: '{pair}' is not a byte in hex")
                data.append(int(pair, 16))
            continue
        cells = _cells(line)
        start, end = _range(cells[0], ctx)
        colour = ctx.theme.colour(cells[3] if len(cells) > 3 and cells[3] else None, "secondary")
        fields.append((start, end, cells[1] if len(cells) > 1 else "", cells[2] if len(cells) > 2 else "", colour))
    if not data:
        raise PosterError(f"{ctx.where}: a hex-dissect block needs a 'bytes:' line")
    for start, end, name, _, _ in fields:
        if end >= len(data):
            raise PosterError(f"{ctx.where}: the field '{name}' ends at byte {end}, but there are {len(data)} bytes")
    cols = _whole(opts, "cols", min(16, len(data)), ctx)
    show_ascii = opts.get("ascii", "yes").lower() not in ("no", "false")
    colour_of = {}
    for start, end, _, _, colour in fields:
        for n in range(start, end + 1):
            colour_of[n] = colour
    cell_w, cell_h, left, top = 30, 26, 52, 8
    rows = (len(data) + cols - 1) // cols
    out = []
    for r in range(rows):
        y = top + r * (cell_h + 8)
        out.append(
            label(
                left - 8, y + 18, f"{r * cols:04x}", SMALL, "end", f'{_mono(ctx)} fill="{ctx.theme.colours["muted"]}"'
            )
        )
        for c in range(cols):
            n = r * cols + c
            if n >= len(data):
                break
            x = left + c * cell_w
            colour = colour_of.get(n)
            fill = f'fill="{colour}" fill-opacity=".2"' if colour else f'fill="{ctx.theme.colours["surface"]}"'
            out.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{cell_h}" rx="3" {fill} stroke="{colour or ctx.theme.colours["border"]}"/>'
            )
            if colour:  # a solid bar under the byte, the colour of its swatch in the key
                out.append(f'<rect x="{x}" y="{y + cell_h + 1}" width="{cell_w - 2}" height="3" fill="{colour}"/>')
            out.append(
                label(x + (cell_w - 2) / 2, y + 18, f"{data[n]:02x}", SIZE, "middle", f'{_mono(ctx)} font-weight="700"')
            )
            if show_ascii:
                ch = chr(data[n]) if 32 <= data[n] < 127 else "·"
                ax = left + cols * cell_w + 14 + c * 10
                out.append(
                    label(ax, y + 18, ch, SIZE, "middle", f'{_mono(ctx)} fill="{colour or ctx.theme.colours["muted"]}"')
                )
    y = top + rows * (cell_h + 8) + 16
    values_x = left + 80 + max((text_width(name, SIZE, True) for _, _, name, _, _ in fields), default=0)
    for start, end, name, value, colour in fields:
        span = f"{start}" if start == end else f"{start}-{end}"
        out.append(f'<rect x="{left}" y="{y - 12}" width="14" height="14" rx="2" fill="{colour}"/>')
        out.append(label(left + 22, y, f"{span}", SMALL, extra=f'{_mono(ctx)} fill="{ctx.theme.colours["muted"]}"'))
        out.append(label(left + 72, y, name, SIZE, extra='font-weight="700"'))
        if value:
            out.append(label(values_x, y, value, SIZE))  # the values in a column of their own
        y += 20
    width = max(WIDTH, left + cols * cell_w + (14 + cols * 10 if show_ascii else 0) + 10)
    return _fig(opts, svg(width, y, "".join(out), opts.get("title", "hex dump"), "chart"))


# ---------------------------------------------------------------------------
# syntax-anatomy: a string taken apart, token by token
# ---------------------------------------------------------------------------


@block(
    "syntax-anatomy",
    "The string on the first line, then token | label | colour lines, each token found in order",
    "coaps://node.example.com:5684/3303/0/5700\ncoaps | Scheme: CoAP over DTLS | navy\nnode.example.com | Host | blue\n5684 | Port | grey\n3303 | Object: Temperature | green\n0 | Instance | amber\n5700 | Resource: Sensor Value | red",
)
def syntax_anatomy_html(code, opts, ctx):
    """The string in large type, with a coloured bar under each token and a leader line to its label."""
    lines = _lines(code)
    if not lines:
        raise PosterError(f"{ctx.where}: a syntax-anatomy block needs the string on its first line")
    text, parts = lines[0].strip(), []
    at = 0
    for line in lines[1:]:
        cells = _cells(line)
        found = text.find(cells[0], at)
        if not cells[0] or found < 0:
            raise PosterError(f"{ctx.where}: '{cells[0]}' is not in '{text}' after the tokens before it")
        at = found + len(cells[0])
        colour = ctx.theme.colour(cells[2] if len(cells) > 2 and cells[2] else None, "secondary")
        parts.append((found, at, cells[1] if len(cells) > 1 else "", colour))
    gap = 160  # room for a label of two short lines
    width = max(WIDTH, gap * ((len(parts) + 1) // 2) + 40, int(len(text) * 14 + 40))
    if "width" in opts:
        width = _whole(opts, "width", width, ctx)
    size = min(26, (width - 20) / max(len(text), 1) / 0.6)
    char = size * 0.6
    left, base = (width - char * len(text)) / 2, 40
    out = [label(left, base, text, size, extra=f'{_mono(ctx)} xml:space="preserve"')]
    centres = [left + char * (s + e) / 2 for s, e, _, _ in parts]
    xs = [0.0] * len(parts)
    for level in (0, 1):  # labels on two rows, so neighbours do not touch
        row = [n for n in range(len(parts)) if n % 2 == level]
        for n, x in zip(row, spread([centres[n] for n in row], gap, gap / 2, width - gap / 2)):
            xs[n] = x
    bottom = base
    for n, ((start, end, name, colour), centre, x) in enumerate(zip(parts, centres, xs)):
        level = n % 2
        x0, x1 = left + char * start, left + char * end
        out.append(f'<rect x="{x0:.1f}" y="{base + 6}" width="{x1 - x0:.1f}" height="5" rx="2" fill="{colour}"/>')
        y_label = base + 46 + level * 44
        out.append(
            f'<path d="M{centre:.1f},{base + 12} L{centre:.1f},{base + 20} L{x:.1f},{y_label - 16}" stroke="{colour}" fill="none"/>'
        )
        for k, part in enumerate(wrap(name, gap - 10, SMALL, True)[:2]):
            out.append(label(x, y_label + k * 14, part, SMALL, "middle", f'font-weight="700" fill="{colour}"'))
        bottom = max(bottom, y_label + 22)
    return _fig(opts, svg(width, bottom, "".join(out), opts.get("title", text), "chart"))


# ---------------------------------------------------------------------------
# code-compare: code side by side, the unsafe and the safe
# ---------------------------------------------------------------------------

CALLOUT = re.compile(r"\s*<(\d+)>\s*$")


@block(
    "code-compare",
    "Panels starting @bad Title, @good Title or @plain Title, then code; a line ending <1> gets a badge; -- 1 | note lines",
    "@bad Unsafe C\nstrcpy(buf, input);  <1>\n@good Bounded C\nstrncpy(buf, input, sizeof buf - 1);  <1>\n-- 1 | The copy is bounded by the buffer",
)
def code_compare_html(code, opts, ctx):
    """Code panels side by side, each with a ✗ or ✓ header, numbered badges on lines, and notes under them."""
    panels, notes = [], []
    for line in code.splitlines():
        head = re.match(r"^@(bad|good|plain)\b\s*(.*)$", line.strip())
        if head:
            panels.append((head[1], head[2], []))
        elif line.startswith("--"):
            number, _, text = line[2:].partition("|")
            notes.append((number.strip(), text.strip()))
        elif panels:
            panels[-1][2].append(line)
        elif line.strip():
            raise PosterError(f"{ctx.where}: code-compare starts with a panel: @bad, @good or @plain and a title")
    if not panels:
        raise PosterError(f"{ctx.where}: a code-compare block needs a panel: @bad, @good or @plain and a title")
    out = ""
    for kind, title, lines in panels:
        while lines and not lines[-1].strip():
            lines.pop()
        mark = {"bad": "&#10007;", "good": "&#10003;", "plain": ""}[kind]
        body = ""
        for line in lines:
            badge = CALLOUT.search(line)
            text = CALLOUT.sub("", line) if badge else line
            body += f"<div>{esc(text) or '&#8203;'}" + (f'<b class="cb">{badge[1]}</b>' if badge else "") + "</div>"
        out += (
            f'<div class="cc {kind}"><div class="cc-h">{mark} {inline(title)}</div><div class="cc-b">{body}</div></div>'
        )
    cols = _whole(opts, "cols", len(panels), ctx)
    notes_html = "".join(f'<li><b class="cb">{esc(n)}</b>{inline(t)}</li>' for n, t in notes)
    return f'<div class="ccs" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>' + (
        f'<ol class="cc-notes">{notes_html}</ol>' if notes else ""
    )


# ---------------------------------------------------------------------------
# pinout: a chip or connector with its pins by function
# ---------------------------------------------------------------------------

FUNCTIONS = {  # pin function: its colour
    "pwr": "#a3322b", "gnd": "#1d1f27", "gpio": "#6b7080", "adc": "#b4540a", "dac": "#8a3d08", "i2c": "#3f74b8",
    "spi": "#2e6b3a", "uart": "#6b4bb4", "pwm": "#0f7b7b", "usb": "#2a3150", "swd": "#c0398b", "rf": "#d97706",
    "nc": "#b0b4bf", "reset": "#7a4b2a", "clk": "#4a7fc1",
}  # fmt: skip
PACKAGES = ("dip", "qfn", "header")


@block(
    "pinout",
    "pin | name | function (pwr, gnd, gpio, adc, i2c, spi, uart, pwm...) or colour lines; package=dip|qfn|header, rows=",
    "1 | VDD | pwr\n2 | PA0 | adc\n3 | PA1 | uart\n4 | GND | gnd\n5 | SDA | i2c\n6 | SCL | i2c\n7 | NRST | reset\n8 | PB3 | swd",
    "package=dip",
)
def pinout_html(code, opts, ctx):
    """A DIP or QFN package, or a pin header, with each pin's name in a pill coloured by its function."""
    package = opts.get("package", "dip").lower()
    if package not in PACKAGES:
        raise PosterError(f"{ctx.where}: pinout package must be one of {', '.join(PACKAGES)}, not '{package}'")
    pins = []
    for line in _lines(code):
        cells = _cells(line)
        if len(cells) < 2:
            raise PosterError(f"{ctx.where}: a pinout line is 'pin | name | function', not '{line}'")
        func = cells[2].lower() if len(cells) > 2 and cells[2] else "gpio"
        colour = FUNCTIONS.get(func) or ctx.theme.colour(func, "secondary")
        pins.append((cells[0], cells[1], func if func in FUNCTIONS else "", colour))
    if not pins:
        raise PosterError(f"{ctx.where}: a pinout needs at least one 'pin | name' line")
    out = []
    pill_w, pill_h, step = 96, 20, 26

    def pill(x, y, pin, name, colour, anchor):
        x0 = x - pill_w if anchor == "end" else x
        out.append(
            f'<rect x="{x0:.1f}" y="{y - pill_h / 2:.1f}" width="{pill_w}" height="{pill_h}" rx="10" fill="{colour}"/>'
        )
        out.append(label(x0 + pill_w / 2, y + 4.5, name, SMALL, "middle", 'fill="#fff" font-weight="700"'))
        number_x = x0 + pill_w + 14 if anchor == "start" else x0 - 14
        out.append(label(number_x, y + 4.5, pin, SMALL - 1, "middle", f'fill="{ctx.theme.colours["muted"]}"'))

    if package == "dip":
        half = (len(pins) + 1) // 2
        body_x, body_w, top = WIDTH / 2 - 70, 140, 20
        body_h = half * step + 10
        out.append(
            f'<rect x="{body_x}" y="{top}" width="{body_w}" height="{body_h}" rx="6" fill="{ctx.theme.colours["header"]}"/>'
        )
        out.append(f'<circle cx="{WIDTH / 2}" cy="{top}" r="9" fill="{ctx.theme.colours["page"]}"/>')
        for n, (pin, name, _, colour) in enumerate(pins):
            right = n >= half
            row = (len(pins) - 1 - n) if right else n
            y = top + 18 + row * step
            x = body_x + body_w + 34 if right else body_x - 34
            out.append(
                f'<rect x="{(body_x + body_w) if right else body_x - 10}" y="{y - 4}" width="10" height="8" fill="{ctx.theme.colours["muted"]}"/>'
            )
            pill(x, y, pin, name, colour, "start" if right else "end")
        height = top + body_h + 16
    elif package == "header":
        rows = _whole(opts, "rows", 2, ctx)
        per_row = (len(pins) + rows - 1) // rows
        top, gap = 20, 30
        for n, (pin, name, _, colour) in enumerate(pins):
            col, row = (n // rows, n % rows) if rows > 1 else (n, 0)
            x = 40 + col * (pill_w + 40)
            y = top + row * gap
            out.append(f'<rect x="{x - 26}" y="{y - 9}" width="18" height="18" fill="{ctx.theme.colours["header"]}"/>')
            out.append(f'<circle cx="{x - 17}" cy="{y}" r="5" fill="#d4af37"/>')
            pill(x, y, pin, name, colour, "start")
        height = top + rows * gap
        width = max(WIDTH, 40 + per_row * (pill_w + 40))
        return _fig(
            opts,
            svg(width, height + _legend(out, pins, height, ctx), "".join(out), opts.get("title", "pinout"), "chart"),
        )
    else:  # qfn: four sides, pin 1 at the top of the left side, counting down and round
        side = (len(pins) + 3) // 4
        body = side * step + 20
        cx, cy = WIDTH / 2, 30 + pill_w + body / 2
        x0, y0 = cx - body / 2, cy - body / 2
        out.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{body}" height="{body}" rx="6" fill="{ctx.theme.colours["header"]}"/>'
        )
        out.append(f'<circle cx="{x0 + 14:.1f}" cy="{y0 + 14:.1f}" r="5" fill="{ctx.theme.colours["page"]}"/>')
        for n, (pin, name, _, colour) in enumerate(pins):
            s, k = divmod(n, side)
            offset = 20 + k * step
            if s == 0:  # left, downwards
                x, y = x0 - 12, y0 + offset
                pill(x, y, pin, name, colour, "end")
            elif s == 1:  # bottom, rightwards: names turned
                x, y = x0 + offset, y0 + body + 12
                _turned(out, x, y, pin, name, colour, pill_w, pill_h, down=True, ctx=ctx)
            elif s == 2:  # right, upwards
                x, y = x0 + body + 12, y0 + body - offset
                pill(x, y, pin, name, colour, "start")
            else:  # top, leftwards
                x, y = x0 + body - offset, y0 - 12
                _turned(out, x, y, pin, name, colour, pill_w, pill_h, down=False, ctx=ctx)
        height = cy + body / 2 + pill_w + 20
    return _fig(
        opts, svg(WIDTH, height + _legend(out, pins, height, ctx), "".join(out), opts.get("title", "pinout"), "chart")
    )


def _turned(out, x, y, pin, name, colour, w, h, down, ctx):
    y0 = y if down else y - w
    out.append(f'<rect x="{x - h / 2:.1f}" y="{y0:.1f}" width="{h}" height="{w}" rx="10" fill="{colour}"/>')
    ty = y0 + w / 2
    out.append(
        f'<text x="{x:.1f}" y="{ty:.1f}" transform="rotate(-90 {x:.1f} {ty:.1f})" text-anchor="middle" dominant-baseline="central"'
        f' font-size="{SMALL}" fill="#fff" font-weight="700">{esc(name)}</text>'
    )
    py = y0 + w + 12 if down else y0 - 6
    out.append(label(x, py, pin, SMALL - 1, "middle", f'fill="{ctx.theme.colours["muted"]}"'))


def _legend(out, pins, top, ctx):
    used = list(dict.fromkeys(func for _, _, func, _ in pins if func))
    x, y = 20, top + 8
    for func in used:
        out.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="6" fill="{FUNCTIONS[func]}"/>')
        out.append(label(x + 18, y + 10.5, func.upper(), SMALL))
        x += 34 + text_width(func, SMALL)
    return 30 if used else 0


# ---------------------------------------------------------------------------
# instrument: an oscilloscope, a logic analyser or a meter on the bench
# ---------------------------------------------------------------------------

INSTRUMENTS = ("scope", "logic", "meter")
SCREEN, GRID, TRACES = "#0d1117", "#2b3442", ("#f7d046", "#4cc9f0", "#f72585", "#80ed99")


@block(
    "instrument",
    "type=scope: Ch1 | colour | values in volts lines; type=logic: Name | 0101 lines; type=meter: value= label=; vdiv=, tdiv=, cursors=",
    "Ch1 | | 0 1.5 3 3 3 1.5 0 0 0 1.5 3 3 3 1.5 0 0\nCh2 | | 1 1.2 1.1 0.9 1 1.1 0.9 1 1.2 1 0.9 1.1 1 0.9 1 1",
    'type=scope vdiv=1 tdiv="1 ms" cursors=2,6',
)
def instrument_html(code, opts, ctx):
    kind = opts.get("type", "scope").lower()
    if kind not in INSTRUMENTS:
        raise PosterError(f"{ctx.where}: instrument type must be one of {', '.join(INSTRUMENTS)}, not '{kind}'")
    picture = {"scope": _scope, "logic": _logic, "meter": _meter}[kind](code, opts, ctx)
    return _fig(opts, picture)


def _screen(out, x, y, w, h, cols, rows):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{SCREEN}"/>')
    for c in range(1, cols):
        gx = x + w * c / cols
        out.append(f'<line x1="{gx:.1f}" y1="{y}" x2="{gx:.1f}" y2="{y + h}" stroke="{GRID}" stroke-dasharray="2 3"/>')
    for r in range(1, rows):
        gy = y + h * r / rows
        out.append(f'<line x1="{x}" y1="{gy:.1f}" x2="{x + w}" y2="{gy:.1f}" stroke="{GRID}" stroke-dasharray="2 3"/>')


def _scope(code, opts, ctx):
    channels = []
    for n, line in enumerate(_lines(code)):
        cells = _cells(line)
        if len(cells) < 3:
            raise PosterError(f"{ctx.where}: a scope line is 'Ch1 | colour | values', not '{line}'")
        try:
            values = [float(v) for v in cells[2].replace(",", " ").split()]
        except ValueError:
            raise PosterError(f"{ctx.where}: the values of {cells[0]} must be numbers") from None
        colour = ctx.theme.colour(cells[1]) if cells[1] else TRACES[n % len(TRACES)]
        channels.append((cells[0], colour, values))
    if not channels:
        raise PosterError(f"{ctx.where}: a scope needs at least one 'Ch1 | colour | values' line")
    vdiv = float(opts.get("vdiv", "1"))
    x0, y0, w, h, cols, rows = 10, 10, WIDTH - 20, 320, 10, 8
    out = []
    _screen(out, x0, y0, w, h, cols, rows)
    mid = y0 + h / 2
    for name, colour, values in channels:
        if len(values) < 2:
            raise PosterError(f"{ctx.where}: {name} needs at least two values")
        step = w / (len(values) - 1)
        points = " ".join(
            f"{x0 + i * step:.1f},{min(max(mid - v / vdiv * h / rows, y0), y0 + h):.1f}" for i, v in enumerate(values)
        )
        out.append(f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
    if opts.get("cursors"):
        try:
            a, b = (float(v) for v in opts["cursors"].split(","))
        except ValueError:
            raise PosterError(f"{ctx.where}: cursors= is two divisions, such as 2,6") from None
        for c in (a, b):
            cx = x0 + w * c / cols
            out.append(
                f'<line x1="{cx:.1f}" y1="{y0}" x2="{cx:.1f}" y2="{y0 + h}" stroke="#ffffff" stroke-dasharray="6 4"/>'
            )
        unit = opts.get("tdiv", "1 div")
        m = re.match(r"\s*([\d.]+)\s*(.*)$", unit)
        delta = f"Δt = {abs(b - a) * float(m[1]):g} {m[2]}" if m else f"Δt = {abs(b - a):g} div"
        out.append(label(x0 + w - 10, y0 + 20, delta, SIZE, "end", 'fill="#ffffff" font-weight="700"'))
    badges = [f"{name} {vdiv:g} V/div" for name, _, _ in channels] + [f"{opts.get('tdiv', '1 div')}/div"]
    x = x0
    for n, text in enumerate(badges):
        colour = channels[n][1] if n < len(channels) else "#d7dce4"
        out.append(
            f'<rect x="{x}" y="{y0 + h + 8}" width="{text_width(text, SMALL) + 16:.1f}" height="20" rx="4" fill="{colour}"/>'
        )
        out.append(label(x + 8, y0 + h + 22, text, SMALL, extra='fill="#0d1117" font-weight="700"'))
        x += text_width(text, SMALL) + 24
    return svg(WIDTH, y0 + h + 36, "".join(out), opts.get("title", "oscilloscope"), "chart")


def _logic(code, opts, ctx):
    channels = []
    for line in _lines(code):
        cells = _cells(line)
        bits = re.sub(r"\s", "", cells[1]) if len(cells) > 1 else ""
        if not bits or set(bits) - {"0", "1"}:
            raise PosterError(f"{ctx.where}: a logic line is 'Name | 0110...', not '{line}'")
        channels.append((cells[0], bits))
    if not channels:
        raise PosterError(f"{ctx.where}: a logic analyser needs at least one 'Name | 0101' line")
    lane, left, top = 44, 70, 10
    length = max(len(bits) for _, bits in channels)
    w = WIDTH - left - 10
    out = []
    _screen(out, left, top, w, lane * len(channels), length, len(channels))
    for n, (name, bits) in enumerate(channels):
        y_hi, y_lo = top + n * lane + 10, top + n * lane + lane - 10
        step = w / length
        points, level = [], None
        for i, bit in enumerate(bits):
            y = y_hi if bit == "1" else y_lo
            x = left + i * step
            if level is not None and y != level:
                points.append(f"{x:.1f},{level:.1f}")
            points.append(f"{x:.1f},{y:.1f}")
            points.append(f"{x + step:.1f},{y:.1f}")
            level = y
        out.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{TRACES[n % len(TRACES)]}" stroke-width="2.5"/>'
        )
        out.append(label(left - 8, top + n * lane + lane / 2 + 4, name, SIZE, "end", f'{_mono(ctx)} font-weight="700"'))
    return svg(WIDTH, top + lane * len(channels) + 10, "".join(out), opts.get("title", "logic analyser"), "chart")


# Seven-segment digits: which of the segments a b c d e f g are lit
SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg",
    "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": "",
}  # fmt: skip


def _digit(x, y, w, h, char, colour, dim):
    t = w * 0.18  # segment thickness
    spots = {
        "a": (x + t, y, w - 2 * t, t), "d": (x + t, y + h - t, w - 2 * t, t), "g": (x + t, y + (h - t) / 2, w - 2 * t, t),
        "f": (x, y + t, t, (h - 3 * t) / 2), "b": (x + w - t, y + t, t, (h - 3 * t) / 2),
        "e": (x, y + (h + t) / 2, t, (h - 3 * t) / 2), "c": (x + w - t, y + (h + t) / 2, t, (h - 3 * t) / 2),
    }  # fmt: skip
    lit = SEGMENTS.get(char, "")
    return "".join(
        f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" rx="{t / 3:.1f}" fill="{colour if name in lit else dim}"/>'
        for name, (sx, sy, sw, sh) in spots.items()
    )


def _meter(code, opts, ctx):
    value = opts.get("value", "").strip()
    m = re.fullmatch(r"(-?[\d. ]+)\s*(.*)", value)
    if not m:
        raise PosterError(f'{ctx.where}: a meter needs value=, such as value="2.41 µA"')
    digits, unit = m[1].strip(), m[2]
    out = [
        '<rect x="10" y="10" width="620" height="200" rx="14" fill="#2b2f36"/>',
        '<rect x="30" y="30" width="580" height="120" rx="6" fill="#c9d4b7"/>',
    ]
    w, h, gap = 52, 90, 16
    count = len(digits.replace(".", ""))
    x = 30 + (420 - count * (w + gap)) / 2
    for char in digits:
        if char == ".":
            out.append(f'<rect x="{x - gap / 2 - 5:.1f}" y="{40 + h - 10}" width="10" height="10" fill="#1f2a14"/>')
            continue
        out.append(_digit(x, 45, w, h, char, "#1f2a14", "#b8c3a6"))
        x += w + gap
    out.append(label(560, 120, unit, 40, "end", 'fill="#1f2a14" font-weight="700"'))
    stats = [f"{k.upper()} {opts[k]}" for k in ("min", "max", "avg") if opts.get(k)]
    out.append(label(40, 182, opts.get("label", ""), SIZE, extra='fill="#e6e8ef" font-weight="700"'))
    out.append(label(600, 182, "   ".join(stats), SIZE, "end", 'fill="#e6e8ef"'))
    return svg(WIDTH, 220, "".join(out), opts.get("title", opts.get("label", "meter")), "chart")


# ---------------------------------------------------------------------------
# Text blocks: pros and cons, a glossary
# ---------------------------------------------------------------------------


@block(
    "proscons",
    "+ advantage and - limitation lines; pros= and cons= name the two columns",
    "+ Ten-year battery\n+ Deep indoor coverage\n- Up to 10 s latency\n- No voice",
)
def proscons_html(code, opts, ctx):
    pros, cons = [], []
    for line in (line.strip() for line in code.splitlines() if line.strip()):
        if line[0] in "+-" and line[1:2] == " ":
            (pros if line[0] == "+" else cons).append(line[2:])
        else:
            raise PosterError(f"{ctx.where}: a proscons line starts '+ ' or '- ', not '{line}'")
    if not pros and not cons:
        raise PosterError(f"{ctx.where}: a proscons block needs at least one '+ ' or '- ' line")

    def column(kind, title, items, sign):
        lis = "".join(f"<li><b>{sign}</b><span>{inline(item)}</span></li>" for item in items)
        return f'<div class="pc {kind}"><div class="pc-h">{inline(title)}</div><ul>{lis}</ul></div>'

    return (
        '<div class="proscons">'
        + column("pro", opts.get("pros", "Advantages"), pros, "&#10003;")
        + column("con", opts.get("cons", "Limitations"), cons, "&#10007;")
        + "</div>"
    )


@block("glossary", "Term | definition lines; cols=", "PSM | Power saving mode\neDRX | Extended discontinuous reception")
def glossary_html(code, opts, ctx):
    rows = [_cells(line) for line in _lines(code)]
    if not rows or any(len(row) < 2 for row in rows):
        raise PosterError(f"{ctx.where}: each glossary line is 'Term | definition'")
    cols = _whole(opts, "cols", 2, ctx)
    out = "".join(f'<div class="gl"><b>{inline(term)}</b><span>{inline(text)}</span></div>' for term, text, *_ in rows)
    return f'<div class="glossary" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


# ---------------------------------------------------------------------------
# Pictures: numbered pins over a picture, and a chain of magnifications
# ---------------------------------------------------------------------------


def _percent(text, ctx, what):
    m = re.fullmatch(r"\s*([\d.]+)\s*%?\s*", text)
    if not m or not 0 <= float(m[1]) <= 100:
        raise PosterError(f"{ctx.where}: {what} '{text}' is not a percentage from 0 to 100")
    return float(m[1])


@block(
    "annotated",
    "The picture on the first line, then x%, y% | heading | text | colour lines; cols= of the legend",
    None,
)
def annotated_html(code, opts, ctx):
    """A picture with numbered pins at the places its lines name, and a legend of the numbers under it."""
    lines = _lines(code)
    if not lines:
        raise PosterError(f"{ctx.where}: an annotated block needs a picture on its first line")
    src = _picture(lines[0].split("|")[0], ctx, "annotated")
    pins, legend = "", ""
    for n, line in enumerate(lines[1:], 1):
        cells = _cells(line)
        where = cells[0].split(",")
        if len(where) != 2:
            raise PosterError(f"{ctx.where}: an annotated pin starts 'x%, y%', not '{cells[0]}'")
        x, y = (_percent(v, ctx, "a pin position") for v in where)
        colour = ctx.theme.colour(cells[3] if len(cells) > 3 and cells[3] else None, "accent")
        pins += f'<b class="pin" style="left:{x}%;top:{y}%;background:{colour}">{n}</b>'
        head = inline(cells[1]) if len(cells) > 1 else ""
        text = f"<span>{inline(cells[2])}</span>" if len(cells) > 2 and cells[2] else ""
        legend += f'<li><b class="pin" style="background:{colour}">{n}</b><div><strong>{head}</strong>{text}</div></li>'
    cols = _whole(opts, "cols", 2, ctx)
    return (
        f'<div class="annotated"><div class="an-pic"><img alt="{esc(opts.get("alt", "annotated picture"))}" src="{src}">{pins}</div>'
        f'<ol class="an-legend" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{legend}</ol></div>'
    )


@block(
    "zoom-chain",
    "picture | caption | magnification | x%, y%, w%, h% lines: the box in each picture is what the next shows",
    None,
)
def zoom_chain_html(code, opts, ctx):
    """Pictures in a row, each with a highlighted box that the next one enlarges, and the magnification between."""
    panels = []
    for line in _lines(code):
        cells = _cells(line)
        box = None
        if len(cells) > 3 and cells[3]:
            parts = cells[3].split(",")
            if len(parts) != 4:
                raise PosterError(f"{ctx.where}: a zoom box is 'x%, y%, w%, h%', not '{cells[3]}'")
            box = [_percent(v, ctx, "a zoom box") for v in parts]
        panels.append(
            (
                _picture(cells[0], ctx, "zoom-chain"),
                cells[1] if len(cells) > 1 else "",
                cells[2] if len(cells) > 2 else "",
                box,
            )
        )
    if len(panels) < 2:
        raise PosterError(f"{ctx.where}: a zoom chain needs at least two pictures")
    out = ""
    for n, (src, caption, zoom, box) in enumerate(panels):
        frame = ""
        if box and n + 1 < len(panels):
            x, y, w, h = box
            frame = f'<i class="zbox" style="left:{x}%;top:{y}%;width:{w}%;height:{h}%"></i>'
        out += f'<figure class="zp"><div class="zpic"><img alt="{esc(caption)}" src="{src}">{frame}</div><figcaption>{inline(caption)}</figcaption></figure>'
        if n + 1 < len(panels):
            out += f'<div class="zarrow"><b>{esc(panels[n + 1][2] or "")}</b><i>&#10230;</i></div>'
    return f'<div class="zoomchain">{out}</div>'
