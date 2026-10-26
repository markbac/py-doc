"""``py-doc icons``: download the icon packs ahead of time, list them, and find an icon's name."""

from __future__ import annotations

import argparse
import sys

from py_doc._logging import configure_logging
from py_doc.icons import PACKS, IconError, cache_dir, fetch, pack_dir

EXAMPLES = """examples:
  py-doc icons fetch                 download every pack into the cache, for a machine that will be offline
  py-doc icons list                  the packs, their licences, and whether each is downloaded
  py-doc icons search router         the icons whose names have "router" in them
  py-doc icons search cloud --pack wi

An icon is written icon=tabler:server on a card, step, highlight, stat or flow box. A bare name, such as
icon=server, is a project icon (the poster's icons: folder), else Tabler's, then Material Design's."""

MAX_HITS = 60


def run_icons(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc icons", description="Download, list and search the icon packs of poster blocks",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    common = argparse.ArgumentParser(add_help=False)  # -q and -v, before or after the command
    noise = common.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    get = commands.add_parser("fetch", parents=[common], help="Download the packs into the cache (default: every pack)")
    get.add_argument("packs", nargs="*", metavar="PACK", help=f"Of: {', '.join(PACKS)}")
    commands.add_parser(
        "list", parents=[common], help="The packs, their versions and licences, and whether each is downloaded"
    )
    find = commands.add_parser("search", parents=[common], help="The icons whose names have a word in them")
    find.add_argument("word", help="Part of an icon's name, such as router")
    find.add_argument("--pack", choices=list(PACKS), help="Only this pack (default: every pack)")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    unknown = [name for name in getattr(args, "packs", []) if name not in PACKS]
    if unknown:
        parser.error(f"there is no icon pack {unknown[0]}. The packs are {', '.join(PACKS)}")
    try:
        if args.command == "fetch":
            for prefix in args.packs or PACKS:
                print(f"{prefix:<10} {fetch(prefix).parent}")
        elif args.command == "list":
            print(f"Cache: {cache_dir()}")
            for pack in PACKS.values():
                state = "downloaded" if (pack_dir(pack) / "icons.json").is_file() else "not downloaded yet"
                print(f"  {pack.prefix:<10} {pack.version:<8} {pack.licence:<11} {pack.title} ({state})")
        else:
            print("\n".join(search(args.word, [args.pack] if args.pack else list(PACKS))) or "No icon found")
    except IconError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def search(word: str, prefixes: list[str]) -> list[str]:
    """The names, as icon= takes them, of the icons and aliases of ``prefixes`` with ``word`` in them."""
    import json

    word, hits = word.lower(), []
    for prefix in prefixes:
        data = json.loads(fetch(prefix).read_text(encoding="utf-8"))
        names = [*data.get("icons", {}), *data.get("aliases", {})]
        hits += [f"{prefix}:{name}" for name in sorted(names) if word in name]
    if len(hits) > MAX_HITS:
        return [*hits[:MAX_HITS], f"... and {len(hits) - MAX_HITS} more: give a longer word, or --pack"]
    return hits
