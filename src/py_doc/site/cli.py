"""``py-doc site``: make, fill and build a web site of the documents in py-doc.yml."""

from __future__ import annotations

import argparse
import functools
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import SITE_ENGINES, ConfigError, ProjectConfig, find_config, load_config
from py_doc.errors import ConversionError, exit_status
from py_doc.runtime import connect

from .engines import engine_for
from .pages import generate_site

logger = logging.getLogger(__name__)


def _assignment(text: str) -> tuple[str, str]:
    name, sep, value = text.partition("=")
    if not sep or not name.strip():
        raise argparse.ArgumentTypeError(f"'{text}' is not NAME=VALUE")
    return name.strip(), value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc site", description="A web site of the documents, made with MkDocs or Astro + Starlight")
    actions = parser.add_subparsers(dest="action", metavar="action", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("-c", "--config", help="py-doc.yml to read (default: the nearest one)")
        noise = sub.add_mutually_exclusive_group()
        noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
        noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")

    init = actions.add_parser("init", help="Make the site project (mkdocs.yml, or an Astro + Starlight project) if it is not there")
    common(init)
    init.add_argument("--engine", choices=SITE_ENGINES, help="The site generator (default: site.engine in py-doc.yml)")
    for name, text in (("generate", "Write the pages and the navigation"), ("build", "Write the pages, then build the site in the tool container")):
        sub = actions.add_parser(name, help=text)
        common(sub)
        sub.add_argument("--var", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set a {{variable}}")
        sub.add_argument("--condition", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set an [[IF:]] condition")
    return parser


def _load(args: argparse.Namespace) -> ProjectConfig:
    path = Path(args.config) if args.config else find_config(Path.cwd())
    if path is None:
        raise ConfigError("No py-doc.yml found here or in a parent folder. `py-doc init` makes one")
    return load_config(path)


def run_site(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 done, 1 a page or the site build failed, 2 the machine cannot run the tools."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        config = _load(args)
        if args.action == "init":
            return _init(config, args.engine)
        runtime = functools.cache(lambda: connect(config.runtime))
        words = {"true": True, "false": False}
        conditions = {name: words.get(value.lower(), value) for name, value in args.condition}
        engine, written = generate_site(config, runtime, dict(args.var), conditions)
        print(f"Wrote {len(written)} file(s) in {engine.root}")
        if args.action == "build":
            out = engine.build(runtime())
            print(f"Built the site in {out}")
        return 0
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (ConversionError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc) if isinstance(exc, ConversionError) else 1


def _init(config: ProjectConfig, chosen: str | None) -> int:
    site = config.site
    name = chosen or (site.engine if site else None)
    if name is None:
        print("Error: say which site to make: --engine mkdocs or --engine starlight, or set site.engine in py-doc.yml", file=sys.stderr)
        return 1
    if site is not None and chosen and site.engine != chosen:
        print(f"Error: py-doc.yml says site.engine: {site.engine}, not {chosen}", file=sys.stderr)
        return 1
    root = site.dir if site else config.root / "site"
    engine = engine_for(name, root)
    title = (site.title if site else None) or config.name or "Documentation"
    written = engine.scaffold(title)
    for path in written:
        print(f"written   {path}")
    if not written:
        print(f"The {name} site in {root} is already there. Nothing was changed")
    if site is None:
        print(f"Add this to {config.root / 'py-doc.yml'} to fill it:\n\nsite:\n  engine: {name}\n  dir: {root.relative_to(config.root).as_posix()}\n")
    else:
        print("Next: py-doc site build")
    return 0
