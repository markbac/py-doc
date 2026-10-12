"""``py-doc import``: Word to Markdown."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._logging import configure_logging
from .docx_import import InvalidDocx, import_docx
from .errors import ConversionError, exit_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc import", description="Convert a Word document (.docx) to Markdown")
    parser.add_argument("input", type=Path, help="The .docx file")
    parser.add_argument("-o", "--output", type=Path, help="Folder for the .md file and its media folder (default: next to the .docx)")
    parser.add_argument("--force", action="store_true", help="Replace an existing .md file")
    parser.add_argument("--no-defloat-images", action="store_true", help="Leave floating pictures out instead of placing them inline")
    parser.add_argument("--print-output-paths", action="store_true", help="Print where the Markdown and the media went")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    return parser


def run_import(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 done, 1 the file cannot be converted or the output exists, 2 not a Word file or no container."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        result = import_docx(args.input, args.output, defloat_images=not args.no_defloat_images, force=args.force)
    except InvalidDocx as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc)
    if args.print_output_paths:
        print(f"Markdown: {result.markdown}")
        print(f"Media dir: {result.media}")
    return 0
