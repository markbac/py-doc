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
from .errors import ConversionError
from .files import find_markdown, is_markdown

logger = logging.getLogger(__name__)


class Converter(Protocol):
    def validate_template(self) -> None: ...

    def convert_file(self, md_path: Path, output_path: Path) -> Path: ...


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
        return 1

    if not pairs:
        logger.warning(f"No Markdown files found in '{input_path}'")
        return 0

    failed = 0
    for src, dst in pairs:
        try:
            converter.convert_file(src, dst)
        except (FileNotFoundError, ConversionError) as exc:
            error(str(exc))
            failed += 1
        except Exception as exc:  # one bad file must not stop the rest of a batch
            logger.debug("Unexpected failure", exc_info=True)
            error(f"Cannot convert '{src}': {type(exc).__name__}: {exc}")
            failed += 1
    if len(pairs) > 1 or failed:
        done = len(pairs) - failed
        summary = f"{done} of {len(pairs)} file(s) converted to {label}" + (f", {failed} failed" if failed else "")
        (logger.error if failed else logger.info)(summary)
    return 1 if failed else 0


def run(parser: argparse.ArgumentParser, make_converter, suffix: str, label: str, argv: Sequence[str] | None) -> int:
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    return convert_all(make_converter(args), args, suffix, label)
