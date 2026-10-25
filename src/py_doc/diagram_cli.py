"""``py-doc diagram`` (or ``py-doc image``): one diagram or poster block as an image file of its own.

A diagram source file (a ``.mmd``, ``.puml``, ``.dot`` ...), a poster block or ``plot`` with ``--type``, or every
diagram and block of a Markdown file, is drawn the way a document draws it and written as SVG or PNG.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config
from py_doc.errors import ConversionError, exit_status
from py_doc.runtime import RuntimeSettings, connect

EXAMPLES = """examples:
  py-doc diagram flow.mmd -o flow.svg              a Mermaid file, as SVG
  py-doc diagram flow.puml -o flow.png             a PlantUML file, as PNG
  py-doc diagram returns.txt --type plot --options "type=pareto" -o returns.svg
  py-doc diagram credit.txt --type threshold -o credit.svg --theme dark
  py-doc diagram poster.md -o images/              every diagram and block of a Markdown file
  py-doc diagram poster.md -o images/ --format png
  py-doc diagram --list                            every type it draws
  py-doc diagram --help-type gauge                 the syntax of one, with an example

The type comes from --type, or from the file's extension. Poster blocks are drawn in the theme of
--theme (default: print), the same way documents draw them."""

EXTENSIONS = {
    ".mmd": "mermaid", ".mermaid": "mermaid", ".puml": "plantuml", ".plantuml": "plantuml", ".dot": "dot",
    ".gv": "dot", ".ditaa": "ditaa", ".edn": "bytefield-svg", ".pikchr": "pikchr", ".railroad": "railroad",
    ".vl.json": "vega-lite", ".vg.json": "vega", ".wavedrom.json": "wavedrom",
}  # fmt: skip
FORMATS = ("svg", "png")


class DiagramCliError(ConversionError):
    """What was asked of ``py-doc diagram`` cannot be done."""


def run_diagram(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc diagram", description="Draw one diagram or poster block as an image file",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("input", nargs="?", help="A diagram source, a block's text, a Markdown file, or - for stdin")
    parser.add_argument("-o", "--output", help="The image (.svg or .png), or a folder for a Markdown file")
    parser.add_argument("-t", "--type", help="The diagram or block type, when the extension does not say it")
    parser.add_argument("--options", default="", help='The options of a block, as after its fence name: "type=pareto"')
    parser.add_argument(
        "-f", "--format", choices=FORMATS, default="svg", help="For a Markdown file: svg (default) or png"
    )
    parser.add_argument(
        "--theme", help="The theme of poster blocks and plots: a built-in name or a theme file (default: print)"
    )
    parser.add_argument(
        "--background", default="#ffffff", help="Behind an SVG block: a CSS colour, or transparent (default: white)"
    )
    parser.add_argument("--padding", type=int, default=0, help="Space round an SVG picture, in pixels (default: 0)")
    parser.add_argument("--list", action="store_true", help="List every type it draws")
    parser.add_argument("--help-type", metavar="TYPE", help="Show the syntax of one type, with an example")
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    if args.list:
        print(listing())
        return 0
    if args.help_type:
        try:
            print(help_for(args.help_type))
        except DiagramCliError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0
    if not args.input:
        parser.error("give a file to draw, or --list")
    try:
        written = draw(args)
    except (ConfigError, ConversionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc)
    for path in written:
        print(f"wrote {path}")
    return 0


def _natives():
    from py_doc.poster_blocks import BLOCKS

    return BLOCKS


def kind_of(path: Path, given: str | None) -> str:
    """The type to draw ``path`` as: ``given``, else from its extension."""
    from py_doc.diagrams import BY_FENCE

    if given:
        name = given.lower()
        if name not in BY_FENCE and name not in _natives() and name != "plot":
            raise DiagramCliError(f"'{given}' is not a type py-doc draws. py-doc diagram --list shows them")
        return name
    name = path.name.lower()
    for suffix, fence in sorted(EXTENSIONS.items(), key=lambda item: -len(item[0])):
        if name.endswith(suffix):
            return fence
    raise DiagramCliError(f"the type of {path.name} is not known from its extension: give it with --type")


def draw(args) -> list[Path]:
    """Draw what ``args`` asks for and return the files written."""
    from py_doc.diagrams.blocks import theme_for

    source = Path(args.input)
    config_path = (
        Path(args.config) if args.config else find_config(Path.cwd() if args.input == "-" else source.resolve().parent)
    )
    connected: list = []

    def runtime():
        if not connected:
            connected.append(connect(load_config(config_path).runtime if config_path else RuntimeSettings()))
        return connected[0]

    theme = theme_for(args.theme, Path.cwd())
    if args.input != "-" and source.suffix.lower() in (".md", ".markdown"):
        if not source.is_file():
            raise DiagramCliError(f"{source} not found")
        return _extract(source, Path(args.output or source.with_suffix("")), args, theme, runtime)
    if args.input == "-":
        text, base, stem = sys.stdin.read(), Path.cwd(), "diagram"
        if not args.type:
            raise DiagramCliError("from stdin, give the type with --type")
        kind = kind_of(Path("stdin"), args.type)
    else:
        if not source.is_file():
            raise DiagramCliError(f"{source} not found")
        text, base, stem = source.read_text(encoding="utf-8"), source.resolve().parent, source.stem
        kind = kind_of(source, args.type)
    output = Path(args.output) if args.output else Path(f"{stem}.svg")
    fmt = output.suffix.lower().lstrip(".")
    if fmt not in FORMATS:
        raise DiagramCliError(f"the output must be a .svg or .png file, not {output.name}")
    one(kind, args.options, text, base, theme, fmt, output, args, runtime)
    return [output]


def one(kind, options, text, base, theme, fmt, output, args, runtime) -> Path:
    """Draw one diagram or block into ``output``, as ``fmt``."""
    from py_doc.diagrams import BY_FENCE
    from py_doc.diagrams import render as drawing
    from py_doc.diagrams.blocks import BlockError, prepare, prepare_plot

    try:
        if kind in BY_FENCE:
            renderer = BY_FENCE[kind]
            try:
                body = drawing.translated(renderer, text, kind)
            except drawing.DiagramError as exc:
                raise DiagramCliError(str(exc)) from None
        elif kind == "plot":
            renderer, body = prepare_plot(options, text, theme)
        else:
            renderer, body = prepare(kind, options, text, base, theme, background=_background(args.background))
    except BlockError as exc:
        raise DiagramCliError(str(exc)) from None
    if fmt == "svg" and "svg" not in renderer.kinds:
        raise DiagramCliError(f"{kind} is drawn as PNG only: write the output as .png")
    picture = drawing.draw_cached(runtime(), renderer, body, fmt, False, base)
    output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "svg" and args.padding:
        output.write_text(padded(picture.read_text(encoding="utf-8"), args.padding), encoding="utf-8")
    else:
        shutil.copyfile(picture, output)
    return output


def _background(value: str) -> str | None:
    return None if value.lower() in ("transparent", "none") else value


def _extract(source: Path, folder: Path, args, theme, runtime) -> list[Path]:
    """Every diagram and block of the Markdown file ``source``, as files in ``folder``."""
    from py_doc.diagrams import BY_FENCE
    from py_doc.diagrams.scan import find_blocks

    text = source.read_text(encoding="utf-8")
    found = find_blocks(text, frozenset(_natives()) | {"plot"})
    if not found:
        raise DiagramCliError(f"{source} has no diagram or block to draw")
    written = []
    for n, block in enumerate(found, 1):
        fmt = args.format
        renderer_kinds = BY_FENCE[block.fence].kinds if block.fence in BY_FENCE else None
        if fmt == "svg" and renderer_kinds is not None and "svg" not in renderer_kinds:
            fmt = "png"  # a tool that draws PNG only, such as ditaa
        name = _slug(block.options.get("caption") or block.options.get("title") or block.fence)
        output = folder / f"{source.stem}-{n:02d}-{name}.{fmt}"
        try:
            written.append(
                one(block.fence, block.info, block.body, source.resolve().parent, theme, fmt, output, args, runtime)
            )
        except DiagramCliError as exc:
            if "drawn as PNG only" not in str(exc):
                raise DiagramCliError(f"{source}:{block.line}: {exc}") from None
            written.append(
                one(
                    block.fence,
                    block.info,
                    block.body,
                    source.resolve().parent,
                    theme,
                    "png",
                    output.with_suffix(".png"),
                    args,
                    runtime,
                )
            )
    return written


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "diagram"


def padded(svg: str, padding: int) -> str:
    """``svg`` with ``padding`` pixels of space round it: its viewBox, and its width and height, made larger."""
    view = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"', svg)
    if not view:
        return svg
    x, y, w, h = (float(v) for v in view.groups())
    box = f'viewBox="{x - padding:g} {y - padding:g} {w + 2 * padding:g} {h + 2 * padding:g}"'
    out = svg[: view.start()] + box + svg[view.end() :]
    opening = re.search(r"<svg\b[^>]*>", out)
    tag = opening.group(0)
    for attr, size in (("width", w), ("height", h)):
        tag = re.sub(rf'\s{attr}="[\d.]+"', f' {attr}="{size + 2 * padding:g}"', tag, count=1)
    return out[: opening.start()] + tag + out[opening.end() :]


def listing() -> str:
    """Every type ``py-doc diagram`` draws, by kind."""
    from py_doc.diagrams import BY_FENCE
    from py_doc.poster_plot import TYPES

    blocks = _natives()
    lines = ["Diagram tools (drawn by the tool container):"]
    lines += [f"  {name}" for name in sorted(BY_FENCE)]
    lines += ["", "Poster blocks (drawn by py-doc; py-doc diagram --help-type NAME for the syntax):"]
    lines += [f"  {name:<16} {blocks[name].syntax[:90]}" for name in sorted(blocks)]
    lines += ["", f"plot, with --options type=: {', '.join(TYPES)}"]
    return "\n".join(lines)


def help_for(name: str) -> str:
    """The syntax of one type, with an example to start from."""
    from py_doc.diagrams import BY_FENCE
    from py_doc.poster_plot import TYPES

    blocks = _natives()
    if name in blocks:
        found = blocks[name]
        fence = f"```{name}{' ' + found.info if found.info else ''}"
        example = f"{fence}\n{found.example}\n```" if found.example is not None else "(its example needs picture files)"
        return f"{name}: {found.syntax}\n\nExample:\n\n{example}"
    if name == "plot":
        return f'plot: a chart preset, drawn with Vega-Lite. --options "type=..." with one of: {", ".join(TYPES)}.\nSee docs/guide/12_posters.md, Plots.'
    if name in BY_FENCE:
        return f"{name}: drawn by the {BY_FENCE[name].name} tool in the container, from its own syntax. See docs/guide/03_writing.md, Diagrams."
    raise DiagramCliError(f"'{name}' is not a type py-doc draws. py-doc diagram --list shows them")
