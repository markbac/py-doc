"""The linter: parse Markdown, extract prose, apply the rules, and walk directories."""

from __future__ import annotations

import logging
from pathlib import Path

from py_doc.files import MARKDOWN_SUFFIXES, find_markdown
from py_doc.markdown import ParseError, parse

from . import rules
from .config import RULE_ACRONYM, RULE_GLOSSARY, RULE_REDUNDANT, LintConfig
from .model import FileResult, LintIssue, LintReport
from .text import segments

logger = logging.getLogger(__name__)

_RULES = (
    (RULE_GLOSSARY, rules.glossary),
    (RULE_REDUNDANT, rules.redundant_phrases),
    (RULE_ACRONYM, rules.acronyms),
)


class LintTargetError(Exception):
    """The path to lint does not exist, or is neither a Markdown file nor a directory."""


class DocLinter:
    """Technical writing style and glossary checks for Markdown."""

    def __init__(self, glossary: dict[str, list[str]] | None = None, config: LintConfig | None = None) -> None:
        """Args:
        glossary: Canonical terms and known misspellings. It replaces the built-in glossary.
        config: Full lint policy. ``glossary`` is applied on top of it.
        """
        self.config = config or LintConfig()
        if glossary is not None:
            self.config.glossary = glossary

    def lint_text(self, text: str, file: Path | str = "<text>") -> list[LintIssue]:
        """Lint Markdown text. Raises :class:`py_doc.markdown.ParseError` for unsupported Markdown."""
        file = Path(file)
        prose = segments(parse(text))
        issues: list[LintIssue] = []
        for rule, check in _RULES:
            if rule in self.config.disabled_rules:
                continue
            severity = self.config.severities.get(rule, "warning")
            issues += [
                LintIssue(i.file, i.line, i.rule, i.category, i.message, severity, i.suggestion)
                for i in check(file, prose, self.config)
            ]
        return sorted(issues, key=lambda issue: (issue.line, issue.rule))

    def lint_file(self, path: Path | str) -> FileResult:
        """Lint one file. A file that cannot be read is an error result, never an empty clean one."""
        path = Path(path).resolve()
        try:
            text = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return FileResult(path, error="File not found")
        except UnicodeDecodeError as exc:
            return FileResult(path, error=f"Not valid UTF-8 ({exc.reason})")
        except OSError as exc:
            return FileResult(path, error=f"Cannot read file: {exc.strerror or exc}")
        try:
            issues = self.lint_text(text, path)
        except ParseError as exc:
            return FileResult(path, error=str(exc))
        logger.debug("Linted %s: %d issue(s)", path.name, len(issues))
        return FileResult(path, issues)

    def lint_path(self, target: Path | str) -> LintReport:
        """Lint a Markdown file, or every Markdown file below a directory.

        Raises :class:`LintTargetError` if ``target`` is missing or is not a Markdown file or directory.
        """
        target = Path(target).resolve()
        if target.is_dir():
            return LintReport([self.lint_file(path) for path in self.find_files(target)])
        if target.is_file():
            if target.suffix.lower() not in MARKDOWN_SUFFIXES:
                raise LintTargetError(f"Not a Markdown file (expected .md or .markdown): {target}")
            return LintReport([self.lint_file(target)])
        raise LintTargetError(f"Path not found: {target}")

    def find_files(self, directory: Path) -> list[Path]:
        """Markdown files below ``directory``, skipping hidden and vendor directories, sorted by path."""
        return find_markdown(directory, self.config.exclude_dirs)
