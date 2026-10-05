"""The style rules. Each takes the prose segments of one file and returns its issues."""

from __future__ import annotations

import re
from pathlib import Path

from .config import RULE_ACRONYM, RULE_GLOSSARY, RULE_REDUNDANT, LintConfig
from .model import LintIssue
from .text import Segment


def _bounded(pattern: str) -> str:
    return rf"(?<!\w){pattern}(?!\w)"


def glossary(file: Path, segments: list[Segment], config: LintConfig) -> list[LintIssue]:
    """Terms spelt differently from their canonical form, in any capitalisation."""
    issues: list[LintIssue] = []
    for canonical, variants in config.glossary.items():
        any_case = re.compile(_bounded(re.escape(canonical)), re.IGNORECASE)
        # Listed variants catch genuine misspellings such as Lw2m, which differ by more than case.
        misspellings = [v for v in variants if v.lower() != canonical.lower()]
        spelt = re.compile("|".join(_bounded(re.escape(v)) for v in misspellings)) if misspellings else None
        for segment in segments:
            for match in any_case.finditer(segment.text):
                if match.group(0) != canonical:
                    issues.append(
                        LintIssue(
                            file, segment.line_at(match.start()), RULE_GLOSSARY, "Glossary",
                            f"Incorrect term capitalization '{match.group(0)}'. Preferred: '{canonical}'.",
                            suggestion=canonical,
                        )
                    )  # fmt: skip
            if spelt:
                for match in spelt.finditer(segment.text):
                    issues.append(
                        LintIssue(
                            file, segment.line_at(match.start()), RULE_GLOSSARY, "Glossary",
                            f"Incorrect term '{match.group(0)}'. Preferred: '{canonical}'.",
                            suggestion=canonical,
                        )
                    )  # fmt: skip
    return issues


def redundant_phrases(file: Path, segments: list[Segment], config: LintConfig) -> list[LintIssue]:
    """Wordy phrases. They are matched across soft line wraps, and every occurrence is reported."""
    issues: list[LintIssue] = []
    for phrase, replacement in config.redundant_phrases.items():
        words = (re.escape(word) for word in phrase.split())
        pattern = re.compile(_bounded(r"\s+".join(words)), re.IGNORECASE)
        for segment in segments:
            for match in pattern.finditer(segment.text):
                issues.append(
                    LintIssue(
                        file, segment.line_at(match.start()), RULE_REDUNDANT, "Style",
                        f"Redundant phrase found: '{phrase}'. Consider simplifying.",
                        suggestion=replacement or "remove it",
                    )
                )  # fmt: skip
    return issues


# --- acronyms -----------------------------------------------------------------------------------

_STOP_WORDS = {"of", "as", "a", "an", "the", "to", "and", "for", "in", "on", "by", "with"}
_WORD = re.compile(r"[A-Za-z0-9]+")
_FORWARD = re.compile(r"\(\s*([A-Za-z0-9]{2,})\s*\)")  # Full Name (ABC)
_REVERSE = re.compile(r"(?<![\w])([A-Za-z0-9]{2,})\s*\(([^()]+)\)")  # ABC (Full Name)
_USE = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9]+(?![A-Za-z0-9_])")


def _looks_like_acronym(token: str) -> bool:
    return sum(ch.isupper() for ch in token) >= 2


def _expands(words: list[str], acronym: str) -> bool:
    """Whether ``words`` could spell out ``acronym``: the first word starts it and the rest follow in order."""
    if len(words) < 2 or words[0].lower() in _STOP_WORDS:
        return False
    letters = iter(acronym.lower())
    if words[0][0].lower() != acronym[0].lower():
        return False
    return all(any(letter == word[0].lower() for letter in letters) for word in words if word.lower() not in _STOP_WORDS)


def _definitions(text: str) -> list[tuple[str, int]]:
    """Acronym definitions in ``text`` as (acronym, offset of the acronym), in either order."""
    found: list[tuple[str, int]] = []
    for match in _FORWARD.finditer(text):
        acronym = match.group(1)
        if not _looks_like_acronym(acronym):
            continue
        words = _WORD.findall(text[: match.start()])
        for count in range(min(len(words), len(acronym) + 2), 1, -1):
            if _expands(words[-count:], acronym):
                found.append((acronym, match.start(1)))
                break
    for match in _REVERSE.finditer(text):
        acronym = match.group(1)
        if _looks_like_acronym(acronym) and _expands(_WORD.findall(match.group(2)), acronym):
            found.append((acronym, match.start(1)))
    return found


def acronyms(file: Path, segments: list[Segment], config: LintConfig) -> list[LintIssue]:
    """The first use of each all-capitals acronym that is not defined, or is defined only later."""
    first_definition: dict[str, tuple[int, int, int]] = {}  # acronym -> (segment, offset, line)
    defining: set[tuple[int, int]] = set()
    for index, segment in enumerate(segments):
        for acronym, offset in _definitions(segment.text):
            defining.add((index, offset))
            first_definition.setdefault(acronym, (index, offset, segment.line_at(offset)))

    exempt = config.allowed_acronyms | set(config.glossary)
    reported: set[str] = set()
    issues: list[LintIssue] = []
    for index, segment in enumerate(segments):
        for match in _USE.finditer(segment.text):
            token = match.group(0)
            if len(token) < config.acronym_min_length or not _looks_like_acronym(token):
                continue
            if token in exempt or token in reported or (index, match.start()) in defining:
                continue
            defined = first_definition.get(token)
            if defined and (defined[0], defined[1]) < (index, match.start()):
                continue
            reported.add(token)
            line = segment.line_at(match.start())
            if defined:
                message = f"Acronym '{token}' is used before it is defined on line {defined[2]}."
            else:
                message = f"Acronym '{token}' is used without being defined."
            issues.append(
                LintIssue(
                    file, line, RULE_ACRONYM, "Acronym", message,
                    suggestion=f"Define it on first use, for example 'Full Name ({token})'.",
                )
            )  # fmt: skip
    return issues
