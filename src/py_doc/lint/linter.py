"""The linter: parse Markdown, extract prose, apply the rules, and walk directories."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from collections.abc import Callable

from py_doc import directives
from py_doc.runtime import Runtime
from py_doc.errors import ConversionError
from py_doc.files import MARKDOWN_SUFFIXES, find_markdown
from py_doc.markdown import ParseError, parse

from . import rules, structure, vale
from .config import (
    RULE_ACRONYM, RULE_BROKEN_LINK, RULE_DIRECTIVE, RULE_DUPLICATE_HEADING, RULE_GLOSSARY, RULE_HEADING_JUMP,
    RULE_HEADING_LENGTH, RULE_IMAGE_ALT, RULE_REDUNDANT, RULE_REQUIRED_SECTION, RULE_SENTENCE_LENGTH, RULE_TERMINOLOGY,
    RULE_UNCLOSED_FENCE, LintConfig,
)  # fmt: skip
from .mdlint import run_markdownlint
from .model import FileResult, LintIssue, LintReport
from .text import segments

# Not for a poster: it has no room to spell out every acronym, and its short, direct sentences are on purpose
POSTER_QUIET = frozenset({RULE_ACRONYM, "PyDoc.Acronyms", "PyDoc.PassiveVoice"})

logger = logging.getLogger(__name__)

# Text rules: Vale replaces them when it is the engine.
_RULES = (
    (RULE_GLOSSARY, rules.glossary),
    (RULE_REDUNDANT, rules.redundant_phrases),
    (RULE_ACRONYM, rules.acronyms),
)
# Rules of the parsed document (or, for sentence length, its prose) that run whatever the engine.
_DOCUMENT_RULES = (
    (RULE_HEADING_JUMP, rules.heading_jumps, False),
    (RULE_BROKEN_LINK, rules.broken_links, False),
    (RULE_IMAGE_ALT, rules.image_alt, False),
    (RULE_SENTENCE_LENGTH, rules.sentence_length, True),
    (RULE_HEADING_LENGTH, rules.heading_length, False),
    (RULE_DUPLICATE_HEADING, rules.duplicate_headings, False),
    (RULE_UNCLOSED_FENCE, rules.unclosed_fences, False),
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
        engine: str = "auto",
        extra_checks: list[Callable[[], list[LintIssue]]] | None = None,
    ) -> None:
        """Args:
        glossary: Canonical terms and known misspellings. It replaces the built-in glossary.
        config: Full lint policy. ``glossary`` is applied on top of it.
        runtime: Returns the tool container, for markdownlint and Vale. It is called only when one of them needs it.
        engine: ``builtin`` (no Vale), ``vale`` (Vale in place of the DOC001 to DOC003 text rules) or ``auto``
            (both, when Vale is installed).
        """
        self.runtime = runtime
        self.engine = engine
        self.extra_checks = list(extra_checks or [])  # checks of things other than Markdown, such as a Structurizr model
        self.config = config or LintConfig()
        if glossary is not None:
            self.config.glossary = glossary

    def lint_text(self, text: str, file: Path | str = "<text>") -> list[LintIssue]:
        """Lint Markdown text. Raises :class:`py_doc.markdown.ParseError` for unsupported Markdown."""
        file = Path(file)
        document = parse(text)
        prose = segments(document)
        found: list[LintIssue] = []
        for rule, check in _RULES:
            if rule in self.config.disabled_rules or self.engine == "vale":
                continue
            if rule == RULE_ACRONYM and self._acronyms_by_document:
                continue  # read over the whole document by lint_paths
            found += check(file, prose, self.config)
        for rule, check, reads_prose in _DOCUMENT_RULES:
            if rule not in self.config.disabled_rules:
                found += check(file, prose if reads_prose else document, self.config)
        issues = [self._graded(issue) for issue in found]
        if RULE_DIRECTIVE not in self.config.disabled_rules:
            severity = self.config.severities.get(RULE_DIRECTIVE, "error")
            issues += [
                LintIssue(file, p.line, RULE_DIRECTIVE, "Directive", p.message, severity)
                for p in directives.check(text, file)
            ]
        if file.resolve() not in self.config.posters:  # captions and the like are document conventions, not a poster's
            issues += structure.check_file(file, text, self.config.structure)
        return sorted(issues, key=lambda issue: (issue.line, issue.rule))

    @property
    def _acronyms_by_document(self) -> bool:
        return self.config.acronym_scope == "document" and bool(self.config.documents)

    def _graded(self, issue: LintIssue) -> LintIssue:
        """The issue at the severity the configuration gives its rule."""
        severity = self.config.severities.get(issue.rule, "warning")
        return LintIssue(issue.file, issue.line, issue.rule, issue.category, issue.message, severity, issue.suggestion)

    def _parsed(self, file: Path):
        """The document tree of a file, or None when it cannot be read or parsed (its own result says why)."""
        try:
            return parse(file.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ParseError):
            return None

    def _required_sections(self, report: LintReport) -> None:
        """``lint.required_sections``, over all the files of each document that has a scanned file."""
        if not self.config.required_sections or RULE_REQUIRED_SECTION in self.config.disabled_rules:
            return
        scanned = {result.file for result in report.results}
        found: list[LintIssue] = []
        for doc_id, sources in self.config.documents.items():
            files = [s.resolve() for s in sources if s.exists()]
            if not files or not scanned.intersection(files):
                continue
            titles = [title for file in files if (tree := self._parsed(file)) is not None for title in rules.headings(tree)]
            found += rules.required_sections(doc_id, files, titles, self.config)
        report.add([self._graded(issue) for issue in found])

    def _terminology(self, report: LintReport) -> None:
        """One spelling of each hyphenated word over every file linted together."""
        if RULE_TERMINOLOGY in self.config.disabled_rules:
            return
        prose = [(r.file, segments(tree)) for r in report.results if r.error is None and (tree := self._parsed(r.file)) is not None]
        report.add([self._graded(issue) for issue in rules.terminology(prose, self.config)])

    def _document_acronyms(self, report: LintReport) -> None:
        """With ``lint.acronyms.scope: document``, read acronyms over each document's files in order.

        A file in no document is read on its own. A file in several documents is reported from the first.
        """
        if not self._acronyms_by_document or RULE_ACRONYM in self.config.disabled_rules or self.engine == "vale":
            return
        scanned = {result.file: result for result in report.results if result.error is None}
        done: set[Path] = set()
        found: list[LintIssue] = []
        groups = [[s.resolve() for s in sources] for sources in self.config.documents.values()]
        groups += [[file] for file in scanned if not any(file in group for group in groups)]
        for group in groups:
            files = [file for file in group if file.is_file()]
            if not any(file in scanned for file in files):
                continue
            prose = []
            for file in files:
                try:
                    prose.append((file, segments(parse(file.read_text(encoding="utf-8-sig")))))
                except (OSError, UnicodeDecodeError, ParseError):
                    continue  # reported by the file's own result, or not a file being linted
            found += [i for i in rules.acronyms_across(prose, self.config) if i.file in scanned and i.file not in done]
            done.update(files)
        report.add([self._graded(issue) for issue in dict.fromkeys(found)])

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
        return self.lint_paths([target])

    def lint_paths(self, targets: list[Path | str]) -> LintReport:
        """Lint every Markdown file named or below a named directory, each once, as one report.

        Raises :class:`LintTargetError` naming the first target that is missing or not Markdown.
        """
        resolved = [Path(target).resolve() for target in targets]
        files: list[Path] = []
        for target in resolved:
            if target.is_dir():
                files += self.find_files(target)
            elif target.is_file():
                if target.suffix.lower() not in MARKDOWN_SUFFIXES:
                    raise LintTargetError(f"Not a Markdown file (expected .md or .markdown): {target}")
                files.append(target)
            else:
                raise LintTargetError(f"Path not found: {target}")
        report = LintReport([self.lint_file(path) for path in dict.fromkeys(files)])
        folders = [target if target.is_dir() else target.parent for target in resolved]
        self._whole_document_rules(report)
        self._document_acronyms(report)
        self._required_sections(report)
        self._terminology(report)
        self._markdownlint(report)
        try:
            base = Path(os.path.commonpath(folders))
        except ValueError:  # on different drives (Windows)
            base = folders[0]
        self._vale(report, base)
        for check in self.extra_checks:
            report.add(check())
        for result in report.results:
            if result.file in self.config.posters:
                result.issues = [issue for issue in result.issues if issue.rule not in POSTER_QUIET]
        return report

    def vale_folder(self) -> Path:
        return self.config.vale.managed_dir or self.config.root / ".py-doc" / "vale"

    def vale_runner(self, base: Path):
        """The runner for Vale, or None when Vale is off or absent in ``auto`` mode. Raises when it is required."""
        return vale.make_runner(self.config.vale, self.engine, self.vale_folder(), base, self.runtime)

    def _vale(self, report: LintReport, target: Path) -> None:
        base = target if target.is_dir() else target.parent
        runner = self.vale_runner(base)
        if runner is None:
            return
        settings = self.config.vale
        files = [result.file for result in report.results if result.error is None]
        try:
            if settings.config is not None:
                logger.info("Using %s as it is: lint.vale rules, terms and avoid patterns are not applied", settings.config)
                ini = settings.config
            else:
                ini = vale.build_workspace(settings, self.config, self.vale_folder()).ini
                absent = vale.missing_packages(settings, self.vale_folder())
                if absent:
                    raise ConversionError(f"Vale packages not downloaded: {', '.join(absent)}. Run `py-doc lint --sync`.")
            found = vale.run_vale(files, runner, ini, settings, Path.cwd())
        except vale.ValeError as exc:  # a broken run is an error on every file, never a clean result
            for result in report.results:
                if result.error is None:
                    result.error = str(exc)
            return
        builtin = report.issues
        report.add(vale.drop_duplicates(found, builtin))

    def _whole_document_rules(self, report: LintReport) -> None:
        """Rules that read all of a document's files: missing sources and ``#anchor`` links."""
        if not self.config.structure:
            return
        scanned = {result.file for result in report.results}
        found: set[LintIssue] = set()
        for sources in self.config.documents.values():
            # A generator's output that is not written yet is not a missing source
            sources = [s for s in sources if s.exists() or s.resolve() not in self.config.generated]
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
