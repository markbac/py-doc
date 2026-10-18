"""``py-doc generate``: run the content generators of py-doc.yml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config

from .registry import GeneratorError, available, run_generators

EXAMPLES = """examples:
  py-doc generate               every generator in content.generators
  py-doc generate glossary      only the generator called glossary
  py-doc generate --list        the generators of py-doc.yml and every type that can be used"""


def run_generate(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc generate", description="Write the Markdown that content.generators in py-doc.yml makes",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("names", nargs="*", metavar="NAME", help="Generators to run (default: all)")
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    parser.add_argument("--list", action="store_true", help="List the generators and the types, and run nothing")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    path = Path(args.config) if args.config else find_config(Path.cwd())
    if path is None:
        print("Error: No py-doc.yml found here or in a parent folder", file=sys.stderr)
        return 2
    try:
        project = load_config(path)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    if args.list:
        for spec in project.generators:
            print(f"{spec.name:<20} {spec.type:<14} {spec.output}")
        print("types: " + ", ".join(sorted(available())) + ", python")
        return 0
    if not project.generators:
        print("py-doc.yml has no content.generators: nothing to generate")
        return 0
    try:
        changed = run_generators(project, args.names or None)
    except GeneratorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    count = len(args.names) if args.names else len(project.generators)
    print(f"{count} generator(s) run, {len(changed)} file(s) changed")
    return 0
