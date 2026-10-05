"""The canonical Markdown document model.

Every renderer and the linter work from these nodes, so no tool parses Markdown on its own.

Positions are 1-based source lines. Block nodes have ``line`` and ``end_line`` (inclusive). Inline
nodes have the ``line`` where they start. Columns are not recorded.

Two limits on inline lines: a code span or inline HTML that itself spans several lines can make
later nodes in the same paragraph report a line that is too small, because the parser does not
expose where inline tokens end.

Link reference definitions (``[id]: url``) are resolved into the links that use them and do not
appear as nodes.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Union

# --- Inline nodes -------------------------------------------------------------------------------


@dataclass
class Text:
    line: int
    text: str


@dataclass
class CodeSpan:
    line: int
    text: str


@dataclass
class Emphasis:
    line: int
    children: list[Inline]


@dataclass
class Strong:
    line: int
    children: list[Inline]


@dataclass
class Link:
    line: int
    url: str
    title: str | None
    children: list[Inline]


@dataclass
class Image:
    line: int
    url: str
    title: str | None
    alt: str  # plain text, formatting removed


@dataclass
class SoftBreak:
    line: int


@dataclass
class HardBreak:
    line: int


@dataclass
class HtmlInline:
    line: int
    text: str


Inline = Union[Text, CodeSpan, Emphasis, Strong, Link, Image, SoftBreak, HardBreak, HtmlInline]


# --- Block nodes --------------------------------------------------------------------------------


@dataclass
class Heading:
    line: int
    end_line: int
    level: int  # 1 to 6
    children: list[Inline]


@dataclass
class Paragraph:
    line: int
    end_line: int
    children: list[Inline]


@dataclass
class CodeBlock:
    line: int
    end_line: int
    text: str  # without the final newline
    language: str | None  # first word of the info string, fenced blocks only
    info: str  # the whole info string
    fenced: bool  # False for an indented code block
    closed: bool  # False for a fence that runs to the end of its container without a closing fence


@dataclass
class BlockQuote:
    line: int
    end_line: int
    children: list[Block]


@dataclass
class ListItem:
    line: int
    end_line: int
    children: list[Block]


@dataclass
class List:
    line: int
    end_line: int
    ordered: bool
    start: int | None  # first number of an ordered list, None for a bullet list
    tight: bool  # no blank lines between items or their paragraphs
    children: list[ListItem]


@dataclass
class ThematicBreak:
    line: int
    end_line: int


@dataclass
class HtmlBlock:
    line: int
    end_line: int
    text: str  # without the final newline


@dataclass
class TableCell:
    line: int
    align: str | None  # "left", "right", "center" or None
    children: list[Inline]


@dataclass
class TableRow:
    line: int
    end_line: int
    header: bool
    children: list[TableCell]


@dataclass
class Table:
    line: int
    end_line: int
    children: list[TableRow]


Block = Union[Heading, Paragraph, CodeBlock, BlockQuote, List, ThematicBreak, HtmlBlock, Table]


# --- Document -----------------------------------------------------------------------------------


@dataclass
class FrontMatter:
    """The raw text between the leading ``---`` lines. Reading it as YAML is left to the caller."""

    line: int
    end_line: int
    text: str


@dataclass
class Document:
    front_matter: FrontMatter | None
    children: list[Block]


Node = Union[Document, FrontMatter, Block, ListItem, TableRow, TableCell, Inline]


def walk(node: Node) -> Iterator[Node]:
    """Yield ``node`` and every node below it, parents before children, in source order."""
    yield node
    if isinstance(node, Document) and node.front_matter is not None:
        yield node.front_matter
    for child in getattr(node, "children", ()):
        yield from walk(child)


def plain_text(nodes: list[Inline]) -> str:
    """The readable text of inline nodes: formatting is dropped, breaks become spaces."""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, (Text, CodeSpan)):
            parts.append(node.text)
        elif isinstance(node, (Emphasis, Strong, Link)):
            parts.append(plain_text(node.children))
        elif isinstance(node, Image):
            parts.append(node.alt)
        elif isinstance(node, (SoftBreak, HardBreak)):
            parts.append(" ")
    return "".join(parts)
