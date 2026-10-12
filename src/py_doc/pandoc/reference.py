"""The Word reference document used when no template is set: pandoc's own, plus boxes for callouts."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Cm

from py_doc.runtime import Mount, Runtime

logger = logging.getLogger(__name__)

# kind -> (background, edge), the colours of the HTML and PDF boxes
CALLOUTS = {
    "note": ("E7F1F8", "0072B2"),
    "tip": ("E8F5E9", "2E7D32"),
    "important": ("F1ECF9", "6A3FB5"),
    "warning": ("FFF4E0", "E08A00"),
    "caution": ("FCE8E8", "C62828"),
}
PREFIX = "Div."  # pandoc applies the custom-style of a callout Div by this name


def callout_style_names() -> list[str]:
    return [PREFIX + kind for kind in CALLOUTS]


def add_styles(document) -> None:
    """Add the callout paragraph styles and a ``Table Grid`` table style, where they are missing."""
    styles = document.styles
    existing = {style.name for style in styles}
    for kind, (fill, edge) in CALLOUTS.items():
        name = PREFIX + kind
        if name in existing:
            continue
        style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = styles["Normal"]
        style.paragraph_format.left_indent = Cm(0.3)
        style.paragraph_format.right_indent = Cm(0.3)
        properties = style.element.get_or_add_pPr()
        properties.append(
            parse_xml(
                f'<w:pBdr {nsdecls("w")}>'
                f'<w:top w:val="single" w:sz="4" w:space="4" w:color="{fill}"/>'
                f'<w:left w:val="single" w:sz="36" w:space="6" w:color="{edge}"/>'
                f'<w:bottom w:val="single" w:sz="4" w:space="4" w:color="{fill}"/>'
                f'<w:right w:val="single" w:sz="4" w:space="6" w:color="{fill}"/>'
                "</w:pBdr>"
            )
        )
        properties.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill}"/>'))
    if "Table Grid" not in existing:
        grid = styles.add_style("Table Grid", WD_STYLE_TYPE.TABLE)
        grid.element.append(
            parse_xml(
                f'<w:tblPr {nsdecls("w")}><w:tblBorders>'
                + "".join(
                    f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
                    for side in ("top", "left", "bottom", "right", "insideH", "insideV")
                )
                + "</w:tblBorders></w:tblPr>"
            )
        )


def default_reference(runtime: Runtime, work: Path) -> Path:
    """Write pandoc's reference.docx with callout styles into ``work`` and return its path."""
    path = work / "reference.docx"
    runtime.run(
        ["pandoc", "-o", path, "--print-default-data-file", "reference.docx"], mounts=[Mount(work, writable=True)], workdir=work
    )
    document = Document(str(path))
    add_styles(document)
    document.save(str(path))
    return path


_CALLOUT = re.compile(
    r"^\s*>+\s*(?:\[!(?P<github>[A-Za-z]+)\]|\*\*(?P<label>[A-Za-z]+):?\*\*)", re.MULTILINE
)


def used_callouts(markdown: str) -> set[str]:
    """The callout kinds a Markdown text uses, in either spelling."""
    found = {(m["github"] or m["label"]).lower() for m in _CALLOUT.finditer(markdown)}
    return found & set(CALLOUTS)


def missing_callout_styles(template: Path, markdown: str) -> list[str]:
    """The callout styles ``markdown`` needs that a template does not define."""
    have = {style.name for style in Document(str(template)).styles}
    return [PREFIX + kind for kind in CALLOUTS if kind in used_callouts(markdown) and PREFIX + kind not in have]
