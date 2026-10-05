"""The ``py-doc`` command: one entry point for converting, building, linting and migrating."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from ._logging import configure_logging
from .build import build_document
from .cli import run_docx
from .config import FORMATS, ConfigError, find_config, load_config
from .errors import ConversionError
from .lint.cli import run as run_lint
from .migrate import LEGACY_FORMATS, Migration, migrate, render
from .slides_cli import run_slides

logger = logging.getLogger(__name__)

# Commands that hand the rest of the command line to the single-purpose tool.
_DELEGATES = {
    "docx": ("Convert Markdown to Word (.docx)", run_docx),
    "slides": ("Convert Markdown to PowerPoint (.pptx)", run_slides),
    "lint": ("Check Markdown for writing style and glossary use", run_lint),
}


def _error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc", description="Markdown technical documentation tools")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="command", required=True)
    for name, (help_text, _) in _DELEGATES.items():
        commands.add_parser(name, help=help_text, add_help=False)

    build = commands.add_parser("build", help="Build the documents described in py-doc.yml")
    build.add_argument("documents", nargs="*", metavar="DOCUMENT", help="Documents to build (default: all)")
    build.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    build.add_argument("-f", "--format", action="append", choices=sorted(FORMATS), help="Build only this format")
    noise = build.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")

    move = commands.add_parser("migrate", help="Create py-doc.yml from legacy build files")
    move.add_argument("paths", nargs="*", default=["."], metavar="PATH", help="Build files or folders to search")
    move.add_argument("-o", "--output", default="py-doc.yml", help="Configuration file to write (default: py-doc.yml)")
    move.add_argument("--from", dest="source", choices=LEGACY_FORMATS, default=LEGACY_FORMATS[0], help="Legacy format")
    move.add_argument("--check", action="store_true", help="Only report what would be migrated")
    move.add_argument("--backup", action="store_true", help="Keep copies (.bak) of the legacy files and any old output")
    move.add_argument("--force", action="store_true", help="Overwrite an existing output file without a backup")
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


def _build(args: argparse.Namespace) -> int:
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    path = Path(args.config) if args.config else find_config(Path.cwd())
    if path is None:
        _error("No py-doc.yml found here or in a parent folder. Use --config, or `py-doc migrate` to create one")
        return 1
    try:
        config = load_config(path)
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

    failed = 0
    names = args.documents or list(config.documents)
    for name in names:
        try:
            build_document(config, config.documents[name], args.format)
        except (FileNotFoundError, ConversionError) as exc:
            _error(f"{name}: {exc}")
            failed += 1
        except Exception as exc:  # one document must not stop the others
            logger.debug("Unexpected failure", exc_info=True)
            _error(f"{name}: {type(exc).__name__}: {exc}")
            failed += 1
    if len(names) > 1 or failed:
        summary = f"{len(names) - failed} of {len(names)} document(s) built" + (f", {failed} failed" if failed else "")
        (logger.error if failed else logger.info)(summary)
    return 1 if failed else 0


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
    configure_logging()
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
    sys.exit(main())
