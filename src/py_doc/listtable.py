"""``[[LISTTABLE]]``: tables whose cells hold several paragraphs and bullet lists.

A marker line, then one row per line::

    [[LISTTABLE: widths=5,95]]
    | 1 | First paragraph<br>Second paragraph<br>- a bullet<br>- another |

Every row is body content: there is no header row. ``<br>`` starts a new paragraph in a cell, and a
paragraph that starts with ``- `` is a bullet. ``\\|`` is a literal pipe. Each table becomes a pandoc grid
table, which takes several blocks per cell, so the cells reach Word (and every other format) as real
paragraphs and lists. Pandoc reads a grid table by character position, so every line is padded exactly.
"""

from __future__ import annotations

import logging
import re

from .directives import Fence

logger = logging.getLogger(__name__)

_MARKER = re.compile(r"^\[\[LISTTABLE(?::(?P<options>[^\]]*))?\]\]\s*$")
_WIDTHS = re.compile(r"^\s*widths\s*=\s*(?P<widths>\d+(?:\s*,\s*\d+)*)\s*$")
_ROW = re.compile(r"^\|.*\|\s*$")
_CELL_SEPARATOR = re.compile(r"(?<!\\)\|")
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
TOTAL_WIDTH = 100  # wider than pandoc's 72 columns, so pandoc keeps the relative widths
MIN_WIDTH = 3


def convert(text: str, name: str) -> str:
    """Replace every ``[[LISTTABLE]]`` of ``text`` outside code with a grid table. ``name`` is used in messages."""
    lines = text.splitlines()
    out: list[str] = []
    fence, converted, index = Fence(), 0, 0
    while index < len(lines):
        line = lines[index]
        index += 1
        match = None if fence.inside(line) else _MARKER.match(line)
        if not match:
            out.append(line)
            continue
        widths = _widths(match["options"])
        rows = []
        while index < len(lines) and _ROW.match(lines[index]):
            rows.append((index + 1, lines[index]))
            index += 1
        if widths is None or not rows:
            problem = "its options are not 'widths=a,b,c'" if widths is None else "no '| ... |' rows follow it"
            logger.warning(f"{name}:{index - len(rows)}: [[LISTTABLE]] is left as written: {problem}")
            out.append(line)
            out += [row for _, row in rows]
            continue
        out += ["", *_grid(rows, widths, name), ""]
        converted += 1
    if converted:
        logger.info(f"{name}: {converted} [[LISTTABLE]] table(s) converted")
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _widths(options: str | None) -> list[int] | None:
    """The relative widths of the options: [] for none given, None when the options are not understood."""
    if options is None or not options.strip():
        return []
    match = _WIDTHS.match(options)
    return [int(w) for w in match["widths"].split(",")] if match else None


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in _CELL_SEPARATOR.split(row.strip()[1:-1])]


def _scale(weights: list[int]) -> list[int]:
    """Column widths in characters, ``TOTAL_WIDTH`` in all, at least ``MIN_WIDTH`` each."""
    total = sum(weights) or len(weights)
    weights = weights if sum(weights) else [1] * len(weights)
    widths = [max(MIN_WIDTH, w * TOTAL_WIDTH // total) for w in weights]
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
    lines: list[str] = []
    for word in _words(text):
        if lines and len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def _cell_lines(cell: str, width: int) -> list[str]:
    """The lines of one cell: paragraphs apart by a blank line, a list after one, bullets together."""
    lines: list[str] = []
    previous_bullet = False
    for paragraph in (p.strip() for p in _BREAK.split(cell)):
        if not paragraph:
            continue
        bullet = paragraph.startswith("- ")
        if lines and not (bullet and previous_bullet):
            lines.append("")
        if bullet:
            wrapped = _wrap(paragraph[2:].strip(), width - 2)
            lines += [("- " if i == 0 else "  ") + text for i, text in enumerate(wrapped)]
        else:
            lines += _wrap(paragraph, width)
        previous_bullet = bullet
    return lines


def _grid(rows: list[tuple[int, str]], weights: list[int], name: str) -> list[str]:
    columns = len(weights) or len(_cells(rows[0][1]))
    widths = _scale(weights or [1] * columns)
    border = "+" + "+".join("-" * w for w in widths) + "+"
    out = [border]
    for number, row in rows:
        cells = _cells(row)
        if len(cells) != columns:
            logger.warning(
                f"{name}:{number}: [[LISTTABLE]] row has {len(cells)} cell(s), not {columns}, so it is "
                f"{'padded' if len(cells) < columns else 'cut'} to {columns}"
            )
            cells = (cells + [""] * columns)[:columns]
        blocks = [_cell_lines(cell, width - 2) for cell, width in zip(cells, widths)]
        for block, width in zip(blocks, widths):
            if any(len(line) > width - 2 for line in block):
                logger.warning(
                    f"{name}:{number}: a word in a [[LISTTABLE]] cell is wider than its column of {width - 2} "
                    "characters, so the table cannot be read. Widen the column or shorten the word"
                )
        for i in range(max(1, *(len(block) for block in blocks))):
            texts = [block[i] if i < len(block) else "" for block in blocks]
            out.append("|" + "|".join(f" {t.ljust(w - 2)} " for t, w in zip(texts, widths)) + "|")
        out.append(border)
    return out
