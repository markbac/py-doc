"""The ``py-doclint`` command line."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from py_doc._cli import deprecation_notice
from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config

from .config import LintConfig
from .linter import DocLinter, LintTargetError
from .model import FileResult, LintIssue, LintReport

logger = logging.getLogger(__name__)


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


def run(argv: list[str] | None = None, legacy: bool = False) -> int:
    """Run the linter and return the exit status: 0 clean, 1 issues found, 2 errors."""
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
    parser.add_argument("--config", metavar="FILE", help="py-doc.yml to read (default: the nearest one above the target)")
    args = parser.parse_args(argv)
    configure_logging()
    if legacy:
        logger.info(deprecation_notice("py-doclint", "py-doc lint"))

    try:
        config = _load_config(args)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    config.exclude_dirs = config.exclude_dirs | frozenset(args.exclude)
    try:
        report = DocLinter(config=config).lint_path(args.target)
    except LintTargetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return _print(report, strict=args.strict)


def _load_config(args: argparse.Namespace) -> LintConfig:
    """The lint settings of the chosen or nearest py-doc.yml, or the built-in ones."""
    if args.config:
        path = Path(args.config)
    else:
        target = Path(args.target).resolve()
        path = find_config(target if target.is_dir() else target.parent)
    if path is None:
        return LintConfig()
    logger.info(f"Using configuration {path}")
    return load_config(path).lint


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
    if report.count("error"):
        return 1  # an issue the configuration calls an error always fails
    return 1 if strict and failing else 0


def _error(result: FileResult) -> None:
    print(f"Error: {_display(result.file)}: {result.error}", file=sys.stderr)


def main() -> None:
    sys.exit(run(legacy=True))


if __name__ == "__main__":
    main()
