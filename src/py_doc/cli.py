"""The ``py-doc2docx`` command line."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._cli import add_common_options, deprecation_notice, run
from .errors import ConversionError
from .render.docx import DocxConverter

__all__ = ["ConversionError", "build_parser", "main", "run_docx"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-doc2docx",
        description="Convert Markdown technical documentation to Word (.docx) documents",
    )
    add_common_options(parser, "Word", ".docx")
    parser.add_argument("-t", "--template", type=str, help="Optional reference Word (.docx or .dotx) template")
    parser.add_argument(
        "--keep-template-body",
        action="store_true",
        help="Keep the template's own body content (cover page, placeholder text) and append the converted "
        "document after it (default: remove it)",
    )
    return parser


def run_docx(argv: Sequence[str] | None = None, legacy: bool = False) -> int:
    """Run the command and return its exit status instead of exiting. ``legacy`` adds the rename notice."""
    return run(
        build_parser(),
        lambda args: DocxConverter(
            template_path=Path(args.template) if args.template else None,
            allow_missing_template=args.allow_missing_template,
            keep_template_body=args.keep_template_body,
        ),
        ".docx",
        "Word",
        argv,
        deprecation_notice("py-doc2docx", "py-doc docx") if legacy else None,
    )


def main() -> None:
    code = run_docx(legacy=True)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
