"""The ``py-doc2slides`` command line."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._cli import add_common_options, deprecation_notice, run, safe_console
from .convert import SlidesConverter


EXAMPLES = """examples:
  py-doc slides talk.md                       talk.pptx next to it (or -o FILE)
  py-doc slides talk.md -t Template.pptx      with a PowerPoint template
  py-doc slides talk.md --split-level 1       a new slide only at each # heading
  py-doc slides talk.md --watch               live HTML twin preview in the browser on every save"""


def build_parser(prog: str = "py-doc slides") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Convert Markdown to PowerPoint (.pptx) presentations",
    )
    add_common_options(parser, "PowerPoint", ".pptx")
    parser.add_argument(
        "-t",
        "--template",
        "-r",
        "--reference",
        dest="template",
        type=str,
        help="Optional reference PowerPoint (.pptx or .potx) template (-r/--reference is the old name)",
    )
    parser.add_argument(
        "--split-level",
        type=int,
        choices=range(1, 7),
        default=2,
        metavar="N",
        help="Start a new slide at each heading up to this level, 1 to 6 (default: 2)",
    )
    return parser


def run_slides(argv: Sequence[str] | None = None, legacy: bool = False) -> int:
    """Run the command and return its exit status instead of exiting. ``legacy`` adds the rename notice."""
    return run(
        build_parser("py-doc2slides" if legacy else "py-doc slides"),
        lambda args: SlidesConverter(
            template_path=Path(args.template) if args.template else None,
            allow_missing_template=args.allow_missing_template,
            split_level=args.split_level,
        ),
        ".pptx",
        "PowerPoint",
        argv,
        deprecation_notice("py-doc2slides", "py-doc slides") if legacy else None,
    )


def main() -> None:
    safe_console()
    code = run_slides(legacy=True)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
