"""``py-doc template check`` and ``py-doc template show``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._logging import configure_logging
from .errors import ConversionError
from .template_check import LEVELS, check_template, inventory, kind_of

def _error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc template", description="Check and inspect Word and PowerPoint templates")
    commands = parser.add_subparsers(dest="action", metavar="action", required=True)
    for name, help_text in (("check", "Report what a template lacks for the pandoc pipeline"), ("show", "List its styles or layouts")):
        sub = commands.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("template", type=Path, help="A .docx, .dotx, .pptx or .potx file")
        noise = sub.add_mutually_exclusive_group()
        noise.add_argument("-q", "--quiet", action="store_true", help="Only warnings and errors")
        noise.add_argument("-v", "--verbose", action="store_true", help="Also show INFO findings")
        if name == "check":
            sub.add_argument("--strict", action="store_true", help="Exit with status 1 for warnings as well as failures")
    return parser


def _table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> str:
    rows = [headers, *rows]
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows)


def run_template(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 fine, 1 failures found (or warnings with --strict), 2 the file cannot be read."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        kind = kind_of(args.template)
        if args.action == "show":
            headers = ("Type", "Style", "Bold", "Next") if kind == "word" else ("Layout", "Placeholders")
            print(_table(inventory(args.template), headers))
            return 0
        report = check_template(args.template)
    except (FileNotFoundError, ConversionError) as exc:
        _error(str(exc))
        return 2
    shown = LEVELS if args.verbose else LEVELS[:2]
    for level in shown:
        for finding in (f for f in report.findings if f.level == level):
            print(f"{level:<5} {finding.check}: {finding.message}")
    print(f"{args.template}: {len(report.failures)} failure(s), {len(report.warnings)} warning(s)")
    return 1 if report.failures or (args.strict and report.warnings) else 0
