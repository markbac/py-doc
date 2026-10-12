"""The ``py-doclint`` command line."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from py_doc._cli import deprecation_notice
from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config
from py_doc.errors import ConversionError
from py_doc.runtime import RuntimeSettings, connect

from .config import LintConfig
from .linter import DocLinter, LintTargetError
from .model import FileResult, LintIssue, LintReport

logger = logging.getLogger(__name__)
EXAMPLE_RULES = Path(__file__).with_name("examples") / "structure-rules.yaml"


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
    parser.add_argument(
        "--engine", choices=("auto", "builtin", "vale"), default="auto",
        help="auto runs the built-in rules and Vale when it is installed, builtin skips Vale, vale uses Vale for the text rules",
    )  # fmt: skip
    parser.add_argument("--show-vale-config", action="store_true", help="Print the Vale configuration py-doc would use and exit")
    parser.add_argument("--check-engines", action="store_true", help="Report whether Vale is found, its version and its folder")
    parser.add_argument("--sync", action="store_true", help="Download the Vale packages in lint.vale.packages (vale sync)")
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
        config=config, runtime=lambda: connect(settings), engine=args.engine, extra_checks=_model_checks(args, config, settings)
    )
    try:
        if args.show_vale_config or args.check_engines or args.sync:
            return _vale_command(args, linter)
        report = linter.lint_path(args.target)
    except (LintTargetError, ConversionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return _print(report, strict=args.strict)


def _model_checks(args: argparse.Namespace, config: LintConfig, settings: RuntimeSettings) -> list:
    """Checks of the Structurizr workspaces the documents use (rules C4001 to C4004), when py-doc.yml names any."""
    path = Path(args.config) if args.config else find_config(Path(args.target).resolve())
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
                ws = load_workspace(workspace_json(file, project.root / ".py-doc" / "c4" / "json", runtime, project.c4.cli))
            except EnvironmentProblem as exc:
                logger.warning("The model rules for %s were skipped: %s", file.name, exc)
                continue
            found += [
                LintIssue(file.resolve(), 1, i.rule, "C4 model", i.message, i.severity) for i in check_model(ws, file, config)
            ]
        return found

    return [check]


def _vale_command(args: argparse.Namespace, linter: DocLinter) -> int:
    from . import vale

    folder = linter.vale_folder()
    target = Path(args.target).resolve()
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
        print("builtin: available (DOC001 to DOC004)")
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
        target = Path(args.target).resolve()
        path = find_config(target if target.is_dir() else target.parent)
    if path is None:
        target = Path(args.target).resolve()
        return LintConfig(root=target if target.is_dir() else target.parent), RuntimeSettings()
    logger.info(f"Using configuration {path}")
    project = load_config(path)
    return project.lint, project.runtime


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
