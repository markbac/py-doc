"""Text directives that run before Markdown is parsed: includes, conditions and variables.

``[[INCLUDE: file.md]]``
    Put another Markdown file here. It is expanded in turn, and a file that includes itself is an error.
``[[INCLUDE-CODE: file.py]]``
    Put a file here as a fenced code block, verbatim. The language comes from the extension.
``[[IF: key]]``, ``[[IF: key == value]]``, ``[[NOT: key]]`` ... ``[[ENDIF]]``
    Keep the lines between only when the condition holds. Blocks may be nested.
``{{name}}``
    Replace with the value of a variable.

Directives on their own line, and ``{{name}}`` in running text, are the only forms recognised. Anything in
a fenced code block or an inline code span is left alone, so a document can show the syntax. Paths are
relative to the file that contains the directive. A mistake is an error that names the file and line,
never a silently dropped section; the one exception is an undefined variable, which is left as written
and reported, because ``{{`` is also ordinary text in many documents.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ConversionError

logger = logging.getLogger(__name__)

MAX_DEPTH = 10

_INCLUDE = re.compile(r"^\[\[INCLUDE:\s*(?P<path>[^\]]+?)\s*\]\]\s*$")
_INCLUDE_CODE = re.compile(r"^\[\[INCLUDE-CODE:\s*(?P<path>[^\]]+?)\s*\]\]\s*$")
_IF = re.compile(r"^\[\[(?P<kind>IF|NOT):\s*(?P<expr>[^\]]+?)\s*\]\]\s*$")
_ENDIF = re.compile(r"^\[\[ENDIF\]\]\s*$")
_COMPARE = re.compile(r"""^(?P<key>\w+)\s*(?P<op>==|!=)\s*(?P<value>"[^"]*"|'[^']*'|\S+)$""")
_VARIABLE = re.compile(r"\{\{\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(?P<ticks>`+)(?P<body>.+?)(?P=ticks)")

_LANGUAGES = {".yml": "yaml", ".md": "markdown", ".sh": "bash", ".py": "python", ".js": "javascript", ".ts": "typescript"}


@dataclass(frozen=True)
class Problem:
    """A mistake in the directives of one file."""

    line: int
    message: str


class DirectiveError(ConversionError):
    """A directive cannot be applied. The message names the file and line."""


class Fence:
    """Tracks whether a line is inside a fenced code block, following CommonMark's closing rule."""

    def __init__(self) -> None:
        self.marker: str | None = None

    def inside(self, line: str) -> bool:
        """True for the lines of a fenced block, including the fences themselves."""
        match = _FENCE.match(line)
        if self.marker is None:
            if match:
                self.marker = match["fence"]
                return True
            return False
        closing = match and match["fence"][0] == self.marker[0] and len(match["fence"]) >= len(self.marker)
        if closing and not line.strip().strip(self.marker[0]):
            self.marker = None
        return True


def _truth(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)


def _holds(expr: str, conditions: dict[str, Any]) -> bool:
    """Evaluate ``key`` or ``key == value``. A key that is not defined raises KeyError naming it."""
    match = _COMPARE.match(expr)
    key = match["key"] if match else expr
    if key not in conditions:
        raise KeyError(key)
    if not match:
        return _truth(conditions[key])
    same = str(conditions[key]) == match["value"].strip("\"'")
    return same if match["op"] == "==" else not same


def _substitute(line: str, variables: dict[str, Any], undefined: list[str]) -> str:
    """Replace ``{{name}}`` outside inline code spans."""

    def replace(match: re.Match) -> str:
        name = match["name"]
        if name in variables:
            return str(variables[name])
        undefined.append(name)
        return match[0]

    parts, last = [], 0
    for span in _INLINE_CODE.finditer(line):
        parts.append(_VARIABLE.sub(replace, line[last : span.start()]))
        parts.append(span[0])
        last = span.end()
    parts.append(_VARIABLE.sub(replace, line[last:]))
    return "".join(parts)


def _code_block(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig").rstrip("\r\n")
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    language = _LANGUAGES.get(path.suffix.lower(), path.suffix.lower().lstrip("."))
    return [f"{fence}{language}", *text.splitlines(), fence]


def expand(
    text: str,
    file: Path,
    variables: dict[str, Any] | None = None,
    conditions: dict[str, Any] | None = None,
) -> str:
    """Apply every directive in ``text``, which was read from ``file``. Raises :class:`DirectiveError`."""
    lines = _expand(text, Path(file), variables or {}, conditions or {}, (), 0)
    return "\n".join(lines) + ("\n" if lines and text.endswith("\n") else "")


def _expand(text, file: Path, variables, conditions, parents: tuple[Path, ...], depth: int) -> list[str]:
    def fail(number: int, message: str) -> DirectiveError:
        return DirectiveError(f"{file}:{number}: {message}")

    if depth > MAX_DEPTH:
        raise DirectiveError(f"{file}: includes are nested more than {MAX_DEPTH} deep")
    out: list[str] = []
    fence = Fence()
    blocks: list[tuple[bool, int]] = []  # (condition held, line of the [[IF:]])
    for number, line in enumerate(text.splitlines(), start=1):
        if fence.inside(line):
            if all(held for held, _ in blocks):
                out.append(line)
            continue
        if match := _IF.match(line):
            try:
                held = _holds(match["expr"], conditions) != (match["kind"] == "NOT")
            except KeyError as exc:
                raise fail(number, f"condition '{exc.args[0]}' is not defined; add it under 'conditions'") from None
            blocks.append((held, number))
            continue
        if _ENDIF.match(line):
            if not blocks:
                raise fail(number, "[[ENDIF]] has no [[IF:]] or [[NOT:]] before it")
            blocks.pop()
            continue
        if not all(held for held, _ in blocks):
            continue
        if match := (_INCLUDE_CODE.match(line) or _INCLUDE.match(line)):
            target = (file.parent / match["path"]).resolve()
            if not target.is_file():
                raise fail(number, f"included file not found: {target}")
            if _INCLUDE_CODE.match(line):
                out += _code_block(target)
                continue
            if target in (file.resolve(), *parents):
                raise fail(number, f"{target.name} includes itself, directly or through other files")
            logger.debug(f"Including {target} from {file}:{number}")
            fragment = target.read_text(encoding="utf-8-sig")
            out += _expand(fragment, target, variables, conditions, (*parents, file.resolve()), depth + 1)
            continue
        undefined: list[str] = []
        out.append(_substitute(line, variables, undefined))
        for name in dict.fromkeys(undefined):
            logger.warning(f"{file}:{number}: variable '{name}' is not defined, so '{{{{{name}}}}}' is left as written")
    if blocks:
        raise fail(blocks[-1][1], "[[IF:]] or [[NOT:]] is never closed with [[ENDIF]]")
    return out


def check(text: str, file: Path) -> list[Problem]:
    """Mistakes in the directives of one file that do not need variables or conditions to find.

    That is: an [[ENDIF]] with nothing open, a block never closed, and an include whose file is missing.
    """
    problems: list[Problem] = []
    fence = Fence()
    open_lines: list[int] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if fence.inside(line):
            continue
        if _IF.match(line):
            open_lines.append(number)
        elif _ENDIF.match(line):
            if open_lines:
                open_lines.pop()
            else:
                problems.append(Problem(number, "[[ENDIF]] has no [[IF:]] or [[NOT:]] before it"))
        elif match := (_INCLUDE_CODE.match(line) or _INCLUDE.match(line)):
            target = (Path(file).parent / match["path"]).resolve()
            if not target.is_file():
                problems.append(Problem(number, f"included file not found: {match['path']}"))
    problems += [Problem(n, "[[IF:]] or [[NOT:]] is never closed with [[ENDIF]]") for n in open_lines]
    return sorted(problems, key=lambda p: p.line)
