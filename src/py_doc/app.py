"""The ``py-doc`` command: one entry point for converting, building, linting and migrating."""

from __future__ import annotations

import argparse
import contextlib
import functools
import logging
import os
import shutil
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from ._cli import safe_console
from ._logging import configure_logging
from .build import build_document
from .cli import run_docx
from .config import FORMATS, ConfigError, find_config, load_config, parse_config
from .errors import ConversionError, exit_status
from .generators import GeneratorError, run_generators
from .lint.cli import run as run_lint
from .migrate import LEGACY_FORMATS, Migration, migrate, render
from .report import BuildReport
from .runtime import connect
from .slides_cli import run_slides
from .analysis.cli import run_check, run_diff, run_stats
from .c4.cli import run_c4
from .generators.cli import run_generate
from .import_cli import run_import
from .init import run_init
from .new import run_new
from .poster_cli import run_poster
from .site.cli import run_site
from .template_cli import run_template
from .tools_cli import run_doctor, run_setup, run_tools

logger = logging.getLogger(__name__)

# Commands that hand the rest of the command line to the single-purpose tool.
_DELEGATES = {
    "init": ("Start a documentation project: py-doc.yml, a first document and more", run_init),
    "new": ("Start a document here in the legacy format, with the next number from doc-numbers.yml", run_new),
    "docx": ("Convert Markdown to Word (.docx)", run_docx),
    "slides": ("Convert Markdown to PowerPoint (.pptx)", run_slides),
    "lint": ("Check the writing, structure and links of Markdown", run_lint),
    "tools": ("Build and inspect the tool container image", run_tools),
    "c4": ("Check, export and draw Structurizr workspaces", run_c4),
    "import": ("Convert a Word (.docx) or PowerPoint (.pptx) file to Markdown", run_import),
    "template": ("Check and inspect Word and PowerPoint templates", run_template),
    "site": ("Make and build a web site of the documents (MkDocs or Astro + Starlight)", run_site),
    "generate": ("Write the Markdown that content.generators makes", run_generate),
    "check": ("Check a project without building it: py-doc.yml, sources, templates and lint", run_check),
    "stats": ("Count the words, headings, tables, pictures and links of documents", run_stats),
    "diff": ("Compare two versions of documents section by section", run_diff),
    "poster": ("Build a self-contained HTML poster from a Markdown file", run_poster),
    "doctor": ("Check that the tool container works", run_doctor),
    "setup": ("Install Docker Engine for the tool runner", run_setup),
}


BUILD_EXAMPLES = """examples:
  py-doc build                               every document in the nearest py-doc.yml
  py-doc build guide -f docx                 only the guide, only as Word
  py-doc build --var version=2.1 --condition audience=staff
  py-doc build --legacy G460-TN-012.yaml     one legacy build file, without py-doc.yml
  py-doc build --lint --site                 generate, lint, build every document, then the site
  py-doc build --strict --lint-report lint.sarif     for CI: warnings fail, issues for code scanning

The pipeline: check py-doc.yml, run content.generators, lint (build.lint or --lint), build the documents and
bundles, build the site (build.site or --site), then check that every output was written."""

MIGRATE_EXAMPLES = """examples:
  py-doc migrate docs --check                report what would be migrated, write nothing
  py-doc migrate docs                        write py-doc.yml from every build file below docs
  py-doc migrate docs --backup               also keep .bak copies of the build files and any old py-doc.yml"""


def _error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-doc",
        description="Markdown technical documentation tools",
        epilog="`py-doc COMMAND --help` describes a command and its options. "
        "The user guide is docs/guide/ in https://github.com/markbac/py-doc",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="command", required=True)
    for name, (help_text, _) in _DELEGATES.items():
        commands.add_parser(name, help=help_text, add_help=False)

    build = commands.add_parser(
        "build",
        help="Build the documents described in py-doc.yml",
        description="Build the documents described in py-doc.yml, or one legacy createdocs build file",
        epilog=BUILD_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    build.add_argument("documents", nargs="*", metavar="DOCUMENT", help="Documents to build (default: all)")
    source = build.add_mutually_exclusive_group()
    source.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    source.add_argument("--legacy", metavar="FILE", help="Build from a legacy createdocs build file instead of py-doc.yml")
    build.add_argument("-f", "--format", action="append", choices=sorted(FORMATS), help="Build only this format")
    build.add_argument("--var", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set a {{variable}}")
    build.add_argument(
        "--condition", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set a [[IF:]] condition"
    )
    build.add_argument("--report", metavar="FILE", help="Write a JSON report of the build (default: reports.path in py-doc.yml)")
    build.add_argument("--timestamps", action="store_true", help="Put the time and the render times in the report")
    build.add_argument("--keep-going", action="store_true", help="Report every broken diagram, not just the first")
    lint = build.add_mutually_exclusive_group()
    lint.add_argument("--lint", dest="lint", action="store_const", const="on", help="Lint the sources first: an error stops the build")
    lint.add_argument("--strict", dest="lint", action="store_const", const="strict", help="Lint the sources first: a warning stops the build too")
    lint.add_argument("--no-lint", dest="lint", action="store_const", const="off", help="Do not lint, whatever build.lint says")
    build.add_argument("--lint-report", metavar="FILE", help="Also write the lint issues to FILE (.sarif, .json or .csv)")
    site = build.add_mutually_exclusive_group()
    site.add_argument("--site", dest="site", action="store_true", default=None, help="Build the site after the documents")
    site.add_argument("--no-site", dest="site", action="store_false", help="Do not build the site, whatever build.site says")
    build.add_argument("--no-generate", action="store_true", help="Do not run content.generators first")
    noise = build.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")

    move = commands.add_parser(
        "migrate",
        help="Create py-doc.yml from legacy build files",
        description="Create py-doc.yml from legacy createdocs build files. The legacy files are never changed",
        epilog=MIGRATE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    move.add_argument("paths", nargs="*", default=["."], metavar="PATH", help="Build files or folders to search")
    move.add_argument("-o", "--output", default="py-doc.yml", help="Configuration file to write (default: py-doc.yml)")
    move.add_argument(
        "--from", dest="source", choices=LEGACY_FORMATS, default=LEGACY_FORMATS[0], help="Legacy format (default: createdocs, the only one)"
    )
    move.add_argument("--check", action="store_true", help="Only report what would be migrated")
    move.add_argument("--backup", action="store_true", help="Keep copies (.bak) of the legacy files and any old output")
    move.add_argument("--force", action="store_true", help="Overwrite an existing output file without a backup")
    move_noise = move.add_mutually_exclusive_group()
    move_noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    move_noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command and return the exit status."""
    args_in = list(sys.argv[1:] if argv is None else argv)
    if args_in and args_in[0] in _DELEGATES:
        return _DELEGATES[args_in[0]][1](args_in[1:])
    args = build_parser().parse_args(args_in)
    if args.command == "build":
        return _build(args)
    return _migrate(args)


# --- build ---------------------------------------------------------------------------------------


def _assignment(text: str) -> tuple[str, str]:
    name, sep, value = text.partition("=")
    if not sep or not name.strip():
        raise argparse.ArgumentTypeError(f"'{text}' is not NAME=VALUE")
    return name.strip(), value


def _conditions(pairs: list[tuple[str, str]]) -> dict:
    """Command line conditions: true and false become booleans, anything else stays text."""
    words = {"true": True, "false": False}
    return {name: words.get(value.lower(), value) for name, value in pairs}


def _load_legacy(path: Path):
    """The configuration ``py-doc migrate`` would write for one createdocs file, without writing it."""
    if not path.is_file():
        raise ConfigError(f"Legacy build file not found: {path}")
    result = migrate([path], path.resolve().parent)
    if not result.migrated:
        raise ConfigError(f"{path} is not a createdocs build file (it needs an 'entries' list of files)")
    for finding in result.findings:
        (logger.warning if finding.level == "warning" else logger.info)(f"{_shown(finding.file)}: {finding.message}")
    return parse_config(result.config, path.resolve().parent)


def _build(args: argparse.Namespace) -> int:
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    path = Path(args.legacy or args.config) if args.legacy or args.config else find_config(Path.cwd())
    if path is None:
        _error("No py-doc.yml found here or in a parent folder. Use --config, --legacy, or `py-doc migrate` to create one")
        return 1
    try:
        config = _load_legacy(path) if args.legacy else load_config(path)
    except ConfigError as exc:
        _error(str(exc))
        return 1
    if not config.documents:
        _error(f"{path} defines no documents")
        return 1
    unknown = [name for name in args.documents if name not in config.documents]
    if unknown:
        _error(f"Unknown document(s): {', '.join(unknown)}. Defined: {', '.join(config.documents)}")
        return 1

    connected = functools.cache(lambda: connect(config.runtime))  # the container is only needed to run a tool
    used: list = []

    def runtime():
        used.append(connected())
        return used[-1]

    report_path = Path(args.report).resolve() if args.report else config.report
    report = BuildReport(config.root, args.timestamps) if report_path else None
    names = args.documents or list(config.documents)
    with report.recording() if report else contextlib.nullcontext():
        status = _pipeline(args, config, names, runtime, report)
    if report:
        report.describe_runtime(used[-1] if used else None)
        try:
            logger.info(f"Wrote {report.write(report_path)}")
        except OSError as exc:
            _error(f"Cannot write the report {report_path}: {exc.strerror or exc}")
            status = max(status, 1)
    return status


def _pipeline(args: argparse.Namespace, config, names: list[str], runtime, report: BuildReport | None) -> int:
    """Generate, lint, build the documents and bundles, build the site, then check the outputs.

    A failed stage stops the ones after it, except that every document is tried. Returns the exit status.
    """

    def step(name: str, state: str, detail: str = "") -> None:
        if report:
            report.step(name, state, detail)

    # 1. content generators: their files are sources, so they come before anything reads the sources
    if config.generators and config.build.generate and not args.no_generate:
        try:
            changed = run_generators(config)
        except GeneratorError as exc:
            _error(str(exc))
            step("generate", "failed", str(exc))
            return 1
        step("generate", "ok", f"{len(config.generators)} generator(s), {len(changed)} file(s) changed")

    # 2. lint the sources of the documents being built
    lint_mode = args.lint or config.build.lint
    lint_report = Path(args.lint_report).resolve() if args.lint_report else config.build.lint_report
    if lint_mode != "off":
        status = _lint_sources(config, names, lint_mode, lint_report, runtime)
        step("lint", "failed" if status else "ok")
        if status:
            _error("Lint found problems, so nothing was built. Fix them, or build with --no-lint")
            return status
    else:
        step("lint", "skipped")

    # 3. the documents, bundles included: one failure does not stop the others
    failed = 0
    status = 0
    written: list[Path] = []
    for name in names:
        try:
            written += build_document(
                config, config.documents[name], args.format, dict(args.var), _conditions(args.condition), runtime,
                args.keep_going, report,
            ) or []
        except (FileNotFoundError, ConversionError) as exc:
            _error(f"{name}: {exc}")
            failed += 1
            status = max(status, exit_status(exc))
            if report:
                report.failed(name, exc)
        except Exception as exc:  # one document must not stop the others
            logger.debug("Unexpected failure", exc_info=True)
            _error(f"{name}: {type(exc).__name__}: {exc}")
            failed += 1
            status = max(status, 1)
            if report:
                report.failed(name, exc)
    if len(names) > 1 or failed:
        summary = f"{len(names) - failed} of {len(names)} document(s) built" + (f", {failed} failed" if failed else "")
        (logger.error if failed else logger.info)(summary)
    step("documents", "failed" if failed else "ok", f"{len(names) - failed} of {len(names)} built")
    if failed:
        return status

    # 4. the site, from the same sources
    want_site = config.build.site if args.site is None else args.site
    if want_site:
        if config.site is None:
            _error("A site build was asked for, but py-doc.yml has no site section")
            step("site", "failed", "no site section")
            return 1
        try:
            from .site.pages import generate_site

            engine, _ = generate_site(config, runtime, dict(args.var), _conditions(args.condition))
            for _, config_file in config.site.targets.items() or [(None, None)]:
                logger.info(f"Built the site in {engine.build(runtime(), config_file)}")
        except (ConversionError, FileNotFoundError) as exc:
            _error(f"site: {exc}")
            step("site", "failed", str(exc))
            return exit_status(exc) if isinstance(exc, ConversionError) else 1
        step("site", "ok")

    # 5. every output is there and not empty
    missing = [path for path in written if not path.is_file() or path.stat().st_size == 0]
    for path in missing:
        _error(f"{_shown(path)} was not written, or is empty")
    step("verify", "failed" if missing else "ok", f"{len(written) - len(missing)} of {len(written)} output(s)")
    return 1 if missing else 0


def _lint_sources(config, names: list[str], mode: str, output: Path | None, runtime) -> int:
    """Lint every source of the documents (bundles: of theirs). Prints the issues; returns the lint exit status."""
    from .lint import DocLinter
    from .lint.cli import exit_status as lint_status
    from .lint.cli import render as render_lint
    from .lint.linter import LintTargetError

    files = sorted({
        s.file.resolve() for name in names for s in config.documents[name].sources
        if s.include and s.structurizr is None and s.file.suffix.lower() in (".md", ".markdown") and s.file.exists()
    })  # fmt: skip
    if not files:
        return 0
    try:
        lint = DocLinter(config=config.lint, runtime=runtime).lint_paths(files)
    except (LintTargetError, ConversionError) as exc:
        _error(str(exc))
        return 2
    print(render_lint(lint, "text"), end="")
    if output is not None:
        fmt = {".sarif": "sarif", ".json": "json", ".csv": "csv"}.get(output.suffix.lower())
        if fmt is None:
            _error(f"{output} must end in .sarif, .json or .csv, which says its format")
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_lint(lint, fmt), encoding="utf-8")
        logger.info(f"Wrote the lint issues to {output}")
    for result in lint.errors:
        _error(f"{_shown(result.file)}: {result.error}")
    logger.info(f"Lint: {len(lint.issues)} issue(s) in {lint.files_scanned} file(s), {lint.count('warning')} warning or error")
    return lint_status(lint, mode == "strict")


# --- migrate -------------------------------------------------------------------------------------


def _backup(path: Path) -> Path:
    """Copy ``path`` to the first free ``.bak`` name and return it."""
    target = path.with_name(path.name + ".bak")
    number = 2
    while target.exists():
        target = path.with_name(f"{path.name}.bak{number}")
        number += 1
    shutil.copy2(path, target)
    return target


def _shown(path: Path) -> str:
    try:
        return Path(os.path.relpath(path)).as_posix()
    except ValueError:  # another drive on Windows
        return path.as_posix()


def _report(result: Migration) -> None:
    for legacy, doc_id in result.migrated:
        print(f"migrated  {_shown(legacy)} -> documents.{doc_id}")
    for path in result.skipped:
        print(f"skipped   {_shown(path)} (not a createdocs build file)")
    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for finding in result.findings:
        grouped[(finding.level, finding.message)].append(finding.file)
    for (level, message), files in grouped.items():
        if len(files) == 1:
            print(f"{level:<9} {_shown(files[0])}: {message}")
        else:
            shown = ", ".join(_shown(f) for f in files[:3]) + (", ..." if len(files) > 3 else "")
            print(f"{level:<9} {len(files)} files: {message} ({shown})")


def _migrate(args: argparse.Namespace) -> int:
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        _error(f"Path not found: {missing[0]}")
        return 1
    output = Path(args.output).resolve()
    try:
        result = migrate(paths, output.parent, args.source)
    except ConfigError as exc:  # the generated file did not load: a bug, reported rather than written
        _error(f"Cannot create a valid configuration: {exc}")
        return 1
    _report(result)
    if not result.migrated:
        _error(f"No {args.source} build files found")
        return 1
    warnings = sum(1 for f in result.findings if f.level == "warning")
    print(f"\n{len(result.migrated)} build file(s) found, {len(result.skipped)} skipped, {warnings} warning(s)")
    if args.check:
        print("Check only: nothing was written")
        return 0

    if output.exists():
        if args.backup:
            print(f"backup    {_shown(_backup(output))}")
        elif not args.force:
            _error(f"{_shown(output)} already exists. Use --backup to keep a copy or --force to replace it")
            return 1
    if args.backup:
        for legacy, _ in result.migrated:
            print(f"backup    {_shown(_backup(legacy))}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(result.config), encoding="utf-8")
    print(f"written   {_shown(output)}")
    return 0


def run() -> None:
    safe_console()
    sys.exit(main())
