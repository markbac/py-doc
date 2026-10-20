"""``py-doc poster``: one self-contained HTML poster from a Markdown file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config
from py_doc.errors import ConversionError, exit_status
from py_doc.poster import build
from py_doc.runtime import RuntimeSettings, connect

POSTER_EXAMPLES = """examples:
  py-doc poster g460.md                 writes g460.html
  py-doc poster g460.md -o out.html

The conventions (front matter, sections, cards, lcd, segments, flow, lanes) are in docs/guide/12_posters.md."""


def run_poster(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc poster", description="Build a self-contained HTML poster from a Markdown file",
        epilog=POSTER_EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("markdown_file")
    parser.add_argument("-o", "--output", help="Output path (default: the input name with .html)")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)

    source = Path(args.markdown_file)
    if not source.is_file():
        print(f"Error: {source} not found", file=sys.stderr)
        return 1
    out = Path(args.output) if args.output else source.with_suffix(".html")
    try:
        config = find_config(source.resolve().parent)
        settings = load_config(config).runtime if config else RuntimeSettings()
        page, ctx = build(source, lambda: connect(settings))
    except (ConfigError, ConversionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({ctx.n} diagrams, {ctx.failed} failed)")
    return 0
