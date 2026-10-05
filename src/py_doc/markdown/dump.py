"""A readable text outline of a document, used for golden tests and debugging.

Each node is one line: its type, its fields, then its source position (``@3`` or ``@3-5``).
Children are indented below their parent. Fields that are ``None`` or ``False`` are left out, so a
boolean such as ``closed`` is only shown when it is true: a fence without it is unclosed.
"""

from __future__ import annotations

import json
from dataclasses import fields

from . import nodes as n

_SKIPPED_FIELDS = {"line", "end_line", "children", "front_matter"}


def dump(node: n.Node) -> str:
    lines: list[str] = []
    _dump(node, 0, lines)
    return "\n".join(lines) + "\n"


def _dump(node: n.Node, depth: int, out: list[str]) -> None:
    out.append("  " * depth + _describe(node))
    if isinstance(node, n.Document) and node.front_matter is not None:
        _dump(node.front_matter, depth + 1, out)
    for child in getattr(node, "children", ()):
        _dump(child, depth + 1, out)


def _describe(node: n.Node) -> str:
    parts = [type(node).__name__]
    for field in fields(node):
        if field.name in _SKIPPED_FIELDS:
            continue
        value = getattr(node, field.name)
        if value is None or value is False:
            continue
        parts.append(field.name if value is True else f"{field.name}={json.dumps(value, ensure_ascii=False)}")
    line = getattr(node, "line", None)
    if line is not None:
        end_line = getattr(node, "end_line", line)
        parts.append(f"@{line}" if end_line == line else f"@{line}-{end_line}")
    return " ".join(parts)
