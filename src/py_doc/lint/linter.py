"""The linter: parse Markdown, extract prose, apply the rules, and walk directories."""

from __future__ import annotations

import logging
from pathlib import Path

from collections.abc import Callable

from py_doc import directives
from py_doc.runtime import Runtime
from py_doc.errors import ConversionError
from py_doc.files import MARKDOWN_SUFFIXES, find_markdown
from py_doc.markdown import ParseError, parse

from . import rules, structure
from .config import RULE_ACRONYM, RULE_DIRECTIVE, RULE_GLOSSARY, RULE_REDUNDANT, LintConfig
from .mdlint import run_markdownlint
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

    def __init__(
        self,
        glossary: dict[str, list[str]] | None = None,
        config: LintConfig | None = None,
        runtime: Callable[[], Runtime] | None = None,
    ) -> None:
        """Args:
        glossary: Canonical terms and known misspellings. It replaces the built-in glossary.
        config: Full lint policy. ``glossary`` is applied on top of it.
        runtime: Returns the tool container, for markdownlint. It is only called when markdownlint is configured.
        """
        self.runtime = runtime
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
        if RULE_DIRECTIVE not in self.config.disabled_rules:
            severity = self.config.severities.get(RULE_DIRECTIVE, "error")
            issues += [
                LintIssue(file, p.line, RULE_DIRECTIVE, "Directive", p.message, severity)
                for p in directives.check(text, file)
            ]
        issues += structure.check_file(file, text, self.config.structure)
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
            report = LintReport([self.lint_file(path) for path in self.find_files(target)])
        elif target.is_file():
            if target.suffix.lower() not in MARKDOWN_SUFFIXES:
                raise LintTargetError(f"Not a Markdown file (expected .md or .markdown): {target}")
            report = LintReport([self.lint_file(target)])
        else:
            raise LintTargetError(f"Path not found: {target}")
        self._whole_document_rules(report)
        self._markdownlint(report)
        return report

    def _whole_document_rules(self, report: LintReport) -> None:
        """Rules that read all of a document's files: missing sources and ``#anchor`` links."""
        if not self.config.structure:
            return
        scanned = {result.file for result in report.results}
        found: set[LintIssue] = set()
        for sources in self.config.documents.values():
            if any(source.resolve() in scanned or not source.exists() for source in sources):
                found.update(structure.check_document([s.resolve() for s in sources], self.config.structure))
        report.add(sorted(found, key=lambda i: (str(i.file), i.line, i.rule)))

    def _markdownlint(self, report: LintReport) -> None:
        settings = self.config.markdownlint
        if settings is None:
            return
        if self.runtime is None:
            raise ConversionError("lint.markdownlint needs the tool container, but no runtime was given")
        files = [result.file for result in report.results if result.error is None]
        report.add(run_markdownlint(files, settings, self.runtime))

    def find_files(self, directory: Path) -> list[Path]:
        """Markdown files below ``directory``, skipping hidden and vendor directories, sorted by path."""
        return find_markdown(directory, self.config.exclude_dirs)
