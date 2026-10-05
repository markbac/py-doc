"""The ``py-doclint`` command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py_doc._logging import configure_logging

from .config import DEFAULT_EXCLUDE_DIRS, LintConfig
from .linter import DocLinter, LintTargetError
from .model import FileResult, LintIssue, LintReport


def _display(path: Path) -> Path:
    """The path relative to the working directory when it is inside it, so files can be told apart."""
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def _shown(issue: LintIssue) -> LintIssue:
    return LintIssue(
        _display(issue.file), issue.line, issue.rule, issue.category, issue.message, issue.severity, issue.suggestion
    )


def run(argv: list[str] | None = None) -> int:
    """Run the linter and return the exit status: 0 clean, 1 issues found with --strict, 2 errors."""
    parser = argparse.ArgumentParser(
        prog="py-doclint", description="Technical writing style and glossary checks for Markdown"
    )
    parser.add_argument("target", nargs="?", default=".", help="Markdown file or documentation directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if any warning or error is reported (info is reported but does not fail)",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="DIR", help="Also skip directories with this name"
    )
    args = parser.parse_args(argv)
    configure_logging()

    config = LintConfig(exclude_dirs=DEFAULT_EXCLUDE_DIRS | frozenset(args.exclude))
    try:
        report = DocLinter(config=config).lint_path(args.target)
    except LintTargetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return _print(report, strict=args.strict)


def _print(report: LintReport, strict: bool) -> int:
    for issue in report.issues:
        print(_shown(issue))
    for result in report.errors:
        _error(result)
    failing = report.count("warning")
    print(
        f"\n[SUMMARY] Scanned {report.files_scanned} file(s): {len(report.issues)} issue(s) reported"
        f" ({failing} warning or error), {len(report.errors)} file(s) could not be linted."
    )
    if report.errors:
        return 2
    return 1 if strict and failing else 0


def _error(result: FileResult) -> None:
    print(f"Error: {_display(result.file)}: {result.error}", file=sys.stderr)


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
