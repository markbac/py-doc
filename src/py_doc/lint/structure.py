"""Structure rules: project conventions that neither the style rules nor markdownlint can know.

The engine runs a handful of rule *types*. What to flag, how severely and what to say is configuration
(``lint.structure`` in ``py-doc.yml``), so a project's conventions are data, not code.

Rule types
    ``manifest-file-exists``  a source listed under a document does not exist.
    ``regex-line``            flag every line matching ``pattern``. ``scope_prefix`` limits it to lines starting
                              with that text, ``exclude_pattern`` suppresses a match that is already right.
    ``blank-line-between``    flag a blank line between two lines that both match ``pattern`` (a loose list).
    ``path-exists``           ``pattern`` has one group, a path that must exist relative to the file.
    ``balanced-markers``      each ``open_pattern`` needs a later ``close_pattern``, and the other way round.
    ``requires-caption``      the line after a ``table``, ``image``, ``fence`` or ``line`` (``trigger_pattern``)
                              must match ``required_pattern``.
    ``cross-file-anchors``    every ``#anchor`` link must match a heading anchor of the whole document, with
                              pandoc's ``-1`` and ``-2`` suffixes for repeated headings.

Fenced code is never searched, and neither are inline code spans, so a document can show the syntax.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml

from py_doc.directives import Fence

from .model import SEVERITIES, LintIssue

logger = logging.getLogger(__name__)

CATEGORY = "Structure"
TYPES = (
    "manifest-file-exists", "regex-line", "blank-line-between", "path-exists", "balanced-markers",
    "requires-caption", "cross-file-anchors",
)  # fmt: skip
BLOCKS = ("table", "image", "fence", "line")
# Rules of the createdocs bundle that py-doc replaces: both callout spellings are accepted.
SUPERSEDED = {"structure/admonition-legacy-format": "both callout spellings are accepted"}

_KEYS = {
    "id", "type", "enabled", "severity", "message", "pattern", "exclude_pattern", "scope_prefix", "open_pattern",
    "close_pattern", "unmatched_open_message", "unmatched_close_message", "block", "languages", "div_languages",
    "trigger_pattern", "required_pattern", "collision_severity", "collision_message",
}  # fmt: skip
_PATTERN_KEYS = ("pattern", "exclude_pattern", "open_pattern", "close_pattern", "trigger_pattern", "required_pattern")
_REQUIRED = {
    "regex-line": ("pattern",),
    "blank-line-between": ("pattern",),
    "path-exists": ("pattern",),
    "balanced-markers": ("open_pattern", "close_pattern"),
    "requires-caption": ("block", "required_pattern"),
    "cross-file-anchors": ("message",),
    "manifest-file-exists": (),
}  # fmt: skip


class StructureRuleError(ValueError):
    """A rule in the configuration is not valid. The message names the rule."""


@dataclass(frozen=True)
class StructureRule:
    id: str
    type: str
    severity: str = "warning"
    message: str = ""
    enabled: bool = True
    pattern: re.Pattern | None = None
    exclude_pattern: re.Pattern | None = None
    scope_prefix: str | None = None
    open_pattern: re.Pattern | None = None
    close_pattern: re.Pattern | None = None
    unmatched_open_message: str | None = None
    unmatched_close_message: str | None = None
    block: str | None = None
    languages: tuple[str, ...] | None = None
    div_languages: tuple[str, ...] | None = None
    trigger_pattern: re.Pattern | None = None
    required_pattern: re.Pattern | None = None
    collision_severity: str | None = None
    collision_message: str | None = None


def parse_rules(entries: Any, where: str = "lint.structure") -> list[StructureRule]:
    """Validate the rule entries. Raises :class:`StructureRuleError` naming the rule and the problem."""
    if not isinstance(entries, list):
        raise StructureRuleError(f"{where} must be a list of rules")
    rules: list[StructureRule] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise StructureRuleError(f"{where}[{index}] must be a mapping")
        name = entry.get("id")
        if not isinstance(name, str) or not name:
            raise StructureRuleError(f"{where}[{index}] needs an 'id'")
        place = f"{where}: rule '{name}'"
        if name in seen:
            raise StructureRuleError(f"{place} is defined twice")
        seen.add(name)
        unknown = sorted(set(entry) - _KEYS)
        if unknown:
            raise StructureRuleError(f"{place} has unknown key '{unknown[0]}'. Keys: {', '.join(sorted(_KEYS))}")
        kind = entry.get("type")
        if kind not in TYPES:
            raise StructureRuleError(f"{place} has type {kind!r}. Types: {', '.join(TYPES)}")
        severity = entry.get("severity", "warning")
        if severity not in SEVERITIES:
            raise StructureRuleError(f"{place}: severity must be one of {', '.join(SEVERITIES)}")
        if entry.get("collision_severity", severity) not in SEVERITIES:
            raise StructureRuleError(f"{place}: collision_severity must be one of {', '.join(SEVERITIES)}")
        # createdocs wrote the pattern of a caption rule as `pattern`.
        if kind == "requires-caption" and "pattern" in entry and "required_pattern" not in entry:
            entry = {**entry, "required_pattern": entry["pattern"]}
            entry.pop("pattern")
        for key in _REQUIRED[kind]:
            if key not in entry:
                raise StructureRuleError(f"{place} (type {kind}) needs '{key}'")
        if kind == "requires-caption":
            if entry["block"] not in BLOCKS:
                raise StructureRuleError(f"{place}: block must be one of {', '.join(BLOCKS)}")
            if entry["block"] == "line" and "trigger_pattern" not in entry:
                raise StructureRuleError(f"{place} (block line) needs 'trigger_pattern'")
        compiled: dict[str, Any] = {}
        for key in _PATTERN_KEYS:
            if key in entry:
                try:
                    compiled[key] = re.compile(entry[key])
                except (re.error, TypeError) as exc:
                    raise StructureRuleError(f"{place}: {key} is not a valid regular expression: {exc}") from None
        if kind == "path-exists" and compiled["pattern"].groups < 1:
            raise StructureRuleError(f"{place}: pattern needs a group around the path")
        rules.append(
            StructureRule(
                id=name, type=kind, severity=severity, message=str(entry.get("message", "")),
                enabled=bool(entry.get("enabled", True)), scope_prefix=entry.get("scope_prefix"),
                unmatched_open_message=entry.get("unmatched_open_message"),
                unmatched_close_message=entry.get("unmatched_close_message"), block=entry.get("block"),
                languages=tuple(str(x).lower() for x in entry["languages"]) if "languages" in entry else None,
                div_languages=tuple(str(x).lower() for x in entry["div_languages"]) if "div_languages" in entry else None,
                collision_severity=entry.get("collision_severity"), collision_message=entry.get("collision_message"),
                **compiled,
            )
        )  # fmt: skip
    return rules


def load_rules(path: Path) -> list[StructureRule]:
    """Rules from a YAML file: a list, or a mapping with ``rules`` (the createdocs ``structure-rules.yaml``).

    Rules that py-doc replaces are left out, and the log says so.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise StructureRuleError(f"The structure rules file was not found: {path}") from None
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise StructureRuleError(f"{path}: cannot read the structure rules: {exc}") from None
    entries = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise StructureRuleError(f"{path}: expected a list of rules, or a mapping with a 'rules' list")
    kept = []
    for entry in entries:
        reason = SUPERSEDED.get(entry.get("id")) if isinstance(entry, dict) else None
        if reason:
            logger.info(f"{path.name}: rule '{entry['id']}' is not needed: {reason}")
        else:
            kept.append(entry)
    return parse_rules(kept, str(path))


# --- scanning ------------------------------------------------------------------------------------


_BACKTICKS = re.compile(r"`+[^`]*`+")
_URL = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_DIV = re.compile(r"^(:{3,})\s*\{?\.?([A-Za-z0-9_-]*)")
_CODE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*([^\s`{]*)")
_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_ANCHOR_LINK = re.compile(r"!?\[[^\]]*\]\(#([^)\s]+)\)")
_FORMATTING = re.compile(r"[`*~]|(?<!\w)_|_(?!\w)")  # an underscore inside a word is part of it
_LINK_TEXT = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _spans(line: str) -> list[tuple[int, int]]:
    return [match.span() for match in _BACKTICKS.finditer(line)]


def _inside(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def live_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """``(line number, line)`` for every line outside fenced code."""
    fence = Fence()
    for number, line in enumerate(lines, start=1):
        if not fence.inside(line):
            yield number, line


def _issue(rule: StructureRule, file: Path, line: int, message: str, severity: str | None = None) -> LintIssue:
    return LintIssue(file, line, rule.id, CATEGORY, message, severity or rule.severity)


def anchor(text: str) -> str:
    """The identifier pandoc gives a heading (``auto_identifiers``).

    Formatting is dropped, then anything but letters, digits, ``_``, ``-`` and ``.`` (spaces become hyphens),
    then lower case, then everything before the first letter. A heading with no letter is ``section``.
    """
    plain = _LINK_TEXT.sub(r"\1", _FORMATTING.sub("", text))
    kept = re.sub(r"[^\w\-. ]", "", plain, flags=re.UNICODE).strip().lower().replace(" ", "-")
    kept = re.sub(r"^[^a-zÀ-￿]+", "", kept)
    return kept or "section"


def check_file(file: Path, text: str, rules: list[StructureRule]) -> list[LintIssue]:
    """Findings of every enabled per-file rule for one file."""
    active = [r for r in rules if r.enabled]
    lines = text.splitlines()
    issues: list[LintIssue] = []
    by_type = {kind: [r for r in active if r.type == kind] for kind in TYPES}

    for number, line in live_lines(lines):
        spans = _spans(line)
        for rule in by_type["regex-line"]:
            if rule.scope_prefix and not line.startswith(rule.scope_prefix):
                continue
            for match in rule.pattern.finditer(line):
                if _inside(match.start(), spans) or (rule.exclude_pattern and rule.exclude_pattern.search(line)):
                    continue
                issues.append(_issue(rule, file, number, rule.message))
                break  # one finding per rule per line
        if not line.strip() and number >= 2 and lines[number - 2].strip():
            for rule in by_type["blank-line-between"]:
                if not rule.pattern.match(lines[number - 2]):
                    continue
                following = number  # the index of the line after this blank
                while following < len(lines) and not lines[following].strip():
                    following += 1
                if following < len(lines) and rule.pattern.match(lines[following]):
                    issues.append(_issue(rule, file, number, rule.message))
        for rule in by_type["path-exists"]:
            for match in rule.pattern.finditer(line):
                if _inside(match.start(), spans):
                    continue
                target = match.group(1).strip().strip("<>")
                if _URL.match(target) or target.startswith("#"):
                    continue  # a web address, or an anchor, which cross-file-anchors checks
                path = unquote(target.split("#", 1)[0].split("?", 1)[0])
                if path and not (file.parent / path).exists():
                    issues.append(_issue(rule, file, number, rule.message.format(target=path)))

    for rule in by_type["balanced-markers"]:
        issues += _balanced(file, lines, rule)
    if by_type["requires-caption"]:
        issues += _captions(file, lines, by_type["requires-caption"])
    return sorted(issues, key=lambda i: (i.line, i.rule))


def _balanced(file: Path, lines: list[str], rule: StructureRule) -> list[LintIssue]:
    stack: list[tuple[int, str]] = []
    issues: list[LintIssue] = []
    for number, line in live_lines(lines):
        spans = _spans(line)
        events = [(m.start(), "open", m.group(0)) for m in rule.open_pattern.finditer(line) if not _inside(m.start(), spans)]
        events += [(m.start(), "close", m.group(0)) for m in rule.close_pattern.finditer(line) if not _inside(m.start(), spans)]
        for _, kind, marker in sorted(events):
            if kind == "open":
                stack.append((number, marker))
            elif stack:
                stack.pop()
            else:
                issues.append(_issue(rule, file, number, (rule.unmatched_close_message or rule.message).format(marker=marker)))
    for number, marker in stack:
        issues.append(_issue(rule, file, number, (rule.unmatched_open_message or rule.message).format(marker=marker)))
    return issues


def _captions(file: Path, lines: list[str], rules: list[StructureRule]) -> list[LintIssue]:
    """Tables, pictures, code blocks, diagram divs and trigger lines each need a caption on the line after."""
    table = next((r for r in rules if r.block == "table"), None)
    image = next((r for r in rules if r.block == "image"), None)
    fenced = next((r for r in rules if r.block == "fence"), None)
    line_rules = [r for r in rules if r.block == "line"]
    count = len(lines)
    issues: list[LintIssue] = []

    def captioned(after: int, rule: StructureRule) -> bool:
        index = after
        while index < count and not lines[index].strip():
            index += 1
        return index < count and bool(rule.required_pattern.search(lines[index]))

    i = 0
    while i < count:
        line = lines[i]
        if code := _CODE.match(line):
            marker, language = code.group(1), code.group(2).lower()
            end = i + 1
            while end < count and not (lines[end].lstrip().startswith(marker[0] * len(marker)) and not lines[end].strip(marker[0])):
                end += 1
            wanted = fenced is not None and (not fenced.languages or language in fenced.languages)
            if wanted and not captioned(end + 1, fenced):
                issues.append(_issue(fenced, file, min(end + 1, count), fenced.message))
            i = end + 1
            continue
        if div := _DIV.match(line):
            marker, language = div.group(1), div.group(2).lower()
            end = i + 1
            while end < count and not lines[end].startswith(marker):
                end += 1
            if fenced is not None and language in (fenced.div_languages or ()) and not captioned(end + 1, fenced):
                issues.append(_issue(fenced, file, min(end + 1, count), fenced.message))
            i = end + 1
            continue
        if table and _TABLE_ROW.match(line):
            while i < count and _TABLE_ROW.match(lines[i]):
                i += 1
            if not captioned(i, table):
                issues.append(_issue(table, file, i, table.message))
            continue
        if image and _IMAGE.search(line) and not captioned(i + 1, image):
            issues.append(_issue(image, file, i + 1, image.message))
        for rule in line_rules:
            if rule.trigger_pattern.search(line) and not captioned(i + 1, rule):
                issues.append(_issue(rule, file, i + 1, rule.message))
        i += 1
    return issues


# --- across a document ------------------------------------------------------------------------------


def _with_includes(file: Path, seen: tuple[Path, ...] = ()) -> Iterator[tuple[Path, int, str]]:
    """The lines of ``file`` in document order, with the files it includes expanded in place."""
    from py_doc.directives import _INCLUDE

    resolved = file.resolve()
    if resolved in seen or not file.is_file():
        return
    try:
        lines = file.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    fence = Fence()
    for number, line in enumerate(lines, start=1):
        if not fence.inside(line) and (match := _INCLUDE.match(line)):
            yield from _with_includes(file.parent / match["path"], (*seen, resolved))
        else:
            yield file, number, line


def check_document(files: list[Path], rules: list[StructureRule]) -> list[LintIssue]:
    """The rules that look at a whole document: its files must exist, and its ``#anchor`` links must resolve."""
    issues: list[LintIssue] = []
    for rule in (r for r in rules if r.enabled and r.type == "manifest-file-exists"):
        issues += [_issue(rule, f, 1, rule.message) for f in files if not f.is_file()]
    anchors = [r for r in rules if r.enabled and r.type == "cross-file-anchors"]
    if not anchors:
        return issues

    headings: list[tuple[Path, int, str]] = []
    everything: dict[Path, list[tuple[int, str]]] = {}
    fences: dict[Path, Fence] = {}
    for file, number, line in (item for f in files for item in _with_includes(f)):
        if fences.setdefault(file, Fence()).inside(line):
            continue
        everything.setdefault(file, []).append((number, line))
        if match := _HEADING.match(line):
            headings.append((file, number, anchor(match.group(2))))

    taken: dict[str, int] = {}
    resolved: set[str] = set()
    first: dict[str, Path] = {}
    collisions: list[tuple[Path, int, str]] = []
    for file, number, base in headings:
        seen = taken.get(base, 0)
        resolved.add(base if seen == 0 else f"{base}-{seen}")
        taken[base] = seen + 1
        if seen == 0:
            first[base] = file
        else:
            collisions.append((file, number, base))

    for rule in anchors:
        if rule.collision_message:
            for file, number, base in collisions:
                text = rule.collision_message.format(target=base, other_file=first[base].name)
                issues.append(_issue(rule, file, number, text, rule.collision_severity or rule.severity))
        for file, entries in everything.items():
            for number, line in entries:
                spans = _spans(line)
                for match in _ANCHOR_LINK.finditer(line):
                    if not _inside(match.start(), spans) and unquote(match.group(1)).lower() not in resolved:
                        issues.append(_issue(rule, file, number, rule.message.format(target=match.group(1))))
    return sorted(issues, key=lambda i: (str(i.file), i.line, i.rule))
