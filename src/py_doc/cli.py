"""The ``py-doc2docx`` command line."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._cli import add_common_options, deprecation_notice, run, safe_console
from .errors import ConversionError
from .convert import DocxConverter

__all__ = ["ConversionError", "build_parser", "main", "run_docx"]


EXAMPLES = """examples:
  py-doc docx guide.md                        guide.docx next to it (or -o FILE)
  py-doc docx guide.md -t Template.docx       with a Word template
  py-doc docx docs -o build                   every Markdown file in docs, into build/"""


def build_parser(prog: str = "py-doc docx") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Convert Markdown technical documentation to Word (.docx) documents",
    )
    add_common_options(parser, "Word", ".docx")
    parser.add_argument("-t", "--template", type=str, help="Optional reference Word (.docx or .dotx) template")
    return parser


def run_docx(argv: Sequence[str] | None = None, legacy: bool = False) -> int:
    """Run the command and return its exit status instead of exiting. ``legacy`` adds the rename notice."""
    return run(
        build_parser("py-doc2docx" if legacy else "py-doc docx"),
        lambda args: DocxConverter(
            template_path=Path(args.template) if args.template else None,
            allow_missing_template=args.allow_missing_template,
        ),
        ".docx",
        "Word",
        argv,
        deprecation_notice("py-doc2docx", "py-doc docx") if legacy else None,
    )


def main() -> None:
    safe_console()
    code = run_docx(legacy=True)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
