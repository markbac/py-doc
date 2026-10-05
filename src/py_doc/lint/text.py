"""Turn a parsed document into the prose that style rules should look at.

Code, inline code, HTML, link destinations and front matter never reach the rules. URLs, e-mail
addresses and file names written as plain text are masked with spaces, so offsets stay valid.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass

from py_doc.markdown import nodes as n

_URL = re.compile(r"(?:[A-Za-z][A-Za-z0-9+.-]*://|www\.)\S+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Dotted or slashed names such as config.json, http.client and docs/api: identifiers, not prose.
_GAP = "\ufffc"  # stands in for inline code and inline HTML, which are not prose
_NAME = re.compile(r"(?<![\w])[\w-]+(?:[./\\][\w-]+)+")


@dataclass
class Segment:
    """One run of prose (a heading, paragraph or table cell) with the source line of each part."""

    text: str
    starts: list[int]  # offsets where a new source line begins, ascending
    lines: list[int]  # the source line from each of those offsets

    def line_at(self, offset: int) -> int:
        return self.lines[max(bisect_right(self.starts, offset) - 1, 0)]


class _Builder:
    def __init__(self, first_line: int) -> None:
        self.parts: list[str] = []
        self.length = 0
        self.starts = [0]
        self.lines = [first_line]

    def add(self, text: str, line: int) -> None:
        if line != self.lines[-1]:
            if self.starts[-1] == self.length:
                self.lines[-1] = line
            else:
                self.starts.append(self.length)
                self.lines.append(line)
        self.parts.append(text)
        self.length += len(text)

    def inlines(self, nodes: list[n.Inline]) -> None:
        for node in nodes:
            if isinstance(node, n.Text):
                self.add(node.text, node.line)
            elif isinstance(node, (n.SoftBreak, n.HardBreak)):
                self.add(" ", node.line)
            elif isinstance(node, (n.CodeSpan, n.HtmlInline)):
                self.add(_GAP, node.line)  # not whitespace, so a phrase cannot run across it
            elif isinstance(node, (n.Emphasis, n.Strong, n.Link)):
                self.inlines(node.children)
            elif isinstance(node, n.Image):
                self.add(node.alt, node.line)

    def segment(self) -> Segment:
        return Segment(_mask("".join(self.parts)), self.starts, self.lines)


def _mask(text: str) -> str:
    for pattern in (_URL, _EMAIL, _NAME):
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return text


def segments(document: n.Document) -> list[Segment]:
    """The prose of ``document`` in source order."""
    found: list[Segment] = []
    for node in n.walk(document):
        if isinstance(node, (n.Heading, n.Paragraph, n.TableCell)):
            builder = _Builder(node.line)
            builder.inlines(node.children)
            segment = builder.segment()
            if segment.text.strip():
                found.append(segment)
    return found
