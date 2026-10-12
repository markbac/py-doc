"""Find diagram fences in Markdown: ```plantuml ... ``` and the Azure DevOps form :::mermaid ... :::."""

from __future__ import annotations

import re
from dataclasses import dataclass

from py_doc.directives import Fence

from .registry import BY_FENCE

_OPEN = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})\s*(?P<info>.*)$")
_DIV = re.compile(r"^:{3,}\s*(?P<name>[A-Za-z][\w-]*)\s*$")
_DIV_END = re.compile(r"^:{3,}\s*$")
_OPTION = re.compile(r"""(?P<key>\w+)=(?:"(?P<quoted>[^"]*)"|(?P<bare>\S+))""")


@dataclass(frozen=True)
class Block:
    start: int  # 0-based index of the first line (the opening fence)
    end: int  # index of the last line (the closing fence), or of the last line of an unclosed block
    fence: str  # the name used in the document, for example "puml"
    body: str
    options: dict[str, str]
    line: int  # 1-based line of the opening fence


def _options(info: str) -> dict[str, str]:
    return {m["key"]: m["quoted"] if m["quoted"] is not None else m["bare"] for m in _OPTION.finditer(info)}


def find_blocks(text: str) -> list[Block]:
    """Diagram blocks outside other code, in order. Only fence names with a renderer are returned."""
    lines = text.splitlines()
    blocks: list[Block] = []
    other = Fence()  # code blocks of other languages, in which diagram-like lines are only text
    index = 0
    while index < len(lines):
        line = lines[index]
        match = _OPEN.match(line)
        if not other.marker and match:
            name = match["info"].split(None, 1)[0].lower().lstrip("{.").rstrip("}") if match["info"] else ""
            if name in BY_FENCE:
                marker = match["fence"]
                end = index + 1
                while end < len(lines):
                    closing = _OPEN.match(lines[end])
                    if closing and closing["fence"][0] == marker[0] and len(closing["fence"]) >= len(marker) and not closing["info"]:
                        break
                    end += 1
                body = "\n".join(lines[index + 1 : min(end, len(lines))])
                blocks.append(Block(index, min(end, len(lines) - 1), name, body, _options(match["info"]), index + 1))
                index = end + 1
                continue
        div = None if other.marker else _DIV.match(line)
        if div and div["name"].lower() in BY_FENCE:
            end = index + 1
            while end < len(lines) and not _DIV_END.match(lines[end]):
                end += 1
            body = "\n".join(lines[index + 1 : end])
            blocks.append(Block(index, min(end, len(lines) - 1), div["name"].lower(), body, {}, index + 1))
            index = end + 1
            continue
        other.inside(line)
        index += 1
    return blocks
