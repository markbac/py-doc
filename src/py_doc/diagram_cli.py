"""``py-doc diagram`` (or ``py-doc image``): one diagram or poster block as an image file of its own.

A diagram source file (a ``.mmd``, ``.puml``, ``.dot`` ...), a poster block or ``plot`` with ``--type``, or every
diagram and block of a Markdown file, is drawn the way a document draws it and written as SVG, PNG, WebP or
PDF. The drawing is :mod:`py_doc.diagram_api`, which is also the Python API.
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import sys
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import ConfigError, find_config, load_config
from py_doc.diagram_api import FORMATS, DiagramApiError, Picture, padded, render_diagram  # noqa: F401 - padded is API
from py_doc.errors import ConversionError, exit_status
from py_doc.runtime import RuntimeSettings, connect

EXAMPLES = """examples:
  py-doc diagram flow.mmd -o flow.svg              a Mermaid file, as SVG
  py-doc diagram flow.puml -o flow.png --dpi 300   a PlantUML file, as PNG at 300 dpi
  py-doc diagram returns.txt --type plot --options "type=pareto" -o returns.pdf
  py-doc diagram credit.txt --type threshold -o credit.svg --theme dark
  py-doc diagram parts.txt --type cards -o parts.png           a block made of HTML, photographed
  py-doc diagram flow.mmd -o flow.png --chrome card --title "Joining" --caption "From power on to joined"
  py-doc diagram poster.md -o images/              every diagram and block of a Markdown file
  py-doc diagram poster.md -o images/ --format webp
  py-doc diagram flow.mmd -o flow.svg --watch      draw again on every save, and show it in the browser
  py-doc diagram --list                            every type it draws
  py-doc diagram --help-type gauge                 the syntax of one, with an example

The type comes from --type, or from the file's extension. Poster blocks are drawn in the theme of
--theme (default: print), the same way documents draw them. SVG is for the pictures that are SVG: a block
made of HTML, and a tool such as ditaa, are PNG, WebP or PDF."""

EXTENSIONS = {
    ".mmd": "mermaid", ".mermaid": "mermaid", ".puml": "plantuml", ".plantuml": "plantuml", ".dot": "dot",
    ".gv": "dot", ".ditaa": "ditaa", ".edn": "bytefield-svg", ".pikchr": "pikchr", ".railroad": "railroad",
    ".vl.json": "vega-lite", ".vg.json": "vega", ".wavedrom.json": "wavedrom",
}  # fmt: skip


class DiagramCliError(ConversionError):
    """What was asked of ``py-doc diagram`` cannot be done."""


def run_diagram(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc diagram", description="Draw one diagram or poster block as an image file",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("input", nargs="?", help="A diagram source, a block's text, a Markdown file, or - for stdin")
    parser.add_argument("-o", "--output", help="The image (.svg, .png, .webp or .pdf), or a folder for a Markdown file")
    parser.add_argument("-t", "--type", help="The diagram or block type, when the extension does not say it")
    parser.add_argument("--options", default="", help='The options of a block, as after its fence name: "type=pareto"')
    parser.add_argument(
        "-f", "--format", choices=FORMATS, default="svg", help="For a Markdown file: svg (default), png, webp or pdf"
    )
    parser.add_argument("--dpi", type=int, help="The density of a PNG or WebP (default: 192)")
    parser.add_argument(
        "--theme", help="The theme of poster blocks and plots: a built-in name or a theme file (default: print)"
    )
    parser.add_argument(
        "--background", default="#ffffff", help="Behind an SVG block: a CSS colour, or transparent (default: white)"
    )
    parser.add_argument("--padding", type=int, default=0, help="Space round the picture, in pixels (default: 0)")
    parser.add_argument(
        "--chrome", choices=("none", "card"), default="none",
        help="card: the picture in a box of the theme, with --title above it and --caption under it",
    )  # fmt: skip
    parser.add_argument("--title", default="", help="With --chrome card, the title (default: the fence's caption)")
    parser.add_argument("--caption", default="", help="With --chrome card, the text under the picture")
    parser.add_argument("--watch", action="store_true", help="Draw again on every save, and show it in the browser")
    parser.add_argument("--port", type=int, default=0, help="With --watch, the local port (default: a free one)")
    parser.add_argument("--no-open", action="store_true", help="With --watch, do not open the browser")
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
    if args.dpi is not None and args.dpi < 24:
        parser.error("--dpi must be at least 24")
    if args.watch:
        if args.input == "-":
            parser.error("--watch needs a file to watch, not stdin")
        return _watch(args)
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
    output = Path(args.output) if args.output else Path(f"{stem}.{args.format}")
    fmt = output.suffix.lower().lstrip(".")
    if fmt not in FORMATS:
        raise DiagramCliError(f"the output must be a .svg, .png, .webp or .pdf file, not {output.name}")
    one(kind, args.options, text, base, theme, output, args, runtime, args.title)
    return [output]


def one(kind, options, text, base, theme, output, args, runtime, title="") -> Path:
    """Draw one diagram or block into ``output``, in the format of its extension."""
    try:
        picture = render_diagram(
            text, kind, theme, options, base, _background(args.background), args.padding, runtime
        )  # fmt: skip
        if args.chrome == "card":
            picture = picture.card(args.title or title, args.caption)
        return picture.save(output, args.dpi)
    except DiagramApiError as exc:
        raise DiagramCliError(str(exc)) from None


def _background(value: str) -> str | None:
    return None if value.lower() in ("transparent", "none") else value


def _extract(source: Path, folder: Path, args, theme, runtime) -> list[Path]:
    """Every diagram and block of the Markdown file ``source``, as files in ``folder``."""
    from py_doc.diagram_api import render_diagram as _render
    from py_doc.diagrams.scan import find_blocks

    text = source.read_text(encoding="utf-8")
    found = find_blocks(text, frozenset(_natives()) | {"plot"})
    if not found:
        raise DiagramCliError(f"{source} has no diagram or block to draw")
    written = []
    for n, block in enumerate(found, 1):
        title = block.options.get("caption") or block.options.get("title") or ""
        name = _slug(title or block.fence)
        output = folder / f"{source.stem}-{n:02d}-{name}.{args.format}"
        try:
            if args.format == "svg":  # a block made of HTML, or a tool such as ditaa, has no SVG: PNG instead
                probe = _render(block.body, block.fence, theme, block.info, source.resolve().parent, runtime=runtime)
                if not probe.has_svg:
                    output = output.with_suffix(".png")
            written.append(
                one(block.fence, block.info, block.body, source.resolve().parent, theme, output, args, runtime, title)
            )
        except (DiagramCliError, DiagramApiError) as exc:
            raise DiagramCliError(f"{source}:{block.line}: {exc}") from None
    return written


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "diagram"


# ---------------------------------------------------------------------------
# --watch: draw again on every save, and show the pictures on a page that reloads
# ---------------------------------------------------------------------------


def _watch(args) -> int:
    from py_doc.watch import watch

    source = Path(args.input).resolve()
    preview = source.parent / ".py-doc" / "preview" / f"{source.stem}-diagram.html"

    def build():
        written = draw(args)
        for path in written:
            print(f"wrote {path}", flush=True)
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_text(preview_page(source.name, written), encoding="utf-8")
        return {source.stem: preview}, {source}

    return watch(
        build, (ConfigError, ConversionError), port=args.port, open_browser=not args.no_open, title="py-doc diagram"
    )  # fmt: skip


def preview_page(name: str, files: list[Path]) -> str:
    """A page that shows each picture ``files`` holds, under its file name, for --watch."""
    kinds = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".pdf": "application/pdf"}
    shown = ""
    for path in files:
        mime = kinds[path.suffix.lower()]
        data = base64.b64encode(path.read_bytes()).decode()
        if mime == "application/pdf":
            picture = f'<embed type="application/pdf" src="data:{mime};base64,{data}" width="100%" height="800">'
        else:
            picture = f'<img alt="{html.escape(path.name)}" src="data:{mime};base64,{data}">'
        shown += f"<figure>{picture}<figcaption>{html.escape(str(path))}</figcaption></figure>"
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(name)}</title><style>'
        "body{margin:0;padding:24px;background:#eef0f4;font:14px/1.4 sans-serif;color:#333}"
        "figure{margin:0 0 24px;background:#fff;padding:16px;border:1px solid #d5d9e0;display:inline-block}"
        "img{max-width:100%;display:block}figcaption{margin-top:8px;color:#666}"
        f"</style></head><body>{shown}</body></html>"
    )


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
