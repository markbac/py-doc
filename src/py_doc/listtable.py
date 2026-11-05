"""``[[LISTTABLE]]``: tables whose cells hold paragraphs, lists, merged cells and blocks such as diagrams.

A marker line, then one row per line::

    [[LISTTABLE: header, widths=5,95]]
    | Step | What happens |
    | 1 | First paragraph<br>Second paragraph<br>- a bullet<br>  - a bullet inside it<br>1. a numbered item |
    | 2 | [[BLOCK: wiring]] |
    | < | ^ |

``<br>`` starts a new paragraph in a cell. A paragraph that starts with ``- `` is a bullet and one that starts
with ``1. `` a numbered item; two spaces before the marker put the item inside the one above. A cell of only
``<`` is merged with the cell on its left, and one of only ``^`` with the cell above. ``header`` makes the first
row the header row. ``[[BLOCK: name]]`` as a paragraph of its own is replaced by the blocks between
``[[BLOCK: name]]`` and ``[[ENDBLOCK]]`` lines elsewhere in the same file: a diagram, a picture, code.

Each table becomes a pandoc grid table, which takes several blocks per cell, in a Div of class ``listtable``.
The blocks go in a Div of class ``listtable-block`` each, which ``listtable.lua`` moves into their cells.
Pandoc reads a grid table by character position, so every line is padded exactly.

:class:`Tables` is fed the lines of one file by :mod:`py_doc.directives`, after conditions and variables.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

MARKER = re.compile(r"^\[\[LISTTABLE(?::(?P<options>[^\]]*))?\]\]\s*$")
ROW = re.compile(r"^\|.*\|\s*$")
BLOCK = re.compile(r"^\[\[BLOCK:\s*(?P<name>[\w-]+)\s*\]\]\s*$")
ENDBLOCK = re.compile(r"^\[\[ENDBLOCK\]\]\s*$")
_OPTIONS = re.compile(
    r"\s*(?:(?P<before>header)\s*(?:,\s*|$))?(?:widths\s*=\s*(?P<widths>\d+(?:\s*,\s*\d+)*))?\s*(?:,\s*(?P<after>header))?\s*"
)
_CELL_SEPARATOR = re.compile(r"(?<!\\)\|")
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ITEM = re.compile(r"^(?P<marker>-|\d+\.)\s+(?P<text>.*)$")
_MARKER_LIKE = re.compile(r"^(?:[-+*]|\d+[.)])$")  # a word pandoc would read as a list item at the start of a line
TOTAL_WIDTH = 100  # wider than pandoc's 72 columns, so pandoc keeps the relative widths
MIN_WIDTH = 3


@dataclass(frozen=True)
class Options:
    header: bool
    widths: list[int]


def options(text: str | None) -> Options | None:
    """The options of a marker, or None when they are not ``header`` and ``widths=a,b,c``."""
    match = _OPTIONS.fullmatch(text or "")
    if not match or (match["before"] and match["after"]):
        return None
    widths = [int(w) for w in match["widths"].split(",")] if match["widths"] else []
    return Options(bool(match["before"] or match["after"]), widths)


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in _CELL_SEPARATOR.split(row.strip()[1:-1])]


def _scale(weights: list[int]) -> list[int]:
    """Column widths in characters, ``TOTAL_WIDTH`` in all, at least ``MIN_WIDTH`` each."""
    weights = weights if sum(weights) else [1] * len(weights)
    widths = [max(MIN_WIDTH, w * TOTAL_WIDTH // sum(weights)) for w in weights]
    widest = widths.index(max(widths))
    widths[widest] = max(MIN_WIDTH, widths[widest] + TOTAL_WIDTH - sum(widths))
    return widths


def _words(text: str) -> list[str]:
    """Split at spaces, but never inside a ``{...}`` attribute block or an inline code span."""
    words, current, depth, ticks = [], "", 0, 0
    for token in re.findall(r"`+|[^`]", text):
        if token[0] == "`":
            ticks = len(token) if not ticks else 0 if len(token) == ticks else ticks
        elif not ticks and token == "{":
            depth += 1
        elif not ticks and token == "}" and depth:
            depth -= 1
        if token == " " and not depth and not ticks:
            if current:
                words.append(current)
            current = ""
        else:
            current += token
    return [*words, current] if current else words


def _wrap(text: str, width: int) -> list[str]:
    """Lines of at most ``width``. A line never starts with a word pandoc would take for a list marker."""
    lines: list[str] = []
    for word in _words(text):
        if lines and len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(re.sub(r"^(\d*)(.)$", r"\1\\\2", word) if _MARKER_LIKE.match(word) else word)
    return lines or [""]


@dataclass
class _Cell:
    text: str
    row: int
    column: int
    rows: int = 1
    columns: int = 1
    lines: list[str] = field(default_factory=list)


class Table:
    """One ``[[LISTTABLE]]``: its marker, its rows as they are added, then its grid table."""

    def __init__(self, marker: str, line: int, settings: Options, scope: str) -> None:
        self.marker, self.line, self.settings, self.scope = marker, line, settings, scope
        self.rows: list[tuple[int, str]] = []
        self.problems: list[tuple[int, str]] = []
        self.slots: dict[str, int] = {}  # block name: the line of the first row that uses it

    def add(self, number: int, row: str) -> None:
        self.rows.append((number, row))

    def _cell_lines(self, text: str, width: int, number: int) -> list[str]:
        """The lines of one cell: paragraphs apart by a blank line, a list after one, items together."""
        lines: list[str] = []
        indents: list[int] = []  # the content column of each open list level
        top_marker = None
        for piece in _BREAK.split(text):
            paragraph = piece.strip()
            if not paragraph:
                continue
            item = _ITEM.match(paragraph)
            if item:
                kind = "-" if item["marker"] == "-" else "1."
                level = min((len(piece) - len(piece.lstrip(" "))) // 2, len(indents))
                if not indents or (level == 0 and kind != top_marker):
                    if lines:
                        lines.append("")
                    indents, level, top_marker = [], 0, kind
                del indents[level:]
                lead = " " * sum(indents)
                marker = item["marker"] + " "
                wrapped = _wrap(item["text"], width - len(lead) - len(marker))
                lines += [lead + marker + wrapped[0]] + [lead + " " * len(marker) + w for w in wrapped[1:]]
                indents.append(len(marker))
                continue
            if lines:
                lines.append("")
            indents = []
            slot = BLOCK.match(paragraph)
            if slot:
                self.slots.setdefault(slot["name"], number)
                paragraph = f"§{list(self.slots).index(slot['name']) + 1}"
            lines += _wrap(paragraph, width)
        return lines

    def _layout(self, columns: int) -> list[_Cell]:
        """The cells that are not merged into another, with their spans. Merges that are not a rectangle are undone."""
        grid: list[list[_Cell | None]] = []
        owner: dict[tuple[int, int], _Cell] = {}
        for r, (number, row) in enumerate(self.rows):
            texts = _cells(row)
            if len(texts) != columns:
                self.problems.append(
                    (
                        number,
                        f"[[LISTTABLE]] row has {len(texts)} cell(s), not {columns}, so it is "
                        f"{'padded' if len(texts) < columns else 'cut'} to {columns}",
                    )
                )
                texts = (texts + [""] * columns)[:columns]
            grid.append([])
            for c, text in enumerate(texts):
                merge = text if text in ("<", "^") else None
                if merge == "<" and c == 0:
                    self.problems.append((number, "'<' in the first column has no cell on its left, so it is empty"))
                    merge, text = None, ""
                if merge == "^" and (r == 0 or (r == 1 and self.settings.header)):
                    where = "the first row has no cell above" if r == 0 else "a body cell cannot join the header row"
                    self.problems.append((number, f"'^' cannot be merged: {where}, so it is empty"))
                    merge, text = None, ""
                if merge:
                    owner[(r, c)] = owner[(r, c - 1) if merge == "<" else (r - 1, c)]
                    grid[r].append(None)
                else:
                    owner[(r, c)] = _Cell(text, r, c)
                    grid[r].append(owner[(r, c)])
        regions: dict[int, list[tuple[int, int]]] = {}  # the spots of each cell, by its id
        for spot, cell in owner.items():
            regions.setdefault(id(cell), []).append(spot)
        for anchor in [cell for row in grid for cell in row if cell]:
            spots = regions[id(anchor)]
            rows = {r for r, _ in spots}
            cols = {c for _, c in spots}
            box = {(r, c) for r in range(min(rows), max(rows) + 1) for c in range(min(cols), max(cols) + 1)}
            if set(spots) != box:
                self.problems.append(
                    (self.rows[anchor.row][0], "these merged cells are not a rectangle, so they are not merged")
                )
                for spot in spots:
                    if spot != (anchor.row, anchor.column):
                        owner[spot] = _Cell("", *spot)
                        grid[spot[0]][spot[1]] = owner[spot]
                continue
            anchor.rows, anchor.columns = len(rows), len(cols)
        return [cell for row in grid for cell in row if cell]

    def grid(self) -> list[str]:
        """The grid table, with every line the same width. Records problems on the way."""
        weights = self.settings.widths or [1] * len(_cells(self.rows[0][1]))
        widths = _scale(weights)
        columns, count = len(widths), len(self.rows)
        cells = self._layout(columns)
        xs = [sum(widths[:c]) + c for c in range(columns + 1)]  # the | of each column boundary
        for cell in cells:
            width = xs[cell.column + cell.columns] - xs[cell.column] - 3
            number = self.rows[cell.row][0]
            cell.lines = self._cell_lines(cell.text, width, number)
            if any(len(line) > width for line in cell.lines):
                self.problems.append(
                    (
                        number,
                        f"a word in a [[LISTTABLE]] cell is wider than its column of {width} characters, so the "
                        "table cannot be read. Widen the column or shorten the word",
                    )
                )
        heights = [1] * count
        for cell in sorted(cells, key=lambda cell: cell.rows):
            room = sum(heights[cell.row : cell.row + cell.rows]) + cell.rows - 1
            heights[cell.row + cell.rows - 1] += max(0, len(cell.lines) - room)
        ys = [sum(heights[:r]) + r for r in range(count + 1)]
        canvas = [[" "] * (xs[-1] + 1) for _ in range(ys[-1] + 1)]

        def put(y: int, x: int, char: str) -> None:
            if canvas[y][x] == " " or char == "+":
                canvas[y][x] = char

        for cell in cells:
            top, bottom = ys[cell.row], ys[cell.row + cell.rows]
            left, right = xs[cell.column], xs[cell.column + cell.columns]
            for y in (top, bottom):
                rule = "=" if self.settings.header and y == ys[1] and count > 1 else "-"
                for x in range(left + 1, right):
                    put(y, x, rule)
            for x in (left, right):
                for y in range(top + 1, bottom):
                    put(y, x, "|")
            for y in (top, bottom):
                for x in (left, right):
                    put(y, x, "+")
            for i, line in enumerate(cell.lines):
                canvas[top + 1 + i][left + 2 : left + 2 + len(line)] = list(line)
        return ["".join(row) for row in canvas]

    def finish(self) -> list[str]:
        """The lines that replace the marker and the rows."""
        if not self.rows:
            self.problems.append((self.line, "[[LISTTABLE]] is left as written: no '| ... |' rows follow it"))
            return [self.marker]
        lines = self.grid()
        keys = " ".join(f"{self.scope}-{name}" for name in self.slots)
        div = f'::: {{.listtable blocks="{keys}"}}' if keys else "::: {.listtable}"
        return ["", div, *lines, ":::", ""]


class Tables:
    """The ``[[LISTTABLE]]`` tables and ``[[BLOCK:]]`` definitions of one file, fed to it line by line.

    ``problems`` are warnings: the table is still made. ``errors`` (a block never closed, an
    ``[[ENDBLOCK]]`` with no block) stop a build.
    """

    def __init__(self, file: str) -> None:
        self.scope = hashlib.sha1(file.encode("utf-8")).hexdigest()[:8]
        self.table: Table | None = None
        self.problems: list[tuple[int, str]] = []
        self.errors: list[tuple[int, str]] = []
        self.count = 0
        self._open: tuple[int, str] | None = None
        self._defined: dict[str, int] = {}
        self._used: dict[str, int] = {}

    def flush(self) -> list[str]:
        """End the table being read, if there is one, and return its lines."""
        if self.table is None:
            return []
        table, self.table = self.table, None
        lines = table.finish()
        self.problems += table.problems
        if table.rows:
            self.count += 1
            for name, number in table.slots.items():
                self._used.setdefault(name, number)
        return lines

    def directive(self, number: int, line: str) -> list[str] | None:
        """The lines that replace ``line`` when it is a marker or a block line, else None."""
        if match := MARKER.match(line):
            settings = options(match["options"])
            if settings is None:
                self.problems.append(
                    (number, "[[LISTTABLE]] is left as written: its options are not 'header' and 'widths=a,b,c'")
                )
                return [line]
            self.table = Table(line, number, settings, self.scope)
            return []
        if match := BLOCK.match(line):
            if self._open:
                self.errors.append((number, f"[[BLOCK: {match['name']}]] is inside [[BLOCK: {self._open[1]}]]"))
                return []
            if match["name"] in self._defined:
                self.errors.append((number, f"[[BLOCK: {match['name']}]] is defined twice in this file"))
            self._open = (number, match["name"])
            self._defined.setdefault(match["name"], number)
            return ["", f'::: {{.listtable-block key="{self.scope}-{match["name"]}"}}', ""]
        if ENDBLOCK.match(line):
            if not self._open:
                self.errors.append((number, "[[ENDBLOCK]] has no [[BLOCK:]] before it"))
                return []
            self._open = None
            return ["", ":::", ""]
        return None

    def close(self) -> list[str]:
        """At the end of the file: the last table's lines, and the checks of the blocks."""
        lines = self.flush()
        if self._open:
            self.errors.append((self._open[0], f"[[BLOCK: {self._open[1]}]] is never closed with [[ENDBLOCK]]"))
        for name, number in self._used.items():
            if name not in self._defined:
                self.problems.append(
                    (number, f"[[BLOCK: {name}]] is used in a table, but this file does not define it")
                )
        for name, number in self._defined.items():
            if name not in self._used:
                self.problems.append((number, f"[[BLOCK: {name}]] is defined, but no table in this file uses it"))
        return lines
