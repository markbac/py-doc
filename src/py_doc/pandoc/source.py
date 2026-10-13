"""Join the sources of a document into one Markdown text for pandoc.

Headings are found line by line outside fenced code, so a ``#`` comment in a code block is never
mistaken for a heading (the shared tree is not used here: pandoc has its own, richer, Markdown).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from py_doc import directives
from py_doc.directives import Fence
from py_doc.errors import ConversionError
from py_doc.markdown import FrontMatterError, Metadata, ParseError, parse, read_metadata

logger = logging.getLogger(__name__)

PAGE_BREAK = "::: {.pagebreak}\n:::\n"
_HEADING = re.compile(r"^(?P<indent> {0,3})(?P<hashes>#{1,6})(?P<rest>[ \t].*|)$")
_FRONT_END = re.compile(r"^(---|\.\.\.)\s*$")


@dataclass
class Joined:
    parts: list[tuple[Path, str]]  # each source file with its text, ready to be joined
    metadata: Metadata
    first_heading: str | None

    @property
    def markdown(self) -> str:
        return "\n".join(text for _, text in self.parts)


def split_front_matter(text: str) -> tuple[str | None, str]:
    """The YAML between leading ``---`` lines (or None) and the Markdown after it."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if _FRONT_END.match(lines[index]):
            rest = "\n".join(lines[index + 1 :]).lstrip("\n")
            return "\n".join(lines[1:index]), rest + "\n" if rest else ""
    return None, text


def read_front_matter(front: str | None, file: Path) -> Metadata:
    if front is None:
        return Metadata()
    try:
        return read_metadata(parse(f"---\n{front}\n---\n"))
    except (FrontMatterError, ParseError) as exc:
        raise ConversionError(f"Cannot convert '{file}': {exc}") from exc


def shift_headings(text: str, offset: int, name: str) -> str:
    """Move every ATX heading outside code by ``offset`` levels, keeping the result within 1 to 6."""
    if not offset:
        return text
    fence, out = Fence(), []
    for number, line in enumerate(text.splitlines(), start=1):
        match = None if fence.inside(line) else _HEADING.match(line)
        if match:
            level = len(match["hashes"]) + offset
            if not 1 <= level <= 6:
                logger.warning(f"Heading at line {number} of '{name}' would be level {level}, so it is kept in 1 to 6")
            line = f"{match['indent']}{'#' * min(6, max(1, level))}{match['rest']}"
        out.append(line)
    return "\n".join(out) + "\n"


_TOO_DEEP = re.compile(r"^(?P<indent> {0,3})(?P<hashes>#{7,})(?=[ \t]|$)")


def keep_deep_hashes_as_text(text: str) -> str:
    """A line of seven or more ``#`` outside code is text, as in CommonMark. Pandoc would make it a heading below 6."""
    fence, out = Fence(), []
    for line in text.splitlines():
        if not fence.inside(line):
            line = _TOO_DEEP.sub(lambda m: f"{m['indent']}\\{m['hashes']}", line)
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def warn_unclosed_fence(text: str, name: str) -> None:
    """A code fence that is never closed is not code to pandoc: it shows the fence and the code as text. Say so."""
    fence, opened = Fence(), None
    for number, line in enumerate(text.splitlines(), start=1):
        was_inside = fence.marker is not None
        fence.inside(line)
        if fence.marker is not None and not was_inside:
            opened = number
    if fence.marker is not None:
        logger.warning(
            f"{name}:{opened}: the code fence {fence.marker} opened here is never closed, so its lines are shown as "
            "text, not code. Add the closing fence"
        )


def retitle(text: str, title: str) -> str:
    """Replace the text of the first heading with ``title``, or put a level 1 heading first if there is none."""
    fence, lines = Fence(), text.splitlines()
    for index, line in enumerate(lines):
        match = None if fence.inside(line) else _HEADING.match(line)
        if match:
            lines[index] = f"{match['indent']}{match['hashes']} {title}"
            return "\n".join(lines) + "\n"
    return f"# {title}\n\n{text}"


def first_heading(text: str) -> str | None:
    fence = Fence()
    for line in text.splitlines():
        match = None if fence.inside(line) else _HEADING.match(line)
        if match:
            return match["rest"].strip().rstrip("#").strip() or None
    return None


def join_sources(sources, variables: dict, conditions: dict, doc_id: str) -> Joined:
    """Expand directives in each included source, apply its options and join the results.

    ``sources`` are the :class:`py_doc.config.Source` entries of a document. The metadata is that of the
    first source's front matter.
    """
    parts: list[tuple[Path, str]] = []
    first = Metadata()
    included = [source for source in sources if source.include]
    if not included:
        raise ConversionError(f"Document '{doc_id}' has no sources to build")
    for index, source in enumerate(included):
        if not source.file.is_file():
            raise FileNotFoundError(f"Source for document '{doc_id}' not found: {source.file}")
        try:
            text = source.file.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ConversionError(f"Cannot read '{source.file}': it is not valid UTF-8 ({exc.reason})") from exc
        text = directives.expand(text, source.file, variables, conditions)
        warn_unclosed_fence(text, str(source.file))
        front, body = split_front_matter(text)
        metadata = read_front_matter(front, source.file)
        if index == 0:
            first = metadata
        if source.title:
            body = retitle(body, source.title)
        body = shift_headings(keep_deep_hashes_as_text(body), source.heading_offset, source.file.name)
        text = body.rstrip("\n") + "\n"
        parts.append((source.file, f"{PAGE_BREAK}\n{text}" if index and source.page_break else text))
    joined = Joined(parts, first, None)
    joined.first_heading = first_heading(joined.markdown)
    return joined
