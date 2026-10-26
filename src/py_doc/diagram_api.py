"""One diagram, poster block or plot as a picture: the engine of ``py-doc diagram``, and its Python API.

    from py_doc import render_diagram

    picture = render_diagram("graph LR; A-->B", kind="mermaid")
    picture.save("flow.svg")                      # or .png, .webp or .pdf
    picture.to_svg()                              # the SVG text
    render_diagram("Load | 72", kind="gauge", options="max=100", theme="dark").save("load.png", dpi=300)
    render_diagram(text, kind="cards").card(title="The parts").save("parts.pdf")

In a notebook a picture shows itself. A block that is all SVG (a chart, a gauge, a QR code) is drawn by
py-doc alone, as SVG, with no Docker. Anything else (a diagram tool, a block made of HTML, PNG, WebP and
PDF files) goes through the tool container and the diagram cache, as a document's diagrams do.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable
from pathlib import Path

from py_doc.diagrams import BY_FENCE
from py_doc.diagrams import render as drawing
from py_doc.diagrams.blocks import HTML_BLOCK, SVG_BLOCK, BlockError, page, prepare, prepare_plot, theme_for
from py_doc.diagrams.registry import PUPPETEER, TOOLS, Renderer
from py_doc.errors import ConversionError

FORMATS = ("svg", "png", "webp", "pdf")
CSS_DPI = 96  # a CSS pixel; a picture at 192 dpi has two device pixels to each
DEFAULT_DPI = 192  # the density of the diagrams of documents


class DiagramApiError(ConversionError):
    """A picture cannot be drawn as asked: an unknown type, a mistake in the block, or a format it lacks."""


def _browser(fmt: str, scale: float) -> Renderer:
    """Chromium photographing (PNG, at ``scale`` device pixels to a CSS pixel) or printing (PDF) a page's #block.
    It draws what Inkscape cannot, such as the HTML labels of a Mermaid diagram."""
    return Renderer(
        f"browser-{fmt}-{scale:g}", (), ".html", (fmt,),
        lambda job: [["node", TOOLS / "block_png.js", job.source, job.output, PUPPETEER, f"{scale:g}"]],
        env={"NODE_PATH": "/opt/node/node_modules"}, finish_png=False,
    )  # fmt: skip


class Picture:
    """A diagram or block, drawn on demand in each format. ``kind`` is its type, such as mermaid or gauge."""

    def __init__(self, kind: str, renderer: Renderer, body: str, base: Path, runtime: Callable, theme, padding=0):
        self.kind = kind
        self._renderer, self._body, self._base, self._runtime = renderer, body, base, runtime
        self._theme, self._padding = theme, padding
        self._svg: str | None = None  # an SVG of its own, as a card has

    # --- what it can be ------------------------------------------------------------------------------

    @property
    def has_svg(self) -> bool:
        """Whether it can be SVG: a block made of HTML, and tools such as ditaa, draw PNG only."""
        return self._svg is not None or self._renderer is SVG_BLOCK or "svg" in self._renderer.kinds

    def to_svg(self) -> str:
        """The SVG text. Raises DiagramApiError for a picture drawn as PNG only."""
        if self._svg is None:
            if self._renderer is SVG_BLOCK:
                text = self._body
            elif "svg" in self._renderer.kinds:
                text = self._draw(self._renderer, self._body, "svg").decode("utf-8")
            else:
                raise DiagramApiError(f"{self.kind} is drawn as PNG only: save it as .png, .webp or .pdf")
            self._svg = padded(text, self._padding) if self._padding else text
        return self._svg

    def to_png(self, dpi: int | None = None) -> bytes:
        """A PNG, at ``dpi`` (default: 192, as the diagrams of a document)."""
        if dpi is None and not self._padding:
            if self._renderer is HTML_BLOCK or self._renderer is SVG_BLOCK or "png" in self._renderer.kinds:
                return self._draw(self._renderer, self._body, "png")
        scale = (dpi or DEFAULT_DPI) / CSS_DPI
        if self._renderer is HTML_BLOCK:
            return _marked(self._draw(_browser("png", scale), self._page(), "png"), dpi or DEFAULT_DPI)
        if self.has_svg:
            return _marked(self._draw(_browser("png", scale), svg_page(self.to_svg()), "png"), dpi or DEFAULT_DPI)
        return _resized(self._draw(self._renderer, self._body, "png"), dpi or DEFAULT_DPI, self._padding)

    def to_webp(self, dpi: int | None = None) -> bytes:
        """A lossless WebP of the PNG at ``dpi``."""
        from PIL import Image

        out = io.BytesIO()
        with Image.open(io.BytesIO(self.to_png(dpi))) as image:
            image.save(out, "WEBP", lossless=True)
        return out.getvalue()

    def to_pdf(self) -> bytes:
        """A one-page PDF the size of the picture. SVG and HTML stay vector; a PNG-only tool's picture is inside it."""
        if self._renderer is HTML_BLOCK:
            return self._draw(_browser("pdf", 1), self._page(), "pdf")
        if self.has_svg:
            return self._draw(_browser("pdf", 1), svg_page(self.to_svg()), "pdf")
        from PIL import Image

        out = io.BytesIO()
        with Image.open(io.BytesIO(self.to_png())) as image:
            image.convert("RGB").save(out, "PDF", resolution=DEFAULT_DPI)
        return out.getvalue()

    def save(self, path, dpi: int | None = None) -> Path:
        """Write the picture in the format of ``path``'s extension: .svg, .png, .webp or .pdf."""
        path = Path(path)
        fmt = path.suffix.lower().lstrip(".")
        if fmt not in FORMATS:
            raise DiagramApiError(f"{path.name}: the picture can be .svg, .png, .webp or .pdf")
        if dpi is not None and fmt in ("svg", "pdf"):
            raise DiagramApiError(f"--dpi is for PNG and WebP: an {fmt.upper()} picture has no pixels")
        data = {
            "svg": lambda: self.to_svg().encode("utf-8"),
            "png": lambda: self.to_png(dpi),
            "webp": lambda: self.to_webp(dpi),
            "pdf": self.to_pdf,
        }[fmt]()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    # --- a frame ----------------------------------------------------------------------------------------

    def card(self, title: str = "", caption: str = "") -> Picture:
        """The picture in a card of the theme: a box with ``title`` above it and ``caption`` under it."""
        from py_doc.poster_blocks import esc, inline

        block = _BLOCK.search(self._body) if self._renderer is HTML_BLOCK else None
        if self.has_svg:
            inner = sized(self.to_svg())
            width = max(round(_size(inner)[0]) + 2 * 17, 280)
        elif block:  # a block made of HTML goes in as it is, so its text stays text
            inner, width = block[2], int(block[1]) + 2 * 17
        else:
            import base64

            data = base64.b64encode(self.to_png()).decode()
            inner = f'<img alt="{esc(title or self.kind)}" src="data:image/png;base64,{data}">'
            width = max(round(_size(inner)[0]) + 2 * 17, 280)
        html = (
            '<div class="fig card-frame">'
            + (f'<div class="fig-title">{inline(title)}</div>' if title else "")
            + f'<div class="card-pic">{inner}</div>'
            + (f'<p class="caption">{inline(caption)}</p>' if caption else "")
            + "</div>"
        )
        style = (
            "<style>.card-frame{margin:0}.card-pic>svg,.card-pic>img{display:block;margin:0 auto;max-width:100%;"
            "height:auto}.body .card-pic>img{border:0;padding:0;background:none}.card-pic>*:last-child{margin-bottom:0}"
            ".card-frame .caption{margin:0}</style>"
        )
        framed = Picture(
            self.kind, HTML_BLOCK, page(style + html, self._theme, width), self._base, self._runtime, self._theme
        )
        if self.has_svg:
            framed._svg = card_svg(self.to_svg(), title, caption, self._theme)
        return framed

    # --- notebooks ----------------------------------------------------------------------------------

    def _repr_svg_(self):
        return self.to_svg() if self.has_svg else None

    def _repr_png_(self):
        return None if self.has_svg else self.to_png()  # no second drawing when there is SVG to show

    # --- drawing ------------------------------------------------------------------------------------------

    def _page(self) -> str:
        """The HTML block's page, with the padding asked round the block."""
        if not self._padding:
            return self._body
        return self._body.replace("</style></head>", f"#block{{padding:{4 + self._padding}px}}</style></head>", 1)

    def _draw(self, renderer: Renderer, body: str, fmt: str) -> bytes:
        try:
            return drawing.draw_cached(self._runtime(), renderer, body, fmt, False, self._base).read_bytes()
        except drawing.DiagramError as exc:
            raise DiagramApiError(f"{self.kind}: {exc}") from None


def render_diagram(
    text: str,
    kind: str,
    theme=None,
    options: str = "",
    base=None,
    background: str | None = "#ffffff",
    padding: int = 0,
    runtime: Callable | None = None,
) -> Picture:
    """``text`` drawn as the diagram or block ``kind`` (``mermaid``, ``plantuml``, ``gauge``, ``plot`` ...).

    ``theme`` is a built-in theme's name, a theme file or a Theme, for blocks and plots (default: print).
    ``options`` are a block's options, as after its fence name (``"type=pareto"``). ``base`` is the folder its
    pictures are found in (default: the working folder). ``background`` goes behind an SVG block; None leaves
    it transparent. ``padding`` adds space round it, in pixels. ``runtime`` gives the tool container; by
    default it is started from the nearest py-doc.yml when a format needs it.
    """
    from py_doc.poster_themes import Theme

    base = Path(base) if base is not None else Path.cwd()
    if not isinstance(theme, Theme):
        theme = theme_for(str(theme) if theme else None, Path.cwd())
    kind = kind.lower()
    try:
        if kind in BY_FENCE:
            renderer = BY_FENCE[kind]
            try:
                body = drawing.translated(renderer, text, kind)
            except drawing.DiagramError as exc:
                raise DiagramApiError(str(exc)) from None
        elif kind == "plot":
            renderer, body = prepare_plot(options, text, theme)
        elif kind in _natives():
            renderer, body = prepare(kind, options, text, base, theme, background=background)
        else:
            raise DiagramApiError(f"'{kind}' is not a type py-doc draws. py-doc diagram --list shows them")
    except BlockError as exc:
        raise DiagramApiError(str(exc)) from None
    return Picture(kind, renderer, body, base, runtime or _default_runtime(), theme, padding)


def _natives():
    from py_doc.poster_blocks import BLOCKS

    return BLOCKS


def _default_runtime() -> Callable:
    connected: list = []

    def runtime():
        if not connected:
            from py_doc.config import find_config, load_config
            from py_doc.runtime import RuntimeSettings, connect

            found = find_config(Path.cwd())
            connected.append(connect(load_config(found).runtime if found else RuntimeSettings()))
        return connected[0]

    return runtime


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

_VIEWBOX = re.compile(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"')
# The width and the block of the page blocks.page writes
_BLOCK = re.compile(r"#block\{width:(\d+)px.*?<div class=\"body\" id=\"block\">(.*)</div></div></body>", re.S)
_PROLOG = re.compile(r"\A\s*(<\?xml[^>]*\?>\s*)?(<!DOCTYPE[^>]*>\s*)?", re.I)


def padded(svg: str, padding: int) -> str:
    """``svg`` with ``padding`` pixels of space round it: its viewBox, and its width and height, made larger."""
    view = _VIEWBOX.search(svg)
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


def sized(svg: str) -> str:
    """``svg`` without its XML prolog, with a size in pixels (from its viewBox when it has none), to put in a page."""
    from py_doc.poster_blocks import sized_svg

    return sized_svg(_PROLOG.sub("", svg, count=1).encode("utf-8")).decode("utf-8")


def _size(markup: str) -> tuple[float, float]:
    """The size in pixels of an ``<svg>`` or ``<img>`` of a PNG drawn at 192 dpi (half its pixels)."""
    if markup.startswith("<img"):
        import base64

        from PIL import Image

        data = base64.b64decode(markup.split("base64,", 1)[1].split('"', 1)[0])
        with Image.open(io.BytesIO(data)) as image:
            return image.width / 2, image.height / 2
    opening = re.search(r"<svg\b[^>]*>", markup).group(0)
    sizes = dict(re.findall(r'\s(width|height)="([\d.]+)(?:px)?"', opening))
    if len(sizes) == 2:
        return float(sizes["width"]), float(sizes["height"])
    view = _VIEWBOX.search(opening)
    return (float(view[3]), float(view[4])) if view else (400.0, 300.0)


def svg_page(svg: str, padding: int = 0) -> str:
    """A page with the SVG ``svg`` alone in ``#block``, for Chromium to photograph or print."""
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:transparent}'
        f"#block{{display:inline-block;line-height:0;padding:{padding}px}}</style></head>"
        f'<body><div class="poster"><div id="block">{sized(svg)}</div></div></body></html>'
    )


def card_svg(svg: str, title: str, caption: str, theme) -> str:
    """The SVG ``svg`` in a card: the theme's box, ``title`` above it and ``caption`` under it, wrapped to its width."""
    from py_doc.poster_svg import esc, wrap

    inner = sized(svg)
    width, height = _size(inner)
    pad, c, font = 16, theme.colours, theme.fonts["body"]
    box_w = max(width + 2 * pad, 280)
    title_lines = wrap(title, box_w - 2 * pad, 13, bold=True) if title else []
    caption_lines = wrap(caption, box_w - 2 * pad, 14) if caption else []
    y, parts = pad, []
    for line in title_lines:
        parts.append(
            f'<text x="{pad}" y="{y + 13:g}" font-size="13" font-weight="700" fill="{c["muted"]}">{esc(line)}</text>'
        )
        y += 18
    y += 6 if title_lines else 0
    opening = re.search(r"<svg\b", inner)
    placed = inner[: opening.end()] + f' x="{(box_w - width) / 2:g}" y="{y:g}"' + inner[opening.end() :]
    parts.append(placed)
    y += height + (10 if caption_lines else 0)
    for line in caption_lines:
        parts.append(f'<text x="{pad}" y="{y + 14:g}" font-size="14" fill="{c["muted"]}">{esc(line)}</text>')
        y += 20
    total = y + pad
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{box_w:g}" height="{total:g}" viewBox="0 0 {box_w:g} {total:g}"'
        f' font-family="{esc(font)}" color="{c["text"]}">'
        f'<rect x=".5" y=".5" width="{box_w - 1:g}" height="{total - 1:g}" fill="{c["surface"]}" stroke="{c["border"]}"/>'
        + "".join(parts)
        + "</svg>"
    )


def _marked(png: bytes, dpi: int) -> bytes:
    """A PNG from Chromium, which writes no density, marked with ``dpi`` so it prints at its size."""
    from PIL import Image

    with Image.open(io.BytesIO(png)) as image:
        out = io.BytesIO()
        image.save(out, "PNG", dpi=(dpi, dpi))
    return out.getvalue()


def _resized(png: bytes, dpi: int, padding: int) -> bytes:
    """A PNG drawn at 192 dpi, scaled to ``dpi`` and marked with it, with ``padding`` CSS pixels of white round it."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(png)) as image:
        image.load()
        if dpi != DEFAULT_DPI:
            factor = dpi / DEFAULT_DPI
            image = image.resize((round(image.width * factor), round(image.height * factor)), Image.LANCZOS)
        if padding:
            image = ImageOps.expand(image, border=round(padding * dpi / CSS_DPI), fill="white")
        out = io.BytesIO()
        image.save(out, "PNG", dpi=(dpi, dpi))
    return out.getvalue()
