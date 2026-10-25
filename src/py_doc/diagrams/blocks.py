"""Poster blocks in documents: a native block fence (``cards``, ``chart``, ``equation``...) drawn as a picture.

The block is drawn by the same code as on a poster, in the theme of ``diagrams.theme`` (``print`` unless set),
then made a picture in the tool container. A block that is all SVG (a chart, a QR code) is written as an SVG
file, which Inkscape turns into PNG where the document needs one. A block made of HTML is laid out with the
poster's styles at the width of the document's text, and photographed by Chromium. Both go through the
diagram cache, so a block that has not changed is not drawn again.
"""

from __future__ import annotations

from pathlib import Path

from py_doc.errors import ConversionError

from .registry import PUPPETEER, TOOLS, Renderer

# CSS pixels of the text width: an A4 or Letter page less its margins, upright or turned. The picture is taken
# at twice this, then shrunk to the page as the other diagrams are.
TEXT_WIDTH = {"portrait": 640, "landscape": 960}

# Its source is already the picture; it has a suffix of its own so the copy is not onto itself
SVG_BLOCK = Renderer("block-svg", (), ".block", ("svg",), lambda job: [["cp", job.source, job.output]])
HTML_BLOCK = Renderer(
    "block-html",
    (),
    ".html",
    ("png",),
    lambda job: [["node", TOOLS / "block_png.js", job.source, job.output, PUPPETEER]],
    env={"NODE_PATH": "/opt/node/node_modules"},
)


class BlockError(ConversionError):
    """A poster block in a document has a mistake."""


def names() -> frozenset[str]:
    """The fence names of the native blocks."""
    from py_doc.poster_blocks import BLOCKS

    return frozenset(BLOCKS)


def theme_for(spec, folder: Path):
    """The theme poster blocks are drawn in: ``spec`` (a built-in name or a theme file), else ``print``."""
    from py_doc.poster_themes import load_theme

    return load_theme(spec or "print", folder)


def prepare(fence: str, info: str, body: str, base: Path, theme, landscape: bool = False) -> tuple[Renderer, str]:
    """The renderer and source text that draw the block ``fence`` of a document as a picture.

    ``info`` is the fence's options as written after its name, ``base`` the folder of the Markdown file (for the
    pictures of a gallery). Raises BlockError for a mistake in the block.
    """
    from py_doc import poster, poster_blocks, poster_svg

    ctx = poster_blocks.Ctx(base, lambda: None, theme, render=poster.render, where=f"the {fence} block")
    try:
        drawn = poster_blocks.block_fragment(fence, poster_blocks.parse_opts(info), body, ctx)
    except poster_blocks.PosterError as exc:
        raise BlockError(str(exc)) from None
    if drawn.svg:
        return SVG_BLOCK, poster_svg.standalone(drawn.svg, theme, background="#ffffff")
    return HTML_BLOCK, page(drawn.html, theme, TEXT_WIDTH["landscape" if landscape else "portrait"])


def page(block_html: str, theme, width: int) -> str:
    """A page of the poster's styles with ``block_html`` in ``#block``, ``width`` CSS pixels wide, on white."""
    from py_doc.poster import CSS

    css = CSS.replace("__VARS__", theme.css_variables()).replace("__PAPER__", "A4")
    css = css.replace("__W__", str(width)).replace("__H__", "0")
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>{css}</style>"
        "<style>body{background:#fff}.poster{background:#fff;min-height:0}"
        f"#block{{width:{width}px;padding:4px}}#block>*:last-child{{margin-bottom:0}}</style>"
        f'</head><body><div class="poster"><div class="body" id="block">{block_html}</div></div></body></html>'
    )
