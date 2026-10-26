"""The ``py-doc2slides`` command line."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ._cli import add_common_options, deprecation_notice, run, safe_console
from .convert import DeckConverter, SlidesConverter


EXAMPLES = """examples:
  py-doc slides talk.md                       talk.pptx next to it (or -o FILE)
  py-doc slides talk.md -t Template.pptx      with a PowerPoint template
  py-doc slides talk.md --split-level 1       a new slide only at each # heading
  py-doc slides talk.md --watch               build on every save, and show the slides in the browser
  py-doc slides talk.md -f html               talk.html: an HTML deck, for a screen or the web
  py-doc slides talk.md -f html --theme dark --pdf      and talk.pdf, one slide a page

In an HTML deck: arrow keys, space or a click move on, o shows every slide, f is full screen and p opens
the presenter view with the notes, the next slide and a timer."""


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
    parser.add_argument(
        "-f", "--format", choices=("pptx", "html"), default="pptx",
        help="pptx (default): an editable PowerPoint deck; html: a self-contained HTML deck",
    )  # fmt: skip
    deck = parser.add_argument_group("an HTML deck (-f html)")
    deck.add_argument("--theme", help="A poster theme (default, dark, print) or a theme file")
    deck.add_argument("--aspect", choices=("16:9", "4:3"), default="16:9", help="The shape of a slide (default: 16:9)")
    deck.add_argument("--footer", help='The footer of every slide, such as "{title} v{version}"')
    deck.add_argument("--embed-fonts", action="store_true", help="Put the theme's web fonts inside the page")
    deck.add_argument("--pdf", action="store_true", help="Also print it to a PDF beside it, one slide a page")
    return parser


def run_slides(argv: Sequence[str] | None = None, legacy: bool = False) -> int:
    """Run the command and return its exit status instead of exiting. ``legacy`` adds the rename notice."""
    return run(
        build_parser("py-doc2slides" if legacy else "py-doc slides"),
        _converter,
        lambda args: ".html" if args.format == "html" else ".pptx",
        lambda args: "HTML deck" if args.format == "html" else "PowerPoint",
        argv,
        deprecation_notice("py-doc2slides", "py-doc slides") if legacy else None,
    )


def _converter(args):
    if args.format == "html":
        if args.template:
            raise SystemExit("Error: an HTML deck takes --theme, not a PowerPoint --template")
        options = {"aspect": args.aspect, "theme": args.theme, "footer": args.footer,
                   "embed_fonts": args.embed_fonts, "pdf": args.pdf}  # fmt: skip
        return DeckConverter(split_level=args.split_level, **{k: v for k, v in options.items() if v})
    deck_only = [
        f"--{name.replace('_', '-')}" for name in ("theme", "footer", "pdf", "embed_fonts") if getattr(args, name)
    ]
    if deck_only:
        raise SystemExit(f"Error: {deck_only[0]} is for an HTML deck: add -f html")
    return SlidesConverter(
        template_path=Path(args.template) if args.template else None,
        allow_missing_template=args.allow_missing_template,
        split_level=args.split_level,
    )


def main() -> None:
    safe_console()
    code = run_slides(legacy=True)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
