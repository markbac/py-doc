"""Shared drawing pieces for the native poster blocks: scales, ticks, polar paths, text and a tree layout.

A block is its parser and its picture. The picture is drawn from these pieces, in the theme's colours, so every
block has the same axes, labels and arcs. Nothing here knows about a poster: a block drawn only with these can
be written on its own as an SVG file (``standalone``), for ``py-doc diagram`` and for documents.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass, field

# The average width of a character as a share of the font size. The poster's fonts are not measured here (the
# page measures them when it fits the layout), so wrapping and label spacing allow for an average letter.
CHAR = 0.55
CHAR_BOLD = 0.6


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def number(value: float) -> str:
    """A value as an axis or label shows it: thousands separated, no trailing zeros."""
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:g}"


def nice(value: float) -> float:
    """The round number (1, 2, 2.5 or 5 times a power of ten) at or above ``value``, for an axis."""
    if value <= 0:
        return 0.0
    power = 10 ** math.floor(math.log10(value))
    return next(m * power for m in (1, 2, 2.5, 5, 10) if value <= m * power + 1e-9)


def extent(values, low: float | None = None, high: float | None = None) -> tuple[float, float]:
    """The axis for ``values``: from zero, or a round number below a negative value, to a round number above.

    ``low`` and ``high`` are used as given when they are not None.
    """
    values = list(values)
    if low is None:
        low = -nice(-min(values)) if min(values) < 0 else 0.0
    if high is None:
        high = nice(max(values)) or 1.0
    return low, high


# ---------------------------------------------------------------------------
# Scales: a value to a position
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Linear:
    """``low..high`` drawn from ``start`` to ``end``. ``start`` may be above ``end``, as a value axis that grows up."""

    low: float
    high: float
    start: float
    end: float

    def __call__(self, value: float) -> float:
        return self.start + (value - self.low) / (self.high - self.low) * (self.end - self.start)

    def ticks(self, step: float) -> list[float]:
        """Every ``step`` from ``low`` to ``high``, both included."""
        return [self.low + step * n for n in range(round((self.high - self.low) / step) + 1)]


@dataclass(frozen=True)
class Log10:
    """``low..high`` (both above zero) on a log scale, each power of ten the same distance apart."""

    low: float
    high: float
    start: float
    end: float

    def __post_init__(self):
        if self.low <= 0 or self.high <= self.low:
            raise ValueError("a log scale needs 0 < low < high")

    def __call__(self, value: float) -> float:
        lo, hi = math.log10(self.low), math.log10(self.high)
        return self.start + (math.log10(value) - lo) / (hi - lo) * (self.end - self.start)

    def ticks(self) -> list[float]:
        """The powers of ten from ``low`` to ``high``."""
        first, last = math.ceil(math.log10(self.low) - 1e-9), math.floor(math.log10(self.high) + 1e-9)
        return [10.0**k for k in range(first, last + 1)]


@dataclass(frozen=True)
class Band:
    """``count`` equal bands from ``start`` to ``end``, each with a mark ``inner`` of its width, centred."""

    count: int
    start: float
    end: float
    inner: float = 0.7

    @property
    def width(self) -> float:
        return (self.end - self.start) / self.count

    def at(self, index: int) -> float:
        """Where band ``index`` starts."""
        return self.start + index * self.width

    def centre(self, index: int) -> float:
        return self.at(index) + self.width / 2

    def mark(self, index: int) -> float:
        """Where the mark of band ``index`` starts."""
        return self.at(index) + self.width * (1 - self.inner) / 2


# ---------------------------------------------------------------------------
# Polar paths: 0 degrees is up, and angles go clockwise, as on a dial
# ---------------------------------------------------------------------------


def polar(cx: float, cy: float, r: float, degrees: float) -> tuple[float, float]:
    a = math.radians(degrees)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def arc(cx: float, cy: float, r: float, start: float, end: float) -> str:
    """The path of an arc from ``start`` to ``end`` degrees (clockwise)."""
    x0, y0 = polar(cx, cy, r, start)
    x1, y1 = polar(cx, cy, r, end)
    large = 1 if (end - start) % 360 > 180 else 0
    return f"M{x0:.2f},{y0:.2f} A{r:.2f},{r:.2f} 0 {large} 1 {x1:.2f},{y1:.2f}"


def sector(cx: float, cy: float, inner: float, outer: float, start: float, end: float) -> str:
    """The path of a ring sector from ``start`` to ``end`` degrees; ``inner`` 0 makes a pie slice.

    A whole ring (360 degrees or more) is two circles; fill it with ``fill-rule="evenodd"`` to keep its hole.
    """
    if end - start >= 360:  # two half arcs each, as one arc cannot end where it starts

        def circle(r):
            x0, y0 = polar(cx, cy, r, start)
            x1, y1 = polar(cx, cy, r, start + 180)
            return f"M{x0:.2f},{y0:.2f} A{r:.2f},{r:.2f} 0 1 1 {x1:.2f},{y1:.2f} A{r:.2f},{r:.2f} 0 1 1 {x0:.2f},{y0:.2f} Z"

        return circle(outer) + (" " + circle(inner) if inner > 0 else "")
    x0, y0 = polar(cx, cy, outer, start)
    x1, y1 = polar(cx, cy, outer, end)
    large = 1 if end - start > 180 else 0
    path = f"M{x0:.2f},{y0:.2f} A{outer:.2f},{outer:.2f} 0 {large} 1 {x1:.2f},{y1:.2f}"
    if inner > 0:
        x2, y2 = polar(cx, cy, inner, end)
        x3, y3 = polar(cx, cy, inner, start)
        path += f" L{x2:.2f},{y2:.2f} A{inner:.2f},{inner:.2f} 0 {large} 0 {x3:.2f},{y3:.2f}"
    else:
        path += f" L{cx:.2f},{cy:.2f}"
    return path + " Z"


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------


def text_width(text: str, size: float, bold: bool = False) -> float:
    """The width ``text`` takes at ``size`` pixels, for an average letter of the theme's fonts."""
    return len(text) * size * (CHAR_BOLD if bold else CHAR)


def wrap(text: str, width: float, size: float, bold: bool = False) -> list[str]:
    """``text`` in lines that fit ``width`` pixels, broken between words. A word longer than a line is kept whole."""
    lines: list[str] = []
    for word in text.split():
        if lines and text_width(lines[-1] + " " + word, size, bold) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines or [""]


def spread(positions: list[float], gap: float, low: float = -math.inf, high: float = math.inf) -> list[float]:
    """Move label positions apart so neighbours are at least ``gap`` apart, keeping their order and staying
    within ``low..high`` where there is room. Each moves as little as it can; used for leader-line callouts."""
    if not positions:
        return []
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    placed = [positions[i] for i in order]
    # Push down, then pull back up from the end so the labels stay inside, then down again from the start
    for i in range(1, len(placed)):
        placed[i] = max(placed[i], placed[i - 1] + gap)
    if placed[-1] > high:
        placed[-1] = high
        for i in range(len(placed) - 2, -1, -1):
            placed[i] = min(placed[i], placed[i + 1] - gap)
    if placed[0] < low:
        placed[0] = low
        for i in range(1, len(placed)):
            placed[i] = max(placed[i], placed[i - 1] + gap)
    out = [0.0] * len(positions)
    for rank, i in enumerate(order):
        out[i] = placed[rank]
    return out


def label(x: float, y: float, content, size: float = 13, anchor: str = "start", extra: str = "") -> str:
    """A ``<text>`` element in the current colour. ``extra`` is more attributes, such as a weight or a fill."""
    more = f" {extra}" if extra else ""
    anchored = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}"{anchored} font-size="{size:g}" fill="currentColor"{more}>{esc(content)}</text>'
    )


def svg(width: float, height: float, body: str, title: str, cls: str = "") -> str:
    """An inline ``<svg>`` of ``width`` by ``height``, scaled to its box, with ``title`` for screen readers."""
    klass = f' class="{cls}"' if cls else ""
    return f'<svg{klass} viewBox="0 0 {width:g} {height:g}" role="img" aria-label="{esc(title)}">{body}</svg>'


def standalone(picture: str, theme, background: str | None = None) -> str:
    """An inline SVG made a file of its own: the namespace added, and the theme's text colour and body font
    given to the text drawn in ``currentColor``. ``background`` is a CSS colour, or None for transparent."""
    wanted = {"xmlns": "http://www.w3.org/2000/svg", "color": theme.colours["text"], "font-family": theme.fonts["body"]}
    opening = picture[: picture.index(">")]  # a picture may already have some, as a barcode has its namespace
    attrs = "".join(f' {name}="{esc(value)}"' for name, value in wanted.items() if f" {name}=" not in opening)
    picture = picture.replace("<svg", "<svg" + attrs, 1)
    if background:
        opened = picture.index(">") + 1
        picture = picture[:opened] + f'<rect width="100%" height="100%" fill="{esc(background)}"/>' + picture[opened:]
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + picture


# ---------------------------------------------------------------------------
# A tidy tree: parents centred over their children, subtrees as close as they can be
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """A tree to lay out. ``tidy`` sets ``x`` (across, in units of ``gap``) and ``depth`` (0 at the root)."""

    label: str
    children: list[Node] = field(default_factory=list)
    data: object = None
    x: float = 0.0
    depth: int = 0

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def tidy(root: Node, gap: float = 1.0) -> tuple[float, int]:
    """Lay out ``root`` top-down: siblings in order, at least ``gap`` apart at every depth, each parent centred
    over its children (a Reingold-Tilford layout with contours). Returns the width and the deepest depth; the
    leftmost node is at x = 0."""

    def place(node: Node, depth: int) -> dict[int, tuple[float, float]]:
        # Lays out the subtree with node at x = 0 and returns its contour: the leftmost and rightmost x per depth
        node.depth, node.x = depth, 0.0
        if not node.children:
            return {depth: (0.0, 0.0)}
        contour: dict[int, tuple[float, float]] = {}
        offsets = []
        for child in node.children:
            sub = place(child, depth + 1)
            shift = 0.0
            if contour:
                shift = max(contour[d][1] - sub[d][0] + gap for d in sub if d in contour)
            offsets.append(shift)
            for d, (lo, hi) in sub.items():
                lo, hi = lo + shift, hi + shift
                contour[d] = (min(contour[d][0], lo), max(contour[d][1], hi)) if d in contour else (lo, hi)
        middle = (offsets[0] + offsets[-1]) / 2
        for child, shift in zip(node.children, offsets):
            move(child, shift - middle)
        contour = {d: (lo - middle, hi - middle) for d, (lo, hi) in contour.items()}
        contour[depth] = (0.0, 0.0)
        return contour

    def move(node: Node, by: float):
        for n in node.walk():
            n.x += by

    contour = place(root, 0)
    left = min(lo for lo, _ in contour.values())
    move(root, -left)
    return max(hi for _, hi in contour.values()) - left, max(contour)
