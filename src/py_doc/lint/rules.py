"""The style rules. Each takes the prose segments of one file and returns its issues."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from py_doc.markdown import nodes as n

from .config import (
    RULE_ACRONYM, RULE_BROKEN_LINK, RULE_DUPLICATE_HEADING, RULE_GLOSSARY, RULE_HEADING_JUMP, RULE_HEADING_LENGTH,
    RULE_IMAGE_ALT, RULE_REDUNDANT, RULE_REQUIRED_SECTION, RULE_SENTENCE_LENGTH, RULE_TERMINOLOGY, RULE_UNCLOSED_FENCE,
    LintConfig,
)  # fmt: skip
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
    return all(
        any(letter == word[0].lower() for letter in letters) for word in words if word.lower() not in _STOP_WORDS
    )


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
    return acronyms_across([(file, segments)], config)


def acronyms_across(files: list[tuple[Path, list[Segment]]], config: LintConfig) -> list[LintIssue]:
    """Acronym use over several files read in order, as the files of one document: a definition in an
    earlier file counts in the later ones, and each acronym is reported once."""
    flat = [(file, segment) for file, segments in files for segment in segments]
    first_definition: dict[str, tuple[int, int, Path, int]] = {}  # acronym -> (segment, offset, file, line)
    defining: set[tuple[int, int]] = set()
    for index, (file, segment) in enumerate(flat):
        for acronym, offset in _definitions(segment.text):
            defining.add((index, offset))
            first_definition.setdefault(acronym, (index, offset, file, segment.line_at(offset)))

    exempt = config.allowed_acronyms | set(config.glossary)
    reported: set[str] = set()
    issues: list[LintIssue] = []
    for index, (file, segment) in enumerate(flat):
        for match in _USE.finditer(segment.text):
            token = match.group(0)
            if len(token) < config.acronym_min_length or not _looks_like_acronym(token):
                continue
            if token in exempt or token in reported or (index, match.start()) in defining:
                continue
            defined = first_definition.get(token)
            if defined and (defined[0], defined[1]) < (index, match.start()):
                continue
            if not defined and not config.acronym_require_definition:
                continue
            reported.add(token)
            line = segment.line_at(match.start())
            if defined:
                where = f"line {defined[3]}" if defined[2] == file else f"{defined[2].name} line {defined[3]}"
                message = f"Acronym '{token}' is used before it is defined on {where}."
            else:
                message = f"Acronym '{token}' is used without being defined."
            suggestion = config.acronym_suggestion.replace("{acronym}", token)
            issues.append(LintIssue(file, line, RULE_ACRONYM, "Acronym", message, suggestion=suggestion or None))
    return issues


# --- structure, links and limits -----------------------------------------------------------------

_EXTERNAL = re.compile(r"^([a-z][a-z0-9+.-]*:|#|/|\{\{)", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def heading_jumps(file: Path, document: n.Document, config: LintConfig) -> list[LintIssue]:
    """A heading more than one level below the heading before it, such as a level 4 after a level 2."""
    issues: list[LintIssue] = []
    previous: int | None = None
    for node in n.walk(document):
        if not isinstance(node, n.Heading):
            continue
        if previous is not None and node.level > previous + 1:
            issues.append(
                LintIssue(
                    file, node.line, RULE_HEADING_JUMP, "Structure",
                    f"Heading level {node.level} follows level {previous}, skipping a level.",
                    suggestion=f"Make it level {previous + 1}",
                )
            )  # fmt: skip
        previous = node.level
    return issues


def broken_links(file: Path, document: n.Document, config: LintConfig) -> list[LintIssue]:
    """A link or picture whose file, relative to this file, is not there. Web addresses are not fetched.

    Text that is not from a file on disk has nothing to be relative to, so it is not checked.
    """
    if not file.is_file():
        return []
    issues: list[LintIssue] = []
    for node in n.walk(document):
        if not isinstance(node, (n.Link, n.Image)) or not node.url:
            continue
        url = unquote(node.url)  # the parser percent-encodes, so {{variable}} arrives as %7B%7Bvariable%7D%7D
        if _EXTERNAL.match(url):
            continue
        target = url.split("#", 1)[0].split("?", 1)[0]
        if target and not (file.parent / target).exists():
            kind = "Picture" if isinstance(node, n.Image) else "Link"
            issues.append(
                LintIssue(file, node.line, RULE_BROKEN_LINK, "Link", f"{kind} target '{target}' is not found.")
            )
    return issues


def image_alt(file: Path, document: n.Document, config: LintConfig) -> list[LintIssue]:
    """A picture without alt text, which a screen reader cannot describe and a caption cannot come from."""
    return [
        LintIssue(
            file,
            node.line,
            RULE_IMAGE_ALT,
            "Accessibility",
            f"Picture '{node.url}' has no alt text.",
            suggestion="Describe the picture between the brackets: ![What it shows](file.png)",
        )  # fmt: skip
        for node in n.walk(document)
        if isinstance(node, n.Image) and not node.alt.strip()
    ]


def sentence_length(file: Path, segments: list[Segment], config: LintConfig) -> list[LintIssue]:
    """A sentence of more words than ``lint.limits.sentence_words``."""
    issues: list[LintIssue] = []
    for segment in segments:
        start = 0
        for sentence in _SENTENCE_END.split(segment.text):
            offset = segment.text.find(sentence, start)
            start = offset + len(sentence)
            words = len(_WORD.findall(sentence))
            if words > config.sentence_words:
                issues.append(
                    LintIssue(
                        file, segment.line_at(offset), RULE_SENTENCE_LENGTH, "Style",
                        f"Sentence of {words} words; the limit is {config.sentence_words}.",
                        suggestion="Split it",
                    )
                )  # fmt: skip
    return issues


def heading_length(file: Path, document: n.Document, config: LintConfig) -> list[LintIssue]:
    """A heading longer than ``lint.limits.heading_length`` characters."""
    issues: list[LintIssue] = []
    for node in n.walk(document):
        if isinstance(node, n.Heading):
            text = n.plain_text(node.children).strip()
            if len(text) > config.heading_length:
                issues.append(
                    LintIssue(
                        file, node.line, RULE_HEADING_LENGTH, "Style",
                        f"Heading of {len(text)} characters; the limit is {config.heading_length}.",
                        suggestion="Shorten it",
                    )
                )  # fmt: skip
    return issues


def duplicate_headings(file: Path, document: n.Document, config: LintConfig) -> list[LintIssue]:
    """A heading with the same text as an earlier one under the same parent heading: two sections a reader
    (and a link to its anchor) cannot tell apart."""
    issues: list[LintIssue] = []
    seen: dict[tuple, int] = {}
    parents: list[str] = []  # the text of the open heading at each level
    for node in n.walk(document):
        if not isinstance(node, n.Heading):
            continue
        text = " ".join(n.plain_text(node.children).split()).lower()
        del parents[node.level - 1 :]
        key = (tuple(parents), node.level, text)
        if text and key in seen:
            issues.append(
                LintIssue(
                    file, node.line, RULE_DUPLICATE_HEADING, "Structure",
                    f"Heading '{n.plain_text(node.children).strip()}' repeats the one on line {seen[key]} in the same section.",
                    suggestion="Give it a distinct title",
                )
            )  # fmt: skip
        seen.setdefault(key, node.line)
        parents += [""] * (node.level - 1 - len(parents)) + [text]
    return issues


def unclosed_fences(file: Path, document: n.Document, config: LintConfig) -> list[LintIssue]:
    """A code fence that is never closed, so the rest of the file becomes code."""
    return [
        LintIssue(
            file,
            node.line,
            RULE_UNCLOSED_FENCE,
            "Structure",
            "Code fence is never closed: the rest of the file is code.",
            suggestion="Close it with the same fence (``` or ~~~) on a line of its own",
        )  # fmt: skip
        for node in n.walk(document)
        if isinstance(node, n.CodeBlock) and node.fenced and not node.closed
    ]


def headings(document: n.Document) -> list[str]:
    return [" ".join(n.plain_text(node.children).split()) for node in n.walk(document) if isinstance(node, n.Heading)]


def required_sections(doc_id: str, files: list[Path], found: list[str], config: LintConfig) -> list[LintIssue]:
    """The headings ``lint.required_sections`` asks of a document (its own list, then ``*``) that none of its
    files has. Matching ignores case and a leading number such as ``2.1``."""
    wanted = config.required_sections.get(doc_id, config.required_sections.get("*", []))
    have = {_bare(text) for text in found}
    return [
        LintIssue(
            files[0],
            1,
            RULE_REQUIRED_SECTION,
            "Structure",
            f"Document '{doc_id}' has no '{section}' section.",
            suggestion=f"Add a heading '{section}'",
        )  # fmt: skip
        for section in wanted
        if _bare(section) not in have
    ]


def _bare(heading: str) -> str:
    return re.sub(r"^[\d.]+\s+", "", heading.strip()).lower()


_HYPHENATED = re.compile(r"(?<![\w-])([A-Za-z]+)-([A-Za-z]{2,})(?![\w-])")  # e-mail, sub-system


def terminology(files: list[tuple[Path, list[Segment]]], config: LintConfig) -> list[LintIssue]:
    """A word written both hyphenated and closed up (e-mail and email, sub-system and subsystem) across the
    files read together. The rarer spelling is reported at each use, with the commoner one suggested."""
    uses: dict[str, dict[str, list[tuple[Path, int]]]] = {}
    joined: dict[str, str] = {}
    for file, segments in files:
        for segment in segments:
            for match in _HYPHENATED.finditer(segment.text):
                key = (match.group(1) + match.group(2)).lower()
                uses.setdefault(key, {}).setdefault(match.group(0), []).append((file, segment.line_at(match.start())))
    if not uses:
        return []
    closed = re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in uses) + r")(?![\w-])", re.IGNORECASE)
    for file, segments in files:
        for segment in segments:
            for match in closed.finditer(segment.text):
                word = match.group(0)
                joined[word.lower()] = joined.get(word.lower(), word)
                uses[word.lower()].setdefault(word, []).append((file, segment.line_at(match.start())))
    issues: list[LintIssue] = []
    for key, spellings in uses.items():
        if key not in joined or len({s.lower() for s in spellings}) < 2:
            continue
        common = max(spellings, key=lambda s: (len(spellings[s]), s == joined[key]))
        for spelling, places in spellings.items():
            if spelling.lower() == common.lower():
                continue
            for file, line in places:
                issues.append(
                    LintIssue(
                        file, line, RULE_TERMINOLOGY, "Terminology",
                        f"'{spelling}' is also written '{common}' in these files.", suggestion=common,
                    )
                )  # fmt: skip
    return issues
