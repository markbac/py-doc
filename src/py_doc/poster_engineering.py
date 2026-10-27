"""Poster blocks for engineering structure diagrams, with the symbols of their notations: a bow-tie, a fault tree,
a GSN safety case, a Karnaugh map, a PLC ladder, a Nassi-Shneiderman structogram, an N-squared matrix, IDEF0
boxes and a value stream map. Each is SVG drawn with ``poster_svg``, so it works in every output.
"""

from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field

from py_doc.poster_blocks import PosterError, block, mark_colour, series_colours
from py_doc.poster_shapes import _cells, _fig, _lines, _muted
from py_doc.poster_svg import Node, label, number, svg, tidy, wrap

WIDTH = 640
SIZE = 12
SMALL = 10.5
BOLD = 'font-weight="700"'


def _box_text(cx, cy, text, width, size=SIZE, lines=4, extra=""):
    """``text`` wrapped to ``width`` and centred on ``cx, cy``, at most ``lines`` lines (the last one cut short)."""
    parts = wrap(text, width, size, "700" in extra)
    if len(parts) > lines:
        parts = parts[: lines - 1] + [" ".join(parts[lines - 1 :])[: max(int(width / size * 1.7), 4)] + "…"]
    lead = size * 1.2
    top = cy - (len(parts) - 1) * lead / 2 + size * 0.35
    return "".join(label(cx, top + n * lead, part, size, "middle", extra) for n, part in enumerate(parts))


def _stroke(ctx, colour="strong", width=1.5):
    return f'stroke="{ctx.theme.colours[colour]}" stroke-width="{width:g}"'


def _arrowhead(x, y, angle, size=8, fill="currentColor"):
    """A filled triangle with its point at ``x, y``, pointing along ``angle`` degrees (0 is right, 90 down)."""
    a = math.radians(angle)
    back = [(x - size * math.cos(a) + size / 2 * math.sin(a), y - size * math.sin(a) - size / 2 * math.cos(a)),
            (x - size * math.cos(a) - size / 2 * math.sin(a), y - size * math.sin(a) + size / 2 * math.cos(a))]  # fmt: skip
    points = " ".join(f"{px:.1f},{py:.1f}" for px, py in [(x, y), *back])
    return f'<polygon points="{points}" fill="{fill}"/>'


@dataclass
class _Line:
    depth: int
    text: str
    number: int
    children: list = field(default_factory=list)


def _indented(code, ctx, what):
    """The lines of ``code`` as a forest, by their indentation (two spaces, or a tab, a level)."""
    roots: list[_Line] = []
    stack: list[_Line] = []
    for n, raw in enumerate(code.splitlines(), 1):
        if not raw.strip():
            continue
        indent = len(raw.expandtabs(2)) - len(raw.expandtabs(2).lstrip())
        item = _Line(indent, raw.strip(), n)
        while stack and stack[-1].depth >= indent:
            stack.pop()
        (stack[-1].children if stack else roots).append(item)
        stack.append(item)
    if not roots:
        raise PosterError(f"{ctx.where}: a {what} block needs at least one line")
    return roots


# ---------------------------------------------------------------------------
# bowtie
# ---------------------------------------------------------------------------


@block(
    "bowtie",
    "hazard:, top: (the top event), then threat: name | barrier, barrier and consequence: name | barrier lines",
    "hazard: Lithium cell\ntop: Thermal runaway\nthreat: Overcharge | Charger cut-off, Cell monitor\nthreat: Crush | Steel enclosure\nconsequence: Fire | Vent path, Fire wall\nconsequence: Toxic smoke | Smoke alarm",
)
def bowtie_html(code, opts, ctx):
    """Threats on the left and consequences on the right of a top event, each line crossed by its barriers:
    preventive on the left, mitigating on the right. The hazard is above the top event."""
    hazard, top, threats, consequences = "", "", [], []
    for line in _lines(code):
        key, _, rest = line.partition(":")
        key = key.strip().lower()
        cells = _cells(rest)
        if key == "hazard":
            hazard = rest.strip()
        elif key in ("top", "top event", "event"):
            top = rest.strip()
        elif key in ("threat", "consequence"):
            barriers = [b.strip() for b in cells[1].split(",") if b.strip()] if len(cells) > 1 else []
            (threats if key == "threat" else consequences).append((cells[0], barriers))
        else:
            raise PosterError(f"{ctx.where}: a bowtie line starts hazard:, top:, threat: or consequence:, not '{line}'")
    if not top or not (threats or consequences):
        raise PosterError(f"{ctx.where}: a bowtie needs a top: event and at least one threat: or consequence:")
    c = ctx.theme.colours
    rows = max(len(threats), len(consequences))
    row_h, box_w, box_h, head = 58, 112, 42, 74 if hazard else 14
    cx, cy, r = WIDTH / 2, head + rows * row_h / 2, 46
    out = []
    if hazard:  # a hazard sign: a box striped in the caution colours, joined to the top event
        out.append(
            f'<rect x="{cx - 80}" y="8" width="160" height="40" fill="{c["warning"]}" stroke="#1d1f27" stroke-width="2"/>'
        )
        out.append(_box_text(cx, 28, hazard, 148, SIZE, 2, BOLD + ' fill="#1d1f27"'))
        out.append(f'<line x1="{cx}" y1="48" x2="{cx}" y2="{cy - r}" {_stroke(ctx)}/>')
    for side, items, colour in ((-1, threats, mark_colour(ctx.theme)), (1, consequences, c["bad"])):
        for i, (name, barriers) in enumerate(items):
            y = head + (i + (rows - len(items)) / 2) * row_h + row_h / 2
            x_box = 4 if side < 0 else WIDTH - 4 - box_w
            edge = x_box + box_w if side < 0 else x_box
            # along the row to a knee beside the top event, then into its edge, the lines gathering towards it
            target_y = cy + (y - cy) * 0.6
            end_x = cx + side * math.sqrt(max(r * r - (target_y - cy) ** 2, 0))
            knee = cx + side * (r + 26)
            out.append(
                f'<path d="M{edge:.1f},{y:.1f} L{knee:.1f},{y:.1f} L{end_x:.1f},{target_y:.1f}" fill="none" {_stroke(ctx, "muted")}/>'
            )
            out.append(
                f'<rect x="{x_box}" y="{y - box_h / 2:.1f}" width="{box_w}" height="{box_h}" rx="4" fill="{colour}"/>'
            )
            out.append(_box_text(x_box + box_w / 2, y, name, box_w - 10, SIZE, 2, BOLD + ' fill="#fff"'))
            # barriers along the line between the box and the knee
            start, stop = (edge + 8, knee - 4) if side < 0 else (knee + 4, edge - 8)
            if barriers:
                span = (stop - start) / len(barriers)
                bw = min(62, span - 6)
                for k, barrier in enumerate(barriers):
                    bx = start + span * (k + 0.5)
                    out.append(
                        f'<rect x="{bx - bw / 2:.1f}" y="{y - 17:.1f}" width="{bw:.1f}" height="34" fill="{c["surface"]}" stroke="{c["strong"]}" stroke-width="1.5"/>'
                    )
                    out.append(
                        f'<rect x="{bx - bw / 2:.1f}" y="{y - 17:.1f}" width="4" height="34" fill="{c["good"]}"/>'
                    )
                    out.append(_box_text(bx + 2, y, barrier, bw - 10, 9.5, 3))
    out.append(f'<circle cx="{cx}" cy="{cy:.1f}" r="{r}" fill="{c["accent"]}" stroke="#fff" stroke-width="3"/>')
    out.append(_box_text(cx, cy, top, 2 * r - 12, SIZE, 3, BOLD + ' fill="#fff"'))
    height = head + rows * row_h + 26
    out.append(label(4, height - 6, "Threats and preventive barriers", SMALL, extra=_muted(ctx)))
    out.append(label(WIDTH - 4, height - 6, "Mitigating barriers and consequences", SMALL, "end", _muted(ctx)))
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "bow-tie diagram"), "chart"))


# ---------------------------------------------------------------------------
# fault-tree
# ---------------------------------------------------------------------------

GATES = ("or", "and", "xor", "pand", "inhibit")
LEAVES = ("basic", "undeveloped", "house", "transfer")
_K_OF_N = re.compile(r"^(\d+)\s*/\s*(\d+)$")


def _gate_path(kind, x, y, w, h):
    """The gate symbol ``kind`` with its output at ``x, y`` (top centre), ``w`` wide and ``h`` high."""
    left, right, bottom = x - w / 2, x + w / 2, y + h
    if kind in ("or", "xor") or _K_OF_N.match(kind):
        d = (f"M{left:.1f},{bottom:.1f} Q{left:.1f},{y + h * 0.35:.1f} {x:.1f},{y:.1f} Q{right:.1f},{y + h * 0.35:.1f} "
             f"{right:.1f},{bottom:.1f} Q{x:.1f},{bottom - h * 0.3:.1f} {left:.1f},{bottom:.1f} Z")  # fmt: skip
        if kind == "xor":
            d += f" M{left:.1f},{bottom + 5:.1f} Q{x:.1f},{bottom - h * 0.3 + 5:.1f} {right:.1f},{bottom + 5:.1f}"
        return d
    if kind == "inhibit":  # a hexagon, pointing up and down
        q = h / 4
        return (f"M{x:.1f},{y:.1f} L{right:.1f},{y + q:.1f} L{right:.1f},{bottom - q:.1f} L{x:.1f},{bottom:.1f} "
                f"L{left:.1f},{bottom - q:.1f} L{left:.1f},{y + q:.1f} Z")  # fmt: skip
    # and, pand: a flat bottom and a round top
    return f"M{left:.1f},{bottom:.1f} L{left:.1f},{y + h / 2:.1f} A{w / 2:.1f},{h / 2:.1f} 0 0 1 {right:.1f},{y + h / 2:.1f} L{right:.1f},{bottom:.1f} Z"


def _fault_node(item, ctx):
    kind, sep, rest = item.text.partition(":")
    if not sep:
        kind, rest = "", item.text
    kind = kind.strip().lower()
    cells = _cells(rest)
    if kind and kind not in GATES + LEAVES and not _K_OF_N.match(kind):
        raise PosterError(
            f"{ctx.where}: line {item.number} of the fault tree starts '{kind}:'. An event is or:, and:, xor:, "
            "pand:, inhibit: or k/n: (such as 2/3:) with events under it, or basic:, undeveloped:, house: or transfer:"
        )
    if item.children and kind in LEAVES:
        raise PosterError(f"{ctx.where}: line {item.number}: a {kind} event has no events under it")
    if item.children and not kind:
        raise PosterError(f"{ctx.where}: line {item.number}: give the gate of '{cells[0]}', such as or: or and:")
    if not item.children and kind and kind not in LEAVES:
        raise PosterError(f"{ctx.where}: line {item.number}: a {kind} gate needs the events under it, indented")
    m = _K_OF_N.match(kind)
    if m and not 1 <= int(m[1]) <= len(item.children) == int(m[2]):
        raise PosterError(f"{ctx.where}: line {item.number}: a {kind} gate needs {m[2]} events under it")
    node = Node(cells[0], data={"kind": kind or "basic", "p": cells[1] if len(cells) > 1 else "",
                                "if": cells[2] if len(cells) > 2 else ""})  # fmt: skip
    node.children = [_fault_node(child, ctx) for child in item.children]
    return node


@block(
    "fault-tree",
    "indented events: gate: event (or, and, xor, pand, inhibit, or k/n such as 2/3) with its causes under it, "
    "and basic:, undeveloped:, house: or transfer: causes; | probability; inhibit's | condition after that",
    "or: Node stops reporting\n  and: No power\n    basic: Cell flat | 1e-3\n    basic: Backup fails | 0.05\n  basic: Radio fault | 2e-4\n  undeveloped: Gateway down",
)
def fault_tree_html(code, opts, ctx):
    """A fault tree from its top event down: each event above the gate that joins its causes, and the basic
    (circle), undeveloped (diamond), house and transfer (triangle) events at its leaves."""
    roots = _indented(code, ctx, "fault-tree")
    if len(roots) != 1:
        raise PosterError(f"{ctx.where}: a fault tree has one top event: indent every other line under it")
    root = _fault_node(roots[0], ctx)
    across, depth = tidy(root)
    c = ctx.theme.colours
    unit = min(132, (WIDTH - 8) / (across + 1))
    box_w, box_h, gate_h, row = unit - 12, 44, 30, 118
    left = (WIDTH - (across + 1) * unit) / 2  # the tree in the middle of the picture
    x_of = lambda node: left + unit / 2 + node.x * unit  # noqa: E731
    out = []
    for node in root.walk():
        x, y = x_of(node), 8 + node.depth * row
        kind = node.data["kind"]
        out.append(
            f'<rect x="{x - box_w / 2:.1f}" y="{y}" width="{box_w:.1f}" height="{box_h}" fill="{c["surface"]}" stroke="{c["strong"]}" stroke-width="1.5"/>'
        )
        text_lines = 2 if node.data["p"] else 3
        out.append(_box_text(x, y + box_h / 2 - (6 if node.data["p"] else 0), node.label, box_w - 8, 11, text_lines))
        if node.data["p"]:
            out.append(label(x, y + box_h - 5, node.data["p"], 9.5, "middle", _muted(ctx)))
        below = y + box_h
        if node.children:
            gw = min(40, box_w * 0.6)
            out.append(f'<line x1="{x:.1f}" y1="{below}" x2="{x:.1f}" y2="{below + 8}" {_stroke(ctx)}/>')
            fill = mark_colour(ctx.theme) if kind != "inhibit" else c["accent"]
            out.append(f'<path d="{_gate_path(kind, x, below + 8, gw, gate_h)}" fill="{fill}" {_stroke(ctx)}/>')
            mark = {"and": "", "or": "", "xor": "", "inhibit": "", "pand": "P"}.get(kind, kind)
            if mark:
                out.append(label(x, below + 8 + gate_h * 0.72, mark, 10, "middle", BOLD + ' fill="#fff"'))
            if kind == "inhibit" and node.data["if"]:  # the condition, in an oval beside the gate
                ox = x + gw / 2 + 34
                out.append(
                    f'<line x1="{x + gw / 2:.1f}" y1="{below + 8 + gate_h / 2:.1f}" x2="{ox - 30:.1f}" y2="{below + 8 + gate_h / 2:.1f}" {_stroke(ctx)}/>'
                )
                out.append(
                    f'<ellipse cx="{ox:.1f}" cy="{below + 8 + gate_h / 2:.1f}" rx="30" ry="15" fill="{c["surface"]}" {_stroke(ctx)}/>'
                )
                out.append(_box_text(ox, below + 8 + gate_h / 2, node.data["if"], 54, 8.5, 2))
            bus = below + 8 + gate_h + 10
            out.append(
                f'<line x1="{x:.1f}" y1="{below + 8 + gate_h - 4:.1f}" x2="{x:.1f}" y2="{bus:.1f}" {_stroke(ctx)}/>'
            )
            xs = [x_of(child) for child in node.children]
            out.append(f'<line x1="{min(xs):.1f}" y1="{bus:.1f}" x2="{max(xs):.1f}" y2="{bus:.1f}" {_stroke(ctx)}/>')
            for cx in xs:
                out.append(f'<line x1="{cx:.1f}" y1="{bus:.1f}" x2="{cx:.1f}" y2="{y + row:.1f}" {_stroke(ctx)}/>')
        else:  # the leaf's symbol, under its box
            sy = below + 22
            out.append(f'<line x1="{x:.1f}" y1="{below}" x2="{x:.1f}" y2="{sy - 14:.1f}" {_stroke(ctx)}/>')
            fill = f'fill="{c["primary"]}"'
            if kind == "basic":
                out.append(f'<circle cx="{x:.1f}" cy="{sy:.1f}" r="14" {fill} {_stroke(ctx)}/>')
            elif kind == "undeveloped":
                out.append(
                    f'<path d="M{x:.1f},{sy - 14:.1f} L{x + 18:.1f},{sy:.1f} L{x:.1f},{sy + 14:.1f} L{x - 18:.1f},{sy:.1f} Z" {fill} {_stroke(ctx)}/>'
                )
            elif kind == "house":
                out.append(
                    f'<path d="M{x:.1f},{sy - 14:.1f} L{x + 14:.1f},{sy - 4:.1f} L{x + 14:.1f},{sy + 14:.1f} L{x - 14:.1f},{sy + 14:.1f} L{x - 14:.1f},{sy - 4:.1f} Z" {fill} {_stroke(ctx)}/>'
                )
            else:  # transfer
                out.append(
                    f'<path d="M{x:.1f},{sy - 14:.1f} L{x + 16:.1f},{sy + 14:.1f} L{x - 16:.1f},{sy + 14:.1f} Z" {fill} {_stroke(ctx)}/>'
                )
    height = 8 + depth * row + box_h + 44
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "fault tree"), "chart"))


# ---------------------------------------------------------------------------
# gsn
# ---------------------------------------------------------------------------

GSN_KINDS = ("goal", "strategy", "solution", "context", "assumption", "justification")
CONTEXTUAL = ("context", "assumption", "justification")
_GSN = re.compile(r"^(?P<kind>[a-z]+)(?:\s+(?P<id>[\w.-]+))?\s*:\s*(?P<text>.*)$", re.I)


def _gsn_item(item, ctx):
    m = _GSN.match(item.text)
    if not m or m["kind"].lower() not in GSN_KINDS:
        raise PosterError(
            f"{ctx.where}: line {item.number} of the GSN block is 'kind ID: text', with kind one of "
            f"{', '.join(GSN_KINDS)}, not '{item.text}'"
        )
    cells = _cells(m["text"])
    kind = m["kind"].lower()
    if kind in CONTEXTUAL + ("solution",) and any(
        _GSN.match(c.text) and _GSN.match(c.text)["kind"].lower() not in CONTEXTUAL for c in item.children
    ):  # noqa: E501
        raise PosterError(f"{ctx.where}: line {item.number}: a {kind} supports nothing, so nothing goes under it")
    undeveloped = any(cell.lower() == "undeveloped" for cell in cells[1:])
    return Node(cells[0], data={"kind": kind, "id": m["id"] or "", "undeveloped": undeveloped, "of": None})


def _gsn_tree(item, ctx):
    """The node of ``item`` with its supporting children; its contexts go beside it, as siblings after it."""
    node = _gsn_item(item, ctx)
    contexts, children = [], []
    for child in item.children:
        built = _gsn_tree(child, ctx)
        if built[0].data["kind"] in CONTEXTUAL:
            for c in built:
                c.data["of"] = node
            contexts += built
        else:
            children += built
    node.children = children
    return [node, *contexts]


def _gsn_shape(kind, x, y, w, h, c, stroke):
    left, top = x - w / 2, y
    if kind == "goal":
        return f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h}" fill="{c["surface"]}" {stroke}/>'
    if kind == "strategy":
        s = 12
        return f'<path d="M{left + s:.1f},{top:.1f} L{left + w:.1f},{top:.1f} L{left + w - s:.1f},{top + h:.1f} L{left:.1f},{top + h:.1f} Z" fill="{c["surface"]}" {stroke}/>'
    if kind == "solution":
        return f'<circle cx="{x:.1f}" cy="{top + h / 2:.1f}" r="{h / 2 + 6:.1f}" fill="{c["surface"]}" {stroke}/>'
    if kind == "context":
        return f'<rect x="{left:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2 - 4:.1f}" fill="{c["surface"]}" {stroke}/>'
    return f'<ellipse cx="{x:.1f}" cy="{top + h / 2:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" fill="{c["surface"]}" {stroke}/>'


@block(
    "gsn",
    "indented 'kind ID: text' lines: goal, strategy and solution supported by those under them; context, "
    "assumption and justification beside the one above them; | undeveloped",
    "goal G1: The node is safe to install\n  context C1: Indoor use, 0 to 40 °C\n  strategy S1: Argue over each hazard\n    goal G2: Overheating is prevented\n      solution Sn1: Thermal test report\n    goal G3: Venting is contained | undeveloped",
)
def gsn_html(code, opts, ctx):
    """A safety case in Goal Structuring Notation: goals (rectangles), strategies (parallelograms) and
    solutions (circles) joined by solid arrows, and contexts, assumptions and justifications beside the
    element they are about, joined by hollow arrows."""
    roots = _indented(code, ctx, "gsn")
    if len(roots) != 1:
        raise PosterError(f"{ctx.where}: a GSN block has one top goal: indent every other line under it")
    top = _gsn_tree(roots[0], ctx)
    root = Node("", children=top) if len(top) > 1 else top[0]  # contexts of the top goal sit beside it
    across, depth = tidy(root)
    shift = 1 if root is not top[0] else 0
    c = ctx.theme.colours
    unit = min(150, (WIDTH - 8) / (across + 1))
    box_w, box_h, row = unit - 14, 64, 112
    stroke = _stroke(ctx)
    left = (WIDTH - (across + 1) * unit) / 2  # the tree in the middle of the picture
    place = {id(node): (left + unit / 2 + node.x * unit, 8 + (node.depth - shift) * row) for node in root.walk()}
    out = []
    for node in root.walk():
        if node is root and shift:
            continue
        x, y = place[id(node)]
        kind = node.data["kind"]
        for child in node.children:  # supported by: a solid arrow to each child
            cx, cy = place[id(child)]
            top_y = cy - (6 if child.data["kind"] == "solution" else 0)
            out.append(
                f'<path d="M{x:.1f},{y + box_h:.1f} L{x:.1f},{(y + box_h + top_y) / 2:.1f} L{cx:.1f},{(y + box_h + top_y) / 2:.1f} L{cx:.1f},{top_y - 1:.1f}" fill="none" {stroke}/>'
            )
            out.append(_arrowhead(cx, top_y, 90, 9, c["strong"]))
        if node.data["of"] is not None:  # in context of: a hollow arrow from the element it is about
            px, py = place[id(node.data["of"])]
            out.append(
                f'<line x1="{px + box_w / 2:.1f}" y1="{py + box_h / 2:.1f}" x2="{x - box_w / 2 - 1:.1f}" y2="{y + box_h / 2:.1f}" {stroke}/>'
            )
            out.append(_arrowhead(x - box_w / 2, y + box_h / 2, 0, 9, "#fff").replace("/>", f" {stroke}/>"))
        out.append(_gsn_shape(kind, x, y, box_w, box_h, c, stroke))
        width = box_w - (34 if kind in ("solution", "assumption", "justification") else 14)
        if node.data["id"]:
            out.append(label(x, y + 14, node.data["id"], 10.5, "middle", BOLD))
        out.append(
            _box_text(
                x, y + box_h / 2 + (6 if node.data["id"] else 0), node.label, width, 10.5, 3 if node.data["id"] else 4
            )
        )
        if kind in ("assumption", "justification"):
            out.append(label(x + box_w / 2 - 6, y + box_h, kind[0].upper(), 11, "end", BOLD))
        if node.data["undeveloped"]:
            d = y + box_h + 6
            out.append(
                f'<path d="M{x:.1f},{d:.1f} L{x + 9:.1f},{d + 9:.1f} L{x:.1f},{d + 18:.1f} L{x - 9:.1f},{d + 9:.1f} Z" fill="#fff" {stroke}/>'
            )
    height = 8 + (depth - shift) * row + box_h + 30
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "GSN safety case"), "chart"))


# ---------------------------------------------------------------------------
# kmap
# ---------------------------------------------------------------------------

GRAY = {1: [0, 1], 2: [0, 1, 3, 2]}


def _primes(ones, dont, n):
    """The prime implicants of the minterms ``ones`` (with the don't-cares ``dont``), as strings of 0, 1 and -."""
    terms = {format(m, f"0{n}b") for m in ones | dont}
    primes = set()
    while terms:
        merged, used = set(), set()
        for a, b in itertools.combinations(sorted(terms), 2):
            diff = [i for i in range(n) if a[i] != b[i]]
            if len(diff) == 1 and "-" not in (a[diff[0]], b[diff[0]]):
                merged.add(a[: diff[0]] + "-" + a[diff[0] + 1 :])
                used |= {a, b}
        primes |= terms - used
        terms = merged
    return sorted(primes)


def _covers(term, m, n):
    bits = format(m, f"0{n}b")
    return all(t in ("-", b) for t, b in zip(term, bits))


def minimal_cover(ones, dont, n):
    """The fewest prime implicants that cover every one, and of those the fewest literals."""
    if not ones:
        return []
    primes = [p for p in _primes(ones, dont, n) if any(_covers(p, m, n) for m in ones)]
    for size in range(1, len(primes) + 1):
        found = [
            combo for combo in itertools.combinations(primes, size)
            if all(any(_covers(p, m, n) for p in combo) for m in ones)
        ]  # fmt: skip
        if found:
            return list(min(found, key=lambda combo: (-sum(p.count("-") for p in combo), combo)))
    return primes


def expression(cover, names):
    """The sum of products of ``cover``, with a prime for a variable that is 0: A′B + CD."""
    if not cover:
        return "0"
    terms = []
    for term in cover:
        text = "".join(name + ("′" if bit == "0" else "") for name, bit in zip(names, term) if bit != "-")
        terms.append(text or "1")
    return " + ".join(terms)


def _runs(indices, size):
    """``indices`` of a circular row of ``size`` as runs: (start, length, whether it wraps past the end)."""
    chosen = set(indices)
    if len(chosen) == size:
        return [(0, size, False)]
    runs = []
    for i in range(size):
        if i in chosen and (i - 1) % size not in chosen:
            length = 0
            while (i + length) % size in chosen:
                length += 1
            runs.append((i, length, i + length > size))
    return runs


def _split(start, length, size):
    """A run that wraps, as its two pieces: up to the end, and from the start."""
    if start + length <= size:
        return [(start, length)]
    return [(start, size - start), (0, start + length - size)]


@block(
    "kmap",
    "vars: A B C D (2 to 4), ones: the minterms that are 1, dont: those that do not matter; loops=no, name=",
    "vars: A B C D\nones: 0 2 5 7 8 10 13 15\ndont: 6",
)
def kmap_html(code, opts, ctx):
    """A Karnaugh map of 2 to 4 variables in Gray-code order, with the loops of a minimal cover of its ones,
    wrapping round its edges where they do, and the simplified expression under it."""
    names, ones, dont = [], set(), set()
    for line in _lines(code):
        key, _, rest = line.partition(":")
        key = key.strip().lower()
        try:
            values = {int(v) for v in re.split(r"[,\s]+", rest.strip()) if v}
        except ValueError:
            values = None
        if key in ("vars", "variables"):
            names = rest.split()
        elif key in ("ones", "minterms") and values is not None:
            ones = values
        elif key in ("dont", "don't", "dontcare") and values is not None:
            dont = values
        else:
            raise PosterError(f"{ctx.where}: a kmap line is vars:, ones: or dont: with whole numbers, not '{line}'")
    n = len(names)
    if not 2 <= n <= 4:
        raise PosterError(f"{ctx.where}: a kmap has 2, 3 or 4 vars:, such as vars: A B C")
    out_of = sorted(m for m in ones | dont if not 0 <= m < 2**n)
    if out_of:
        raise PosterError(f"{ctx.where}: {out_of[0]} is not a minterm of {n} variables (0 to {2**n - 1})")
    if ones & dont:
        raise PosterError(f"{ctx.where}: {min(ones & dont)} is both a one and a don't-care")
    row_bits, col_bits = n // 2, n - n // 2
    rows, cols = GRAY[row_bits], GRAY[col_bits]
    c = ctx.theme.colours
    cell, x0, y0 = 58, 150, 64
    out = []
    # the corner: the row variables and the column variables, either side of a diagonal
    out.append(f'<line x1="{x0 - 64}" y1="{y0 - 52}" x2="{x0 - 8}" y2="{y0 - 8}" {_stroke(ctx, "muted", 1)}/>')
    out.append(label(x0 - 44, y0 - 10, "".join(names[:row_bits]), SIZE, "end", BOLD))
    out.append(label(x0 - 30, y0 - 40, "".join(names[row_bits:]), SIZE, "start", BOLD))
    for j, col in enumerate(cols):
        out.append(label(x0 + (j + 0.5) * cell, y0 - 15, format(col, f"0{col_bits}b"), SIZE, "middle", _muted(ctx)))
    for i, row in enumerate(rows):
        out.append(label(x0 - 15, y0 + (i + 0.5) * cell + 4, format(row, f"0{row_bits}b"), SIZE, "end", _muted(ctx)))
        for j, col in enumerate(cols):
            m = (row << col_bits) | col
            x, y = x0 + j * cell, y0 + i * cell
            out.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{c["surface"]}" stroke="{c["border"]}"/>'
            )
            value = "1" if m in ones else "X" if m in dont else "0"
            out.append(
                label(x + cell / 2, y + cell / 2 + 6, value, 17, "middle", BOLD if value == "1" else _muted(ctx))
            )
            out.append(label(x + cell - 4, y + cell - 5, str(m), 8.5, "end", _muted(ctx)))
    out.append(
        f'<rect x="{x0}" y="{y0}" width="{cell * len(cols)}" height="{cell * len(rows)}" fill="none" {_stroke(ctx, "strong", 2)}/>'
    )
    cover = minimal_cover(ones, dont, n)
    if opts.get("loops", "yes").lower() not in ("no", "false"):
        colours = series_colours(ctx.theme)
        right, bottom = x0 + len(cols) * cell, y0 + len(rows) * cell
        for k, term in enumerate(cover):
            colour, inset = colours[k % len(colours)], 5 + (k % 4) * 3
            covered = [m for m in range(2**n) if _covers(term, m, n)]
            row_idx = {rows.index(m >> col_bits) for m in covered}
            col_idx = {cols.index(m & (2**col_bits - 1)) for m in covered}
            for r_start, r_len, r_wrap in _runs(row_idx, len(rows)):
                for c_start, c_len, c_wrap in _runs(col_idx, len(cols)):
                    for rs, rl in _split(r_start, r_len, len(rows)):
                        for cs, cl in _split(c_start, c_len, len(cols)):
                            x1, y1 = x0 + cs * cell + inset, y0 + rs * cell + inset
                            x2, y2 = x0 + (cs + cl) * cell - inset, y0 + (rs + rl) * cell - inset
                            # a piece of a loop that wraps round is open at the map's edge: it runs past it
                            x1 = x0 - 7 if c_wrap and cs == 0 else x1
                            x2 = right + 7 if c_wrap and cs + cl == len(cols) else x2
                            y1 = y0 - 7 if r_wrap and rs == 0 else y1
                            y2 = bottom + 7 if r_wrap and rs + rl == len(rows) else y2
                            out.append(
                                f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2 - x1:.1f}" height="{y2 - y1:.1f}" rx="14" fill="{colour}" fill-opacity=".12" stroke="{colour}" stroke-width="2.5"/>'
                            )
    base = y0 + len(rows) * cell + 38
    out.append(label(x0, base, f"{opts.get('name', 'F')} = {expression(cover, names)}", 16, "start", BOLD))
    return _fig(opts, svg(WIDTH, base + 12, "".join(out), opts.get("title", "Karnaugh map"), "chart"))


# ---------------------------------------------------------------------------
# plc-ladder
# ---------------------------------------------------------------------------

CONTACTS = {"no": "", "nc": "/", "p": "P", "n": "N"}
COILS = {"coil": "", "ncoil": "/", "set": "S", "reset": "R"}
BOXES = ("ton", "tof", "tp", "ctu", "ctd", "ctud")


def _ladder_element(text, ctx):
    words = text.split()
    if not words or words[0].lower() not in (*CONTACTS, *COILS, *BOXES):
        raise PosterError(
            f"{ctx.where}: a ladder element starts NO, NC, P, N (contacts), COIL, NCOIL, SET, RESET (coils) or "
            f"{', '.join(b.upper() for b in BOXES)} (boxes), then its tag: not '{text}'"
        )
    return words[0].lower(), words[1] if len(words) > 1 else "", " ".join(words[2:])


def _draw_element(kind, tag, param, x, y, out, ctx):
    """One element centred at ``x`` on the wire at ``y``, 44 wide, with its tag above it and its value under it."""
    stroke = _stroke(ctx, "strong", 2)
    out.append(f'<rect x="{x - 23}" y="{y - 3}" width="46" height="6" fill="{ctx.theme.colours["page"]}"/>')
    if kind in CONTACTS:
        out.append(
            f'<line x1="{x - 22}" y1="{y}" x2="{x - 8}" y2="{y}" {stroke}/><line x1="{x + 8}" y1="{y}" x2="{x + 22}" y2="{y}" {stroke}/>'
        )
        out.append(
            f'<line x1="{x - 8}" y1="{y - 12}" x2="{x - 8}" y2="{y + 12}" {stroke}/><line x1="{x + 8}" y1="{y - 12}" x2="{x + 8}" y2="{y + 12}" {stroke}/>'
        )
        if kind == "nc":
            out.append(f'<line x1="{x - 10}" y1="{y + 12}" x2="{x + 10}" y2="{y - 12}" {stroke}/>')
        elif CONTACTS[kind]:
            out.append(label(x, y + 4, CONTACTS[kind], 10, "middle", BOLD))
    elif kind in COILS:
        out.append(
            f'<line x1="{x - 22}" y1="{y}" x2="{x - 11}" y2="{y}" {stroke}/><line x1="{x + 11}" y1="{y}" x2="{x + 22}" y2="{y}" {stroke}/>'
        )
        out.append(
            f'<path d="M{x - 6},{y - 13} Q{x - 15},{y} {x - 6},{y + 13} M{x + 6},{y - 13} Q{x + 15},{y} {x + 6},{y + 13}" fill="none" {stroke}/>'
        )
        if kind == "ncoil":
            out.append(f'<line x1="{x - 6}" y1="{y + 10}" x2="{x + 6}" y2="{y - 10}" {stroke}/>')
        elif COILS[kind]:
            out.append(label(x, y + 4, COILS[kind], 10, "middle", BOLD))
    else:  # a function box
        out.append(
            f'<rect x="{x - 22}" y="{y - 18}" width="44" height="36" fill="{ctx.theme.colours["surface"]}" {stroke}/>'
        )
        out.append(label(x, y + 4, kind.upper(), 10, "middle", BOLD))
    out.append(label(x, y - 21, tag, SMALL, "middle", BOLD))
    if param:
        out.append(label(x, y + 31, param, 9.5, "middle", _muted(ctx)))


@block(
    "plc-ladder",
    "rung: comment, then a NO tag | NC tag | COIL tag line in series, and branch: lines in parallel with its "
    "first elements; NO, NC, P, N, COIL, NCOIL, SET, RESET, TON, TOF, TP, CTU, CTD, CTUD",
    "rung: Start and stop the pump\nNO Start | NC Stop | COIL Pump\nbranch: NO Pump\nrung: Run the pump for 30 s at most\nNO Pump | TON T1 PT=30s\nrung: Stop it after that\nNO T1 | RESET Pump",
)
def plc_ladder_html(code, opts, ctx):
    """A ladder diagram: power rails at each side and a rung for each ``rung:``, its elements in series and its
    output at the right end, and ``branch:`` paths in parallel with its first elements, such as a seal-in."""
    rungs: list[dict] = []
    for line in _lines(code):
        key, sep, rest = line.partition(":")
        word = key.strip().lower() if sep else ""
        if word == "rung":
            rungs.append({"note": rest.strip(), "series": [], "branches": []})
            continue
        if not rungs:
            rungs.append({"note": "", "series": [], "branches": []})
        if word == "branch":
            if not rungs[-1]["series"]:
                raise PosterError(f"{ctx.where}: a branch: goes under the elements of its rung")
            rungs[-1]["branches"].append([_ladder_element(e, ctx) for e in _cells(rest) if e])
        elif rungs[-1]["series"]:
            raise PosterError(f"{ctx.where}: a rung has one line of elements in series; start another with rung:")
        else:
            rungs[-1]["series"] = [_ladder_element(e, ctx) for e in _cells(line) if e]
    rungs = [rung for rung in rungs if rung["series"]]
    if not rungs:
        raise PosterError(f"{ctx.where}: a ladder needs a line of elements, such as NO Start | COIL Pump")
    left, right, slot = 24, WIDTH - 24, 92
    out, y = [], 12
    for n, rung in enumerate(rungs, 1):
        series = rung["series"]
        out.append(label(left + 8, y + 10, f"{n}  {rung['note']}".strip(), SMALL, extra=_muted(ctx)))
        wire = y + 48
        output = len(series) > 1 and series[-1][0] in (*COILS, *BOXES)
        inputs = series[:-1] if output else series
        xs = [left + 52 + slot * i for i in range(len(inputs))]
        if output:
            xs.append(right - 52)
        if xs[len(inputs) - 1] > (right - 52 - slot + 8 if output else right - 30):
            raise PosterError(f"{ctx.where}: rung {n} has more elements than fit on a line: split it into two rungs")
        out.append(f'<line x1="{left}" y1="{wire}" x2="{right}" y2="{wire}" {_stroke(ctx, "strong", 2)}/>')
        for (kind, tag, param), x in zip(series, xs):
            _draw_element(kind, tag, param, x, wire, out, ctx)
        bottom = wire + 32
        for k, branch in enumerate(rung["branches"]):
            by = wire + 58 * (k + 1)
            if len(branch) > len(inputs):
                raise PosterError(f"{ctx.where}: a branch of rung {n} has more elements than its rung has inputs")
            start, stop = left + 52 - slot / 2 + 4, left + 52 + slot * (len(branch) - 1) + slot / 2 - 4
            out.append(
                f'<path d="M{start:.1f},{wire} L{start:.1f},{by} L{stop:.1f},{by} L{stop:.1f},{wire}" fill="none" {_stroke(ctx, "strong", 2)}/>'
            )
            for i, (kind, tag, param) in enumerate(branch):
                _draw_element(kind, tag, param, left + 52 + slot * i, by, out, ctx)
            bottom = by + 32
        y = bottom + 10
    out.append(f'<line x1="{left}" y1="6" x2="{left}" y2="{y}" {_stroke(ctx, "strong", 4)}/>')
    out.append(f'<line x1="{right}" y1="6" x2="{right}" y2="{y}" {_stroke(ctx, "strong", 4)}/>')
    return _fig(opts, svg(WIDTH, y + 6, "".join(out), opts.get("title", "ladder diagram"), "chart"))


# ---------------------------------------------------------------------------
# structogram
# ---------------------------------------------------------------------------

_STRUCT = re.compile(r"^(if|else|while|for|repeat|until|case|when)\b\s*(.*)$", re.I)


def _statements(items, ctx):
    """The indented lines as statements: (kind, text, bodies)."""
    out: list = []
    for item in items:
        m = _STRUCT.match(item.text)
        word, text = (m[1].lower(), m[2].strip()) if m else ("do", item.text)
        if word == "else":
            if not out or out[-1][0] != "if" or out[-1][2][1] is not None:
                raise PosterError(f"{ctx.where}: line {item.number}: an else follows an if, at the same indent")
            out[-1] = ("if", out[-1][1], [out[-1][2][0], _statements(item.children, ctx)])
        elif word == "until":
            if not out or out[-1][0] != "repeat" or out[-1][1]:
                raise PosterError(f"{ctx.where}: line {item.number}: an until follows a repeat, at the same indent")
            out[-1] = ("repeat", text, out[-1][2])
        elif word == "when":
            raise PosterError(f"{ctx.where}: line {item.number}: a when goes under a case, indented")
        elif word == "case":
            branches = []
            for child in item.children:
                cm = _STRUCT.match(child.text)
                if not cm or cm[1].lower() not in ("when", "else"):
                    raise PosterError(f"{ctx.where}: line {child.number}: under a case, each line is when VALUE")
                value = cm[2].strip() if cm[1].lower() == "when" else "else"
                branches.append((value, _statements(child.children, ctx)))
            if not branches:
                raise PosterError(f"{ctx.where}: line {item.number}: a case needs when lines under it")
            out.append(("case", text, branches))
        elif word == "if":
            out.append(("if", text, [_statements(item.children, ctx), None]))
        elif word in ("while", "for", "repeat"):
            out.append((word, text if word != "repeat" else "", [_statements(item.children, ctx)]))
        elif item.children:
            raise PosterError(
                f"{ctx.where}: line {item.number}: only if, else, while, for, repeat and case have lines under them"
            )
        else:
            out.append(("do", text, []))
    for kind, text, _ in out:
        if kind == "repeat" and not text:
            raise PosterError(f"{ctx.where}: a repeat needs an until line after its steps, at its own indent")
    return out


def _fill(x, y, w, h, out, ctx):
    """A blank box that fills the shorter side of a decision down to the taller."""
    if h > 0:
        c = ctx.theme.colours
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{c["surface"]}" {_stroke(ctx, "strong", 1.2)}/>'
        )


def _struct_draw(statements, x, y, w, out, ctx):
    """Draw ``statements`` from ``y`` in a column ``w`` wide at ``x``; return the height used."""
    c, stroke = ctx.theme.colours, _stroke(ctx, "strong", 1.2)
    start = y
    if not statements:  # an empty branch: a box with a dash, as the notation has
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="28" fill="{c["surface"]}" {stroke}/>')
        out.append(label(x + w / 2, y + 18, "—", SIZE, "middle", _muted(ctx)))
        return 28
    for kind, text, bodies in statements:
        if kind == "do":
            lines = wrap(text, w - 14, SIZE)
            h = 12 + 15 * len(lines)
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" fill="{c["surface"]}" {stroke}/>')
            out += [label(x + 7, y + 19 + n * 15, part, SIZE) for n, part in enumerate(lines)]
            y += h
        elif kind in ("if", "case"):
            branches = [("yes", bodies[0]), ("no", bodies[1] or [])] if kind == "if" else bodies
            k = len(branches)
            head = 30 + 15 * len(wrap(text, w * 0.5, SIZE, True))
            # the triangle's point is under the last branch for a case, between the two for a decision
            point = x + w / 2 if kind == "if" else x + w * (k - 1) / k
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{head}" fill="{c["code"]}" {stroke}/>')
            out.append(
                f'<path d="M{x:.1f},{y:.1f} L{point:.1f},{y + head:.1f} L{x + w:.1f},{y:.1f}" fill="none" {stroke}/>'
            )
            out.append(
                _box_text(point if kind == "if" else x + w * 0.62, y + head * 0.34, text, w * 0.5, SIZE, 3, BOLD)
            )
            bw = w / k
            for n, (value, _) in enumerate(branches):
                anchor = "start" if n == 0 else "end" if n == k - 1 else "middle"
                tx = x + 6 if n == 0 else x + w - 6 if n == k - 1 else x + bw * (n + 0.5)
                out.append(label(tx, y + head - 6, value, SMALL, anchor, _muted(ctx)))
            y += head
            sub: list[str] = []
            heights = [_struct_draw(body, x + bw * n, y, bw, sub, ctx) for n, (_, body) in enumerate(branches)]
            tall = max(heights)
            for n, h in enumerate(heights):
                _fill(x + bw * n, y + h, bw, tall - h, sub, ctx)
            out += sub
            y += tall
        else:  # while and for test at the top, repeat at the bottom; the body is indented on a gutter
            gutter = 26
            lines = wrap(f"{kind} {text}" if kind != "repeat" else f"until {text}", w - 16, SIZE, True)
            band = 10 + 15 * len(lines)
            sub = []
            body_h = _struct_draw(bodies[0], x + gutter, y + (band if kind != "repeat" else 0), w - gutter, sub, ctx)
            total = band + body_h
            out.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{total:.1f}" fill="{c["code"]}" {stroke}/>'
            )
            text_y = y + 17 if kind != "repeat" else y + body_h + 17
            out += [label(x + 8, text_y + n * 15, part, SIZE, extra=BOLD) for n, part in enumerate(lines)]
            out += sub
            y += total
    return y - start


@block(
    "structogram",
    "indented steps; if COND with else, while COND, for X, repeat then until COND, case X with when VALUE lines",
    "Wake on the timer\nRead the sensor\nif Reading changed?\n  Send it\nelse\n  Count the skip\nwhile Queue not empty\n  Send the next message\nSleep",
)
def structogram_html(code, opts, ctx):
    """A Nassi-Shneiderman diagram: steps as boxes one under the other, a decision as a triangle over its two
    branches, a loop as a box round its body, and a case as a triangle over each of its branches."""
    statements = _statements(_indented(code, ctx, "structogram"), ctx)
    out: list[str] = []
    height = _struct_draw(statements, 1, 1, WIDTH - 2, out, ctx)
    return _fig(opts, svg(WIDTH, height + 2, "".join(out), opts.get("title", "structogram"), "chart"))


# ---------------------------------------------------------------------------
# n2
# ---------------------------------------------------------------------------


@block(
    "n2",
    "items: A, B, C, then A -> B | what A gives B lines; the items are on the diagonal, outputs along the row",
    "items: Sensor, Controller, Radio, Cloud\nSensor -> Controller | Reading over I2C\nController -> Radio | Message\nRadio -> Cloud | MQTT publish\nCloud -> Controller | New settings",
)
def n2_html(code, opts, ctx):
    """An N-squared chart: the items on the diagonal, and what each gives another in its row, in that one's
    column. Feed-forward interfaces are above the diagonal; feedback, below it, is shaded."""
    items, links = [], {}
    for line in _lines(code):
        if line.lower().startswith("items:"):
            items = [name.strip() for name in line.split(":", 1)[1].split(",") if name.strip()]
            continue
        m = re.match(r"^(.+?)\s*->\s*(.+?)\s*(?:\|\s*(.*))?$", line)
        if not m:
            raise PosterError(f"{ctx.where}: an n2 line is items: A, B or A -> B | interface, not '{line}'")
        links[(m[1].strip(), m[2].strip())] = (m[3] or "").strip()
    if items:
        for name in (name for pair in links for name in pair):
            if name not in items:
                raise PosterError(f"{ctx.where}: '{name}' is not one of the items: {', '.join(items)}")
    else:  # the items in the order the lines name them
        items = list(dict.fromkeys(name for pair in links for name in pair))
    if len(items) < 2:
        raise PosterError(f"{ctx.where}: an n2 chart needs at least two items")
    c = ctx.theme.colours
    n = len(items)
    cell = min(120, (WIDTH - 2) / n)
    out = []
    for i, a in enumerate(items):
        for j, b in enumerate(items):
            x, y = 1 + j * cell, 1 + i * cell
            if i == j:
                out.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" fill="{c["primary"]}" stroke="#fff" stroke-width="2"/>'
                )
                out.append(
                    _box_text(x + cell / 2, y + cell / 2, a, cell - 12, SIZE, 4, BOLD + f' fill="{c["on-primary"]}"')
                )
                continue
            text = links.get((a, b))
            fill = c["callout"] if text is not None and i > j else c["surface"]
            out.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" fill="{fill}" stroke="{c["border"]}"/>'
            )
            if text is not None:
                out.append(_box_text(x + cell / 2, y + cell / 2, text or "•", cell - 12, SMALL, 5))
    bottom = n * cell + 22
    note = "Each row: what its item gives. Each column: what its item takes. Shaded: feedback."
    out.append(label(1, bottom, note, SMALL, extra=_muted(ctx)))
    return _fig(opts, svg(WIDTH, bottom + 8, "".join(out), opts.get("title", "N-squared chart"), "chart"))


# ---------------------------------------------------------------------------
# idef0
# ---------------------------------------------------------------------------

ROLES = {"in": "inputs", "input": "inputs", "out": "outputs", "output": "outputs", "control": "controls",
         "mech": "mechanisms", "mechanism": "mechanisms"}  # fmt: skip


@block(
    "idef0",
    "box: A1 Function lines, each followed by in:, out:, control: and mech: lines; an output named as a later "
    "box's input or control joins them",
    "box: A1 Measure the air\nin: Air\ncontrol: Sample interval\nout: Reading\nmech: Sensor\nbox: A2 Send the reading\nin: Reading\ncontrol: Radio settings\nout: Message\nmech: Radio",
)
def idef0_html(code, opts, ctx):
    """IDEF0 function boxes down a staircase: inputs enter at the left, outputs leave at the right, controls come
    in from the top and mechanisms from below. An output that is a later box's input or control is one arrow."""
    boxes: list[dict] = []
    for line in _lines(code):
        key, _, rest = line.partition(":")
        key = key.strip().lower()
        if key == "box":
            words = rest.split(maxsplit=1)
            node = words[0] if len(words) > 1 and re.match(r"^A\d+$", words[0], re.I) else ""
            name = words[1] if node else rest.strip()
            boxes.append({"node": node, "name": name, "inputs": [], "outputs": [], "controls": [], "mechanisms": []})
        elif key in ROLES and boxes:
            boxes[-1][ROLES[key]] += [v.strip() for v in rest.split(",") if v.strip()]
        else:
            raise PosterError(
                f"{ctx.where}: an idef0 line is box:, or in:, out:, control: or mech: under a box, not '{line}'"
            )
    if not boxes:
        raise PosterError(f"{ctx.where}: an idef0 block needs at least one box: line")
    if len(boxes) > 5:
        raise PosterError(f"{ctx.where}: an idef0 diagram shows at most 5 boxes: draw the detail of one in another")
    c, n = ctx.theme.colours, len(boxes)
    bw, bh, margin_l, margin_r = 124, 62, 116, 112
    step_x = (WIDTH - margin_l - margin_r - bw) / (n - 1) if n > 1 else 0
    step_y, top = 100, 46
    stroke = _stroke(ctx, "strong", 1.5)
    out = []

    def arrow(points, text, at):
        out.append(f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in points)}" fill="none" {stroke}/>')
        (x1, y1), (x2, y2) = points[-2], points[-1]
        out.append(_arrowhead(x2, y2, math.degrees(math.atan2(y2 - y1, x2 - x1)), 8, c["strong"]))
        out.append(label(at[0], at[1], text, SMALL))

    place = [(margin_l + i * step_x, top + i * step_y) for i in range(n)]
    joined: set[tuple[int, str]] = set()
    for i, box in enumerate(boxes):
        x, y = place[i]
        for k, name in enumerate(box["outputs"]):
            oy = y + bh * (k + 1) / (len(box["outputs"]) + 1)
            target = next(
                ((j, role) for j in range(i + 1, n) for role in ("inputs", "controls") if name in boxes[j][role]), None
            )
            if target is None:
                arrow([(x + bw, oy), (WIDTH - 6, oy)], name, (x + bw + 8, oy - 5))
                continue
            j, role = target
            joined.add((j, name))
            tx, ty = place[j]
            if role == "inputs":
                iy = ty + bh * (boxes[j]["inputs"].index(name) + 1) / (len(boxes[j]["inputs"]) + 1)
                knee = x + bw + 16 + 8 * k
                arrow([(x + bw, oy), (knee, oy), (knee, iy), (tx, iy)], name, (x + bw + 6, oy - 5))
            else:
                cx = tx + bw * (boxes[j]["controls"].index(name) + 1) / (len(boxes[j]["controls"]) + 1)
                arrow([(x + bw, oy), (cx, oy), (cx, ty)], name, (x + bw + 6, oy - 5))
    for i, box in enumerate(boxes):
        x, y = place[i]
        for k, name in enumerate(box["inputs"]):
            if (i, name) not in joined:
                iy = y + bh * (k + 1) / (len(box["inputs"]) + 1)
                arrow([(6, iy), (x, iy)], name, (8, iy - 5))
        for k, name in enumerate(box["controls"]):
            if (i, name) not in joined:
                cx = x + bw * (k + 1) / (len(box["controls"]) + 1)
                arrow([(cx, y - 34), (cx, y)], name, (cx + 4, y - 26))
        for k, name in enumerate(box["mechanisms"]):
            mx = x + bw * (k + 1) / (len(box["mechanisms"]) + 1)
            arrow([(mx, y + bh + 34), (mx, y + bh)], name, (mx + 4, y + bh + 30))
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{bh}" fill="{c["surface"]}" {_stroke(ctx, "strong", 2)}/>'
        )
        out.append(_box_text(x + bw / 2, y + bh / 2 - 4, box["name"], bw - 14, SIZE, 3, BOLD))
        if box["node"]:
            out.append(label(x + bw - 5, y + bh - 5, box["node"].upper(), 10, "end", _muted(ctx)))
    height = top + (n - 1) * step_y + bh + 44
    return _fig(opts, svg(WIDTH, height, "".join(out), opts.get("title", "IDEF0 diagram"), "chart"))


# ---------------------------------------------------------------------------
# vsm
# ---------------------------------------------------------------------------


def _amount(text):
    m = re.match(r"\s*(-?[\d.,]+)\s*(.*)$", text or "")
    return (float(m[1].replace(",", "")), m[2].strip()) if m else (None, text)


def _total(values):
    """The sum of amounts in one unit, such as 3.5 days; amounts in different units are listed."""
    parsed = [_amount(v) for v in values if v]
    units = {unit.removesuffix("s") if len(unit) > 1 else unit for _, unit in parsed}  # a day and 2 days
    if parsed and all(value is not None for value, _ in parsed) and len(units) == 1:
        total, unit = round(sum(value for value, _ in parsed), 6), units.pop()
        plural = unit + "s" if total != 1 and any(u == unit + "s" for _, u in parsed) else unit
        return f"{number(total)} {plural}".strip()
    return " + ".join(values) or "—"


def _factory(x, y, w, h, colour):
    """A factory: a saw-tooth roof over a box."""
    tooth = w / 3
    d = f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + h * 0.4:.1f}"
    for t in range(3):
        d += f" L{x + tooth * (t + 1):.1f},{y:.1f} L{x + tooth * (t + 1):.1f},{y + h * 0.4:.1f}"
    d += f" L{x + w:.1f},{y + h:.1f} Z"
    return f'<path d="{d}" fill="{colour}"/>'


@block(
    "vsm",
    "supplier: name | detail, customer: name | detail, then process: name | C/T 40 s | data and inventory: "
    "amount lines in flow order",
    "supplier: Cell maker | Weekly\ncustomer: Installer | 400 a day\ninventory: 5 days\nprocess: Solder | C/T 40 s | Uptime 92 %\ninventory: 2 days\nprocess: Test | C/T 30 s | 1 operator\ninventory: 1 day\nprocess: Pack | C/T 20 s",
)
def vsm_html(code, opts, ctx):
    """A value stream map: the supplier and the customer, process boxes with their data under them, inventory
    triangles between them, and the timeline of waiting (up) and processing (down) with its totals."""
    supplier = customer = None
    flow: list[tuple] = []
    for line in _lines(code):
        key, _, rest = line.partition(":")
        key, cells = key.strip().lower(), _cells(rest)
        if key == "supplier":
            supplier = cells
        elif key == "customer":
            customer = cells
        elif key in ("process", "inventory"):
            flow.append((key, cells[0], cells[1:]))
        else:
            raise PosterError(f"{ctx.where}: a vsm line is supplier:, customer:, process: or inventory:, not '{line}'")
    if not any(kind == "process" for kind, *_ in flow):
        raise PosterError(f"{ctx.where}: a value stream map needs at least one process: line")
    c = ctx.theme.colours
    weights = [1.0 if kind == "process" else 0.55 for kind, *_ in flow]
    unit, spans, at = (WIDTH - 12) / sum(weights), [], 6.0
    for weight in weights:
        spans.append((at, at + weight * unit))
        at += weight * unit
    band, box_h, line = 96, 44, _stroke(ctx, "muted", 1.5)
    out = []
    for place, party in ((6, supplier), (WIDTH - 90, customer)):
        if party:
            out.append(_factory(place, 8, 84, 40, mark_colour(ctx.theme)))
            out.append(label(place + 42, 62, party[0], SMALL, "middle", BOLD))
            if len(party) > 1:
                out.append(label(place + 42, 75, party[1], 9.5, "middle", _muted(ctx)))
    # the flow, pushed along under the boxes and triangles
    for (x1, x2), nxt in zip(spans, spans[1:]):
        out.append(
            f'<line x1="{x2 - 4:.1f}" y1="{band + box_h / 2:.1f}" x2="{nxt[0] + 4:.1f}" y2="{band + box_h / 2:.1f}" {line} stroke-dasharray="6 3"/>'
        )
    if supplier:
        out.append(f'<path d="M48,80 L48,{band - 8} L{spans[0][0] + 12:.1f},{band - 8}" fill="none" {line}/>')
        out.append(_arrowhead(spans[0][0] + 12, band - 8, 0, 8, c["muted"]))
    if customer:
        out.append(
            f'<path d="M{spans[-1][1] - 12:.1f},{band - 8} L{WIDTH - 48},{band - 8} L{WIDTH - 48},81" fill="none" {line}/>'
        )
        out.append(_arrowhead(WIDTH - 48, 80, -90, 8, c["muted"]))
    data_bottom = band + box_h
    for (kind, name, data), (x1, x2) in zip(flow, spans):
        cx = (x1 + x2) / 2
        if kind == "process":
            w = x2 - x1 - 8
            out.append(f'<rect x="{x1 + 4:.1f}" y="{band}" width="{w:.1f}" height="{box_h}" fill="{c["primary"]}"/>')
            out.append(_box_text(cx, band + box_h / 2, name, w - 8, SIZE, 2, BOLD + f' fill="{c["on-primary"]}"'))
            if data:
                dh = 8 + 14 * len(data)
                out.append(
                    f'<rect x="{x1 + 4:.1f}" y="{band + box_h + 6}" width="{w:.1f}" height="{dh}" fill="{c["surface"]}" stroke="{c["border"]}"/>'
                )
                out += [label(x1 + 9, band + box_h + 20 + 14 * k, item, 9.5) for k, item in enumerate(data)]
                data_bottom = max(data_bottom, band + box_h + 6 + dh)
        else:  # an inventory triangle with an I in it
            ty = band + 4
            out.append(
                f'<path d="M{cx:.1f},{ty:.1f} L{cx + 18:.1f},{ty + 32:.1f} L{cx - 18:.1f},{ty + 32:.1f} Z" fill="{c["warning"]}" stroke="#1d1f27" stroke-width="1.2"/>'
            )
            out.append(label(cx, ty + 27, "I", 11, "middle", BOLD + ' fill="#1d1f27"'))
    # the timeline: waiting up, processing down, and the totals at its end
    high, low = data_bottom + 34, data_bottom + 62
    waits, works, path = [], [], []
    for (kind, name, data), (x1, x2) in zip(flow, spans):
        if kind == "inventory":
            waits.append(name)
            out.append(label((x1 + x2) / 2, high - 6, name, 9.5, "middle"))
        else:
            time = next((d[3:].strip() for d in data if d.upper().startswith("C/T")), "")
            if time:
                works.append(time)
                out.append(label((x1 + x2) / 2, low + 15, time, 9.5, "middle"))
        level = high if kind == "inventory" else low
        path += [(x1, level), (x2, level)]
    out.append(
        f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in path)}" fill="none" {_stroke(ctx, "strong", 1.8)}/>'
    )
    totals = f"Lead time {_total(waits)}  ·  Processing time {_total(works)}"
    out.append(label(WIDTH - 6, low + 38, totals, SIZE, "end", BOLD))
    return _fig(opts, svg(WIDTH, low + 48, "".join(out), opts.get("title", "value stream map"), "chart"))
