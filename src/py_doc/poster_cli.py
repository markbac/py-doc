"""``py-doc poster``: self-contained HTML posters from Markdown files, or from the posters of py-doc.yml."""

from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import ConfigError, PosterConfig, find_config, load_config
from py_doc.errors import ConversionError, exit_status
from py_doc.poster import write_poster
from py_doc.poster_settings import SettingsError, layer, merge
from py_doc.poster_themes import BUILTIN
from py_doc.runtime import RuntimeSettings, connect

POSTER_EXAMPLES = """examples:
  py-doc poster                         every poster under posters: in the nearest py-doc.yml
  py-doc poster sn100                   one poster of py-doc.yml, by name
  py-doc poster g460.md                 a Markdown file: writes g460.html
  py-doc poster g460.md -o out.html --theme dark
  py-doc poster g460.md --theme brand.yml --var version=2.1 --condition internal=true
  py-doc poster --pdf                   every poster, and a one-page PDF of each

Settings come from poster: in py-doc.yml, then the front matter, then the poster's entry under posters:,
then the command line. The conventions are in docs/guide/12_posters.md."""


def run_poster(argv: list[str]) -> int:
    from py_doc.app import _assignment, _conditions  # app imports this module

    parser = argparse.ArgumentParser(
        prog="py-doc poster", description="Build self-contained HTML posters from Markdown",
        epilog=POSTER_EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("targets", nargs="*", metavar="POSTER", help="Markdown files, or names under posters: in py-doc.yml (default: every poster)")
    parser.add_argument("-o", "--output", help="Output path, for one poster (default: the input name with .html, or the poster's output)")
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    parser.add_argument("--theme", help=f"A built-in theme ({', '.join(BUILTIN)}) or a theme file. Wins over every other setting")
    parser.add_argument("--var", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set a {{variable}}")
    parser.add_argument("--condition", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set a [[IF:]] condition")
    parser.add_argument(
        "--pdf", action=argparse.BooleanOptionalAction, default=None,
        help="Also print each poster to a one-page PDF beside its page (default: the pdf setting)",
    )  # fmt: skip
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)

    try:
        files = [Path(t) for t in args.targets if t.lower().endswith(".md") or Path(t).is_file()]
        start = files[0].resolve().parent if files else Path.cwd()
        path = Path(args.config) if args.config else find_config(start)
        project = load_config(path) if path else None
        jobs = _jobs(args.targets, files, project)
        if args.output and len(jobs) != 1:
            print("Error: --output needs exactly one poster", file=sys.stderr)
            return 1
        command_line = layer(
            {"theme": args.theme, "variables": dict(args.var), "conditions": _conditions(args.condition)}, Path.cwd(), "the command line"
        )
        settings = project.runtime if project else RuntimeSettings()
        defaults = project.poster if project else {}
        runtime = functools.cache(lambda: connect(settings))  # one container check for every poster
        for job in jobs:
            out = Path(args.output) if args.output else job.output
            ctx, files = write_poster(job.source, out, runtime, merge(job.settings, command_line), defaults, args.pdf)
            print(f"wrote {out} ({ctx.n} diagrams, {ctx.failed} failed)")
            for extra in files[1:]:
                print(f"wrote {extra}")
    except (ConfigError, ConversionError, SettingsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc)
    return 0


def _jobs(targets: list[str], files: list[Path], project) -> list[PosterConfig]:
    """The posters to build: files as given, names from py-doc.yml, or every poster of py-doc.yml."""
    posters = project.posters if project else {}
    if not targets:
        if not posters:
            raise ConfigError("no poster given, and no posters: in py-doc.yml. Name a Markdown file, or add posters to py-doc.yml")
        return list(posters.values())
    jobs = []
    for target in targets:
        file = next((f for f in files if str(f) == target), None)
        if file is not None:
            if not file.is_file():
                raise ConfigError(f"{file} not found")
            jobs.append(PosterConfig(file.stem, file, file.with_suffix(".html")))
        elif target in posters:
            jobs.append(posters[target])
        else:
            known = f" The posters of py-doc.yml are: {', '.join(posters)}" if posters else ""
            raise ConfigError(f"'{target}' is not a Markdown file or a poster of py-doc.yml.{known}")
    return jobs
