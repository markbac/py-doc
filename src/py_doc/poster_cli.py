"""``py-doc poster``: self-contained HTML posters from Markdown files, or from the posters of py-doc.yml."""

from __future__ import annotations

import argparse
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
  py-doc poster sn100 --watch           build again on every save, and reload it in the browser

Settings come from poster: in py-doc.yml, then the front matter, then the poster's entry under posters:,
then the command line. The conventions are in docs/guide/12_posters.md."""


def run_poster(argv: list[str]) -> int:
    from py_doc.app import _assignment, _conditions  # app imports this module

    parser = argparse.ArgumentParser(
        prog="py-doc poster", description="Build self-contained HTML posters from Markdown",
        epilog=POSTER_EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument(
        "targets",
        nargs="*",
        metavar="POSTER",
        help="Markdown files, or names under posters: in py-doc.yml (default: every poster)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output path, for one poster (default: the input name with .html, or the poster's output)",
    )
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    parser.add_argument(
        "--theme", help=f"A built-in theme ({', '.join(BUILTIN)}) or a theme file. Wins over every other setting"
    )
    parser.add_argument(
        "--var", action="append", default=[], metavar="NAME=VALUE", type=_assignment, help="Set a {{variable}}"
    )
    parser.add_argument(
        "--condition",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        type=_assignment,
        help="Set a [[IF:]] condition",
    )
    parser.add_argument(
        "--embed-fonts", action=argparse.BooleanOptionalAction, default=None,
        help="Download the theme's web fonts once and put them inside the page (default: the embed_fonts setting)",
    )  # fmt: skip
    parser.add_argument(
        "--pdf", action=argparse.BooleanOptionalAction, default=None,
        help="Also print each poster to a one-page PDF beside its page (default: the pdf setting)",
    )  # fmt: skip
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Build again on every save, and reload the page in the browser (Ctrl+C stops)",
    )
    parser.add_argument(
        "--port", type=int, default=0, help="With --watch, the local port to serve the pages on (default: a free one)"
    )
    parser.add_argument("--no-open", action="store_true", help="With --watch, do not open the browser")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)

    if args.watch and args.pdf:
        print("Error: --watch builds the pages only; leave out --pdf", file=sys.stderr)
        return 1
    if args.targets == ["help"] and not Path("help").is_file():
        parser.print_help()
        return 0
    # Each target that is a file, by the text it was given as: .\a.md and ./a.md are both a.md once made a Path
    files = {t: Path(t) for t in args.targets if t.lower().endswith((".md", ".markdown")) or Path(t).is_file()}
    start = next(iter(files.values())).resolve().parent if files else Path.cwd()
    config_path = Path(args.config) if args.config else find_config(start)
    connected: list = []

    def runtime():  # one container check for every poster, and every build of --watch
        if not connected:
            connected.append(connect(load_config(config_path).runtime if config_path else RuntimeSettings()))
        return connected[0]

    def build_all() -> tuple[dict[str, Path], set[Path]]:
        """Write every poster asked for. Returns their pages by name, and the files they were made from."""
        project = load_config(config_path) if config_path else None  # read again on each build of --watch
        jobs = _jobs(args.targets, files, project)
        if args.output and len(jobs) != 1:
            raise ConfigError("--output needs exactly one poster")
        command_line = layer(
            {
                "theme": args.theme,
                "variables": dict(args.var),
                "conditions": _conditions(args.condition),
                "embed_fonts": args.embed_fonts,
            },
            Path.cwd(),
            "the command line",
        )
        defaults = project.poster if project else {}
        pages, sources = {}, {config_path.resolve()} if config_path else set()
        for job in jobs:
            out = Path(args.output) if args.output else job.output
            settings = merge(job.settings, command_line)
            ctx, written = write_poster(job.source, out, runtime, settings, defaults, False if args.watch else args.pdf,
                                        project.mermaid if project else None)  # fmt: skip
            print(f"wrote {out} ({ctx.n} diagrams, {ctx.failed} failed)")
            for extra in written[1:]:
                print(f"wrote {extra}")
            pages[job.name] = out.resolve()
            sources |= {job.source.resolve(), *_paths(settings), *_paths(defaults)}
        return pages, sources

    errors = (ConfigError, ConversionError, SettingsError)
    if args.watch:
        from py_doc.watch import watch

        return watch(build_all, errors, port=args.port, open_browser=not args.no_open)
    try:
        build_all()
    except errors as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc)
    return 0


def _paths(value) -> list[Path]:
    """The files a layer of settings names, such as its theme and logos, to watch with the Markdown."""
    if isinstance(value, Path):
        return [value]
    if isinstance(value, dict):
        return [path for item in value.values() for path in _paths(item)]
    if isinstance(value, list):
        return [path for item in value for path in _paths(item)]
    return []


def _jobs(targets: list[str], files: dict[str, Path], project) -> list[PosterConfig]:
    """The posters to build: files as given, names from py-doc.yml, or every poster of py-doc.yml."""
    posters = project.posters if project else {}
    if not targets:
        if not posters:
            raise ConfigError(
                "no poster given, and no posters: in py-doc.yml. Name a Markdown file, or add posters to py-doc.yml"
            )
        return list(posters.values())
    jobs = []
    for target in targets:
        file = files.get(target)
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
