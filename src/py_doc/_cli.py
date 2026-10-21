"""What the converter commands share: options, output paths, batch conversion and exit codes."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from . import __version__
from ._logging import configure_logging
from .errors import ConversionError, OutputLocked, exit_status
from .files import find_markdown, is_markdown

logger = logging.getLogger(__name__)


class Converter(Protocol):
    def validate_template(self) -> None: ...

    def convert_file(self, md_path: Path, output_path: Path) -> Path: ...

    def convert_twin(self, md_path: Path, output_path: Path) -> Path: ...


def safe_console() -> None:
    """Let a character the output's encoding lacks become ``?`` instead of stopping the command.

    On Windows, output sent to a pipe or a file uses the ANSI code page (cp1252 and the like), so an
    emoji or an arrow quoted from a document raised UnicodeEncodeError partway through a lint report.
    A console window, and anything already writing UTF-8, can show every character and is left alone.
    """
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def add_common_options(parser: argparse.ArgumentParser, kind: str, suffix: str) -> None:
    """Add the options both converter commands have. ``kind`` names the output, such as ``Word``."""
    parser.add_argument("input", type=str, help="Input Markdown (.md) file or directory")
    parser.add_argument("-o", "--output", type=str, help=f"Output {kind} ({suffix}) file path or directory")
    parser.add_argument(
        "--allow-missing-template",
        action="store_true",
        help="Use a default blank document with a warning if the template file is not found (default: fail)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Build again on every save, and reload an HTML preview twin in the browser (Ctrl+C stops)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="With --watch, the local port to serve the preview on (default: a free one)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="With --watch, do not open the browser",
    )
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")


def output_for_file(source: Path, output: str | None, suffix: str) -> Path:
    """Where a single file goes: next to it by default, or into ``-o`` when that is a directory."""
    if not output:
        return source.with_suffix(suffix)
    target = Path(output)
    if output.endswith(("/", os.sep)) or target.is_dir():
        return target / source.with_suffix(suffix).name
    return target


def plan_directory(root: Path, output: str | None, suffix: str) -> list[tuple[Path, Path]]:
    """(source, destination) pairs for every Markdown file below ``root``."""
    out_dir = Path(output).resolve() if output else root
    if out_dir.exists() and not out_dir.is_dir():
        raise ConversionError(f"Output '{out_dir}' is a file, but the input is a directory")
    skip = out_dir if out_dir != root and root in out_dir.parents else None
    pairs = [(src, out_dir / src.relative_to(root).with_suffix(suffix)) for src in find_markdown(root, skip=skip)]
    seen: dict[Path, Path] = {}
    for src, dst in pairs:
        if dst in seen:
            raise ConversionError(f"'{seen[dst]}' and '{src}' would both be written to '{dst}'")
        seen[dst] = src
    return pairs


def convert_all(converter: Converter, args: argparse.Namespace, suffix: str, label: str) -> int:
    """Run the conversion the arguments ask for. Returns the exit status: 0, or 1 if anything failed."""
    input_path = Path(args.input).resolve()
    try:
        converter.validate_template()
        if input_path.is_file():
            if not is_markdown(input_path):
                logger.warning(f"'{input_path.name}' does not end in .md or .markdown")
            pairs = [(input_path, output_for_file(input_path, args.output, suffix).resolve())]
        elif input_path.is_dir():
            pairs = plan_directory(input_path, args.output, suffix)
        else:
            error(f"Path not found: {input_path}")
            return 1
    except (FileNotFoundError, ConversionError) as exc:
        error(str(exc))
        return exit_status(exc)

    if not pairs:
        logger.warning(f"No Markdown files found in '{input_path}'")
        return 0

    failed = 0
    status = 0
    for src, dst in pairs:
        try:
            converter.convert_file(src, dst)
        except (FileNotFoundError, ConversionError) as exc:
            error(str(exc))
            failed += 1
            status = max(status, exit_status(exc))
        except Exception as exc:  # one bad file must not stop the rest of a batch
            logger.debug("Unexpected failure", exc_info=True)
            error(f"Cannot convert '{src}': {type(exc).__name__}: {exc}")
            failed += 1
            status = max(status, 1)
    if len(pairs) > 1 or failed:
        done = len(pairs) - failed
        summary = f"{done} of {len(pairs)} file(s) converted to {label}" + (f", {failed} failed" if failed else "")
        (logger.error if failed else logger.info)(summary)
    return status


PREVIEW_DIR = Path(".py-doc") / "preview"  # where --watch writes the HTML twins, below the input folder


def watch_converter(converter: Converter, args: argparse.Namespace, suffix: str, label: str) -> int:
    """Build the documents and an HTML twin of each on every save, and serve the twins with a live reload.

    The twins go to ``.py-doc/preview`` below the input's folder, so no file of the user's is overwritten and
    the folder of documents stays clean. A document open in Word or PowerPoint is left as it is, with a
    warning, and its twin is still built.
    """
    input_path = Path(args.input).resolve()
    try:
        converter.validate_template()
        if input_path.is_file():
            if not is_markdown(input_path):
                logger.warning(f"'{input_path.name}' does not end in .md or .markdown")
            base = input_path.parent
            pairs = [(input_path, output_for_file(input_path, args.output, suffix).resolve())]
        elif input_path.is_dir():
            base = input_path
            pairs = plan_directory(input_path, args.output, suffix)
        else:
            error(f"Path not found: {input_path}")
            return 1
    except (FileNotFoundError, ConversionError) as exc:
        error(str(exc))
        return exit_status(exc)

    if not pairs:
        logger.warning(f"No Markdown files found in '{input_path}'")
        return 0

    sources = {src for src, _ in pairs}
    template_path = getattr(converter, "template_path", None)
    if template_path:
        sources.add(Path(template_path).resolve())

    def build_all() -> tuple[dict[str, Path], set[Path]]:
        pages: dict[str, Path] = {}
        for src, dst in pairs:
            try:
                converter.convert_file(src, dst)
                print(f"wrote {dst}")
            except OutputLocked:
                logger.warning(f"{dst.name} is open in {label}, so it was not written; the preview is up to date")
            name = src.relative_to(base).with_suffix("").as_posix()  # by path, so a/readme and b/readme both show
            pages[name] = converter.convert_twin(src, base / PREVIEW_DIR / f"{name}.html").resolve()
        return pages, sources

    from .poster_watch import watch

    return watch(
        build_all,
        (ConversionError, FileNotFoundError, OSError),
        port=args.port,
        open_browser=not args.no_open,
        title=f"{label} Preview",
    )


def deprecation_notice(old: str, new: str) -> str:
    return (
        f"{old} is now part of py-doc. `{new}` does the same, and `py-doc build` builds every document "
        "from py-doc.yml (`py-doc migrate` creates it). This command keeps working"
    )


def run(
    parser: argparse.ArgumentParser,
    make_converter,
    suffix: str,
    label: str,
    argv: Sequence[str] | None,
    notice: str | None = None,
) -> int:
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    if notice:
        logger.info(notice)
    if args.watch:
        return watch_converter(make_converter(args), args, suffix, label)
    if args.port or args.no_open:
        logger.warning("--port and --no-open only apply with --watch, so they are ignored")
    return convert_all(make_converter(args), args, suffix, label)
