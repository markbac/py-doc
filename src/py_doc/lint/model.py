"""Results of linting: issues, per-file results and a report over many files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SEVERITIES = ("error", "warning", "info")
_RANK = {name: rank for rank, name in enumerate(SEVERITIES)}


def at_least(severity: str, threshold: str) -> bool:
    """Whether ``severity`` is as serious as ``threshold`` (error is the most serious)."""
    return _RANK[severity] <= _RANK[threshold]


@dataclass(frozen=True)
class LintIssue:
    file: Path
    line: int
    rule: str  # for example DOC001
    category: str  # Glossary, Style or Acronym
    message: str
    severity: str = "warning"
    suggestion: str | None = None

    def __str__(self) -> str:
        text = f"{self.file}:{self.line}: {self.severity} {self.rule} [{self.category}] {self.message}"
        return f"{text} (suggestion: {self.suggestion})" if self.suggestion else text


@dataclass
class FileResult:
    """The outcome for one file: its issues, or the reason it could not be linted.

    An error is never the same as a clean file, so a missing or unreadable file cannot pass silently.
    """

    file: Path
    issues: list[LintIssue] = field(default_factory=list)
    error: str | None = None


@dataclass
class LintReport:
    """Results for every file that was scanned, clean ones included."""

    results: list[FileResult] = field(default_factory=list)

    @property
    def files_scanned(self) -> int:
        return len(self.results)

    @property
    def issues(self) -> list[LintIssue]:
        return [issue for result in self.results for issue in result.issues]

    @property
    def errors(self) -> list[FileResult]:
        return [result for result in self.results if result.error is not None]

    def add(self, issues: list[LintIssue]) -> None:
        """Put issues from another check with their files, in line order. A file not scanned gets its own result."""
        by_file = {result.file: result for result in self.results}
        for issue in issues:
            result = by_file.get(issue.file)
            if result is None:
                result = by_file[issue.file] = FileResult(issue.file)
                self.results.append(result)
            if issue not in result.issues:
                result.issues.append(issue)
        for result in self.results:
            result.issues.sort(key=lambda i: (i.line, i.rule))

    def count(self, threshold: str = "info") -> int:
        """Number of issues at or above ``threshold``."""
        return sum(1 for issue in self.issues if at_least(issue.severity, threshold))
