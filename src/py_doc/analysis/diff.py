"""A semantic diff of two versions of a Markdown document: which sections were added, removed, renamed, moved
or changed, rather than which lines.

A section is a heading and the blocks up to the next heading of any level, named by the path of headings
above it (``Install > Windows``). Text is compared with its whitespace collapsed, so rewrapping a paragraph
is not a change. Text before the first heading is the ``(preamble)``.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from py_doc.markdown import nodes as n
from py_doc.markdown import parse

PREAMBLE = "(preamble)"
_WORD = re.compile(r"\S+")


@dataclass
class Section:
    path: tuple[str, ...]  # heading texts from the top: ("Install", "Windows")
    level: int  # 0 for the preamble
    line: int
    body: str  # the section's own text without its heading, whitespace collapsed

    @property
    def title(self) -> str:
        return " > ".join(self.path) or PREAMBLE


@dataclass
class SectionChange:
    kind: str  # added, removed, renamed, moved, changed
    old: Section | None
    new: Section | None
    words_added: int = 0
    words_removed: int = 0
    detail: list[str] = field(default_factory=list)

    def describe(self) -> str:
        if self.kind == "added":
            return f"+ added    {self.new.title} (line {self.new.line}, {len(_WORD.findall(self.new.body))} words)"
        if self.kind == "removed":
            return f"- removed  {self.old.title} (was line {self.old.line})"
        if self.kind == "renamed":
            text = f"~ renamed  {self.old.title} -> {self.new.title}"
        elif self.kind == "moved":
            text = f"> moved    {self.new.title} (line {self.old.line} -> {self.new.line})"
        else:
            text = f"* changed  {self.new.title}"
        if self.words_added or self.words_removed:
            text += f" (+{self.words_added} / -{self.words_removed} words)"
        return text

    def as_dict(self) -> dict:
        def side(section: Section | None):
            return None if section is None else {"section": section.title, "level": section.level, "line": section.line}

        return {
            "kind": self.kind,
            "old": side(self.old),
            "new": side(self.new),
            "words_added": self.words_added,
            "words_removed": self.words_removed,
        }


def sections(text: str) -> list[Section]:
    """The sections of a Markdown text, in order. Headings inside lists or quotes do not start one."""
    lines = text.splitlines()
    document = parse(text)
    start = document.front_matter.end_line if document.front_matter else 0
    heads = [block for block in document.children if isinstance(block, n.Heading)]
    found: list[Section] = []
    path: list[str] = []
    bounds = [(None, start + 1)] + [(head, head.line) for head in heads]
    for index, (head, first) in enumerate(bounds):
        end = bounds[index + 1][1] - 1 if index + 1 < len(bounds) else len(lines)
        body_from = head.end_line + 1 if head else first
        body = " ".join(" ".join(lines[body_from - 1 : end]).split())
        if head is None:
            if body:
                found.append(Section((), 0, first, body))
            continue
        title = " ".join(n.plain_text(head.children).split())
        del path[head.level - 1 :]
        path += [""] * (head.level - 1 - len(path)) + [title]
        found.append(Section(tuple(p for p in path if p), head.level, head.line, body))
    return found


def _words(old: str, new: str) -> tuple[int, int]:
    a, b = _WORD.findall(old), _WORD.findall(new)
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
    return added, removed


def diff_markdown(old_text: str, new_text: str) -> list[SectionChange]:
    """The section changes from ``old_text`` to ``new_text``, in the order of the new text, removals last."""
    old, new = sections(old_text), sections(new_text)
    old_by_path: dict[tuple, Section] = {}
    for section in old:
        old_by_path.setdefault(section.path, section)
    matched: dict[int, Section] = {}  # index in new -> its old section
    used: set[int] = set()
    for index, section in enumerate(new):
        previous = old_by_path.get(section.path)
        if previous is not None and id(previous) not in used:
            matched[index] = previous
            used.add(id(previous))
    # A section whose path is new but whose text is an unmatched old section's was renamed (or moved under another parent)
    spare = {s.body: s for s in old if id(s) not in used and s.body}
    renamed: set[int] = set()
    for index, section in enumerate(new):
        if index not in matched and section.body in spare:
            matched[index] = spare.pop(section.body)
            used.add(id(matched[index]))
            renamed.add(index)

    # Order: sections matched by their path whose relative order changed were moved (a renamed one is reported as that)
    order = [old.index(matched[i]) for i in sorted(matched) if i not in renamed]
    keep = set(_longest_increasing(order))
    changes: list[SectionChange] = []
    for index, section in enumerate(new):
        previous = matched.get(index)
        if previous is None:
            changes.append(SectionChange("added", None, section))
            continue
        added, removed = _words(previous.body, section.body) if previous.body != section.body else (0, 0)
        if index in renamed:
            kind = "renamed" if previous.path[:-1] == section.path[:-1] else "moved"
        elif old.index(previous) not in keep:
            kind = "moved"
        elif added or removed or previous.body != section.body or previous.level != section.level:
            kind = "changed"
        else:
            continue
        changes.append(SectionChange(kind, previous, section, added, removed))
    changes += [SectionChange("removed", s, None) for s in old if id(s) not in used]
    return changes


def _longest_increasing(values: list[int]) -> list[int]:
    """The longest increasing subsequence: the sections that kept their order, so the others moved."""
    tails: list[int] = []
    parent: dict[int, int | None] = {}
    tail_at: list[int] = []
    for value in values:
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if tails[mid] < value:
                lo = mid + 1
            else:
                hi = mid
        parent[value] = tail_at[lo - 1] if lo else None
        if lo == len(tails):
            tails.append(value)
            tail_at.append(value)
        else:
            tails[lo] = value
            tail_at[lo] = value
    result: list[int] = []
    node = tail_at[-1] if tail_at else None
    while node is not None:
        result.append(node)
        node = parent[node]
    return result[::-1]
