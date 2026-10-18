"""Counts of what a Markdown file holds: words of prose, headings, code blocks, tables, pictures and links."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from py_doc.lint.text import segments
from py_doc.markdown import nodes as n
from py_doc.markdown import parse

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")


@dataclass
class FileStats:
    words: int = 0  # prose only: code, HTML, link targets and front matter are not counted
    headings: int = 0
    code_blocks: int = 0
    tables: int = 0
    images: int = 0
    links: int = 0
    lint_issues: int | None = None  # set when the files were linted

    def __add__(self, other: FileStats) -> FileStats:
        total = FileStats()
        for item in fields(FileStats):
            a, b = getattr(self, item.name), getattr(other, item.name)
            setattr(total, item.name, None if a is None and b is None else (a or 0) + (b or 0))
        return total

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


def text_stats(text: str) -> FileStats:
    document = parse(text)
    stats = FileStats(words=sum(len(_WORD.findall(segment.text)) for segment in segments(document)))
    for node in n.walk(document):
        if isinstance(node, n.Heading):
            stats.headings += 1
        elif isinstance(node, n.CodeBlock):
            stats.code_blocks += 1
        elif isinstance(node, n.Table):
            stats.tables += 1
        elif isinstance(node, n.Image):
            stats.images += 1
        elif isinstance(node, n.Link):
            stats.links += 1
    return stats


def file_stats(path: Path) -> FileStats:
    return text_stats(Path(path).read_text(encoding="utf-8-sig"))
