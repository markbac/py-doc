"""The ``py-doclint`` command line."""

from __future__ import annotations

import argparse
import csv
import io
import logging
import sys
from dataclasses import replace
from pathlib import Path

from py_doc._cli import deprecation_notice, safe_console
from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config
from py_doc.errors import ConversionError
from py_doc.runtime import RuntimeSettings, connect

from . import formats
from .config import LintConfig
from .linter import DocLinter, LintTargetError
from .model import FileResult, LintIssue, LintReport

logger = logging.getLogger(__name__)
FORMATS = ("text", "csv", "github", "json", "sarif")
EXAMPLE_RULES = Path(__file__).with_name("examples") / "structure-rules.yaml"
EXAMPLES = """examples:
  py-doc lint                          check every Markdown file below this folder
  py-doc lint docs README.md           check a folder and a file as one report
  py-doc lint docs --strict            exit with status 1 on any warning (for CI)
  py-doc lint docs --format github     annotations for a GitHub Actions run
  py-doc lint docs --format sarif --output lint.sarif   for code scanning
  py-doc lint --check-engines          say whether Vale is installed and used"""


def _display(path: Path) -> Path:
    """The path relative to the working directory when it is inside it, so files can be told apart."""
    try:
        return path.relative_to(Path.cwd())
    except ValueError:
        return path


def _shown(issue: LintIssue) -> LintIssue:
    return replace(issue, file=_display(issue.file))


def run(argv: list[str] | None = None, legacy: bool = False) -> int:
    """Run the linter and return the exit status: 0 clean, 1 issues found, 2 errors."""
    parser = argparse.ArgumentParser(
        prog="py-doclint" if legacy else "py-doc lint",
        description="Check Markdown for writing style, glossary terms, acronyms, structure, links and project conventions",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "targets", nargs="*", default=["."], metavar="TARGET", help="Markdown files or folders to check (default: .)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if any warning or error is reported (info is reported but does not fail)",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="DIR", help="Also skip directories with this name"
    )
    parser.add_argument(
        "--config", metavar="FILE", help="py-doc.yml to read (default: the nearest one above the first target)"
    )
    parser.add_argument(
        "--engine", choices=("auto", "builtin", "vale"), default="auto",
        help="auto runs the built-in rules and Vale when it is installed, builtin skips Vale, vale uses Vale for the text rules",
    )  # fmt: skip
    parser.add_argument(
        "--format", choices=FORMATS, default="text",
        help="text (default), csv for a spreadsheet, github for workflow annotations, json, or sarif for code scanning",
    )  # fmt: skip
    parser.add_argument("--output", metavar="FILE", help="Write the report to this file instead of standard output")
    parser.add_argument(
        "--show-vale-config", action="store_true", help="Print the Vale configuration py-doc would use and exit"
    )
    parser.add_argument(
        "--check-engines", action="store_true", help="Report whether Vale is found, its version and its folder"
    )
    parser.add_argument(
        "--sync", action="store_true", help="Download the Vale packages in lint.vale.packages (vale sync)"
    )
    parser.add_argument(
        "--print-example-rules", action="store_true", help="Print an example set of structure rules and exit"
    )
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    if legacy:
        logger.info(deprecation_notice("py-doclint", "py-doc lint"))

    if args.print_example_rules:
        print(EXAMPLE_RULES.read_text(encoding="utf-8"), end="")
        return 0
    try:
        config, settings = _load_config(args)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    config.exclude_dirs = config.exclude_dirs | frozenset(args.exclude)
    linter = DocLinter(
        config=config,
        runtime=lambda: connect(settings),
        engine=args.engine,
        extra_checks=_model_checks(args, config, settings),
    )
    try:
        if args.show_vale_config or args.check_engines or args.sync:
            return _vale_command(args, linter)
        report = linter.lint_paths(args.targets)
    except (LintTargetError, ConversionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return _print(report, strict=args.strict, fmt=args.format, output=Path(args.output) if args.output else None)


def _model_checks(args: argparse.Namespace, config: LintConfig, settings: RuntimeSettings) -> list:
    """Checks of the Structurizr workspaces the documents use (rules C4001 to C4004), when py-doc.yml names any."""
    path = Path(args.config) if args.config else find_config(Path(args.targets[0]).resolve())
    if path is None:
        return []
    project = load_config(path)
    files = sorted({s.file for d in project.documents.values() for s in d.sources if s.structurizr is not None})
    if not files:
        return []

    def check() -> list[LintIssue]:
        from py_doc.c4.check import check_model
        from py_doc.c4.model import load_workspace
        from py_doc.c4.structurizr import workspace_json
        from py_doc.errors import EnvironmentProblem

        found: list[LintIssue] = []
        box: list = []

        def runtime():
            box[:] = box or [connect(settings)]
            return box[0]

        for file in files:
            try:
                ws = load_workspace(
                    workspace_json(file, project.root / ".py-doc" / "c4" / "json", runtime, project.c4.cli)
                )
            except EnvironmentProblem as exc:
                logger.warning("The model rules for %s were skipped: %s", file.name, exc)
                continue
            found += [
                LintIssue(file.resolve(), 1, i.rule, "C4 model", i.message, i.severity)
                for i in check_model(ws, file, config)
            ]
        return found

    return [check]


def _vale_command(args: argparse.Namespace, linter: DocLinter) -> int:
    from . import vale

    folder = linter.vale_folder()
    target = Path(args.targets[0]).resolve()
    base = target if target.is_dir() else target.parent
    if args.show_vale_config:
        settings = linter.config.vale
        if settings.config is not None:
            print(f"# lint.vale.config is set, so {settings.config} is used as it is")
            print(settings.config.read_text(encoding="utf-8"), end="")
            return 0
        workspace = vale.build_workspace(settings, linter.config, folder)
        print(f"# {workspace.ini}")
        print(workspace.ini.read_text(encoding="utf-8"), end="")
        print("# Rules written: " + ", ".join(workspace.files))
        return 0
    runner = linter.vale_runner(base)
    if args.check_engines:
        print("builtin: available (DOC001 to DOC013)")
        if runner is None:
            print("vale: not used (off, or not installed)")
            print(f"  {vale.INSTALL_HELP}")
            return 0
        version = ".".join(map(str, vale.check_version(runner)))
        print(f"vale: {version} ({type(runner).__name__}), styles in {folder / 'styles'}")
        return 0
    if runner is None:
        raise ConversionError(f"--sync needs Vale. {vale.INSTALL_HELP}")
    ini = vale.build_workspace(linter.config.vale, linter.config, folder).ini
    vale.check_version(runner)
    print(vale.sync(runner, ini) or "Vale packages are up to date")
    return 0


def _load_config(args: argparse.Namespace) -> tuple[LintConfig, RuntimeSettings]:
    """The lint and container settings of the chosen or nearest py-doc.yml, or the built-in ones."""
    if args.config:
        path = Path(args.config)
    else:
        target = Path(args.targets[0]).resolve()
        path = find_config(target if target.is_dir() else target.parent)
    if path is None:
        target = Path(args.targets[0]).resolve()
        return LintConfig(root=target if target.is_dir() else target.parent), RuntimeSettings()
    logger.info(f"Using configuration {path}")
    project = load_config(path)
    return project.lint, project.runtime


def _csv(issues: list[LintIssue]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["file", "line", "column", "severity", "rule", "category", "message", "suggestion"])
    for i in issues:
        writer.writerow([i.file, i.line, i.column or "", i.severity, i.rule, i.category, i.message, i.suggestion or ""])
    return out.getvalue()


def _annotation(issue: LintIssue) -> str:
    """A GitHub Actions workflow command. Info is shown as a notice."""
    level = {"error": "error", "warning": "warning"}.get(issue.severity, "notice")
    escape = lambda text: text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")  # noqa: E731
    properties = f"file={issue.file.as_posix()},line={issue.line}" + (f",col={issue.column}" if issue.column else "")
    properties += f",title={escape(issue.rule).replace(':', '%3A').replace(',', '%2C')}"
    return f"::{level} {properties}::{escape(issue.message)}"


def render(report: LintReport, fmt: str) -> str:
    """The issues of a report in one of FORMATS, paths relative to the working folder."""
    shown = [_shown(issue) for issue in report.issues]
    errors = [replace(result, file=_display(result.file)) for result in report.errors]
    if fmt == "csv":
        return _csv(shown)
    if fmt == "json":
        return formats.to_json(report, shown, errors)
    if fmt == "sarif":
        return formats.to_sarif(shown, errors)
    return "".join(f"{_annotation(issue) if fmt == 'github' else issue}\n" for issue in shown)


def exit_status(report: LintReport, strict: bool) -> int:
    if report.errors:
        return 2
    if report.count("error"):
        return 1  # an issue the configuration calls an error always fails
    return 1 if strict and report.count("warning") else 0


def _print(report: LintReport, strict: bool, fmt: str = "text", output: Path | None = None) -> int:
    text = render(report, fmt)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    for result in report.errors:
        _error(result)
    failing = report.count("warning")
    machine = fmt in ("csv", "json", "sarif") and output is None  # keep standard output parseable
    print(
        f"\n[SUMMARY] Scanned {report.files_scanned} file(s): {len(report.issues)} issue(s) reported"
        f" ({failing} warning or error), {len(report.errors)} file(s) could not be linted.",
        file=sys.stderr if machine else sys.stdout,
    )
    return exit_status(report, strict)


def _error(result: FileResult) -> None:
    print(f"Error: {_display(result.file)}: {result.error}", file=sys.stderr)


def main() -> None:
    safe_console()
    sys.exit(run(legacy=True))


if __name__ == "__main__":
    main()
