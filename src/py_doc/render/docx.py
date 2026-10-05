"""Render Markdown as a Word (.docx) document.

The Markdown is parsed once by :mod:`py_doc.markdown` and this module walks the resulting tree.
Every construct is rendered through a named Word style, so a reference template controls how it looks.
A style the template lacks is created with a plain default.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.image.exceptions import UnrecognizedImageError
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt, RGBColor

from py_doc.errors import ConversionError
from py_doc.markdown import FrontMatterError, Metadata, ParseError, parse, read_metadata
from py_doc.markdown import nodes as n

logger = logging.getLogger(__name__)

# Characters that cannot appear in an XML 1.0 document (python-docx rejects them).
XML_INVALID_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")

CODE_FONT = "Consolas"
CODE_STYLE = "Code"
MAX_LIST_DEPTH = 3  # Word's built-in list styles stop at level 3

_ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


@dataclass(frozen=True)
class _Format:
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: bool = False


class _Renderer:
    """Writes the nodes of one parsed document into a python-docx ``Document``."""

    def __init__(self, doc, base_dir: Path, name: str) -> None:
        self.doc = doc
        self.base_dir = base_dir
        self.name = name
        self.style_names = {style.name for style in doc.styles}
        self.has_link_style = "Hyperlink" in self.style_names
        self.restart_warned = False

    def render(self, document: n.Document) -> None:
        self.blocks(document.children, quote=0)

    def set_properties(self, metadata: Metadata) -> None:
        """Copy the front matter into the document properties. Front matter is not part of the body."""
        properties = self.doc.core_properties
        for name, value in (
            ("title", metadata.title),
            ("subject", metadata.subtitle),
            ("author", metadata.author),
            ("keywords", metadata.keywords),
            ("version", metadata.version),
            ("content_status", metadata.status),
            ("identifier", metadata.document_id),
        ):
            if value:
                setattr(properties, name, value)

    # --- styles ---------------------------------------------------------------------------------

    def style(self, name: str) -> str:
        """Return ``name``, first creating a plain paragraph style if the template lacks it."""
        if name in self.style_names:
            return name
        style = self.doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = self.doc.styles["Normal"]
        if name == CODE_STYLE:
            style.font.name = CODE_FONT
            style.font.size = Pt(9.5)
            style.font.color.rgb = RGBColor(30, 41, 59)
            style.paragraph_format.left_indent = Inches(0.4)
            fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
            fonts.set(qn("w:eastAsia"), CODE_FONT)
            fonts.set(qn("w:cs"), CODE_FONT)
        elif name.startswith("Heading"):
            style.font.bold = True
        elif name == "Quote":
            style.font.italic = True
            style.paragraph_format.left_indent = Inches(0.4)
        elif name.startswith("List"):
            logger.warning(f"The template has no '{name}' style, so those list items get no bullet or number")
        self.style_names.add(name)
        return name

    # --- blocks ---------------------------------------------------------------------------------

    def blocks(self, blocks: list[n.Block], quote: int) -> None:
        for block in blocks:
            self.block(block, quote)

    def block(self, block: n.Block, quote: int) -> None:
        if isinstance(block, n.Heading):
            self.heading(block)
        elif isinstance(block, n.Paragraph):
            paragraph = self.doc.add_paragraph(style=self.style("Quote") if quote else None)
            if quote > 1:
                paragraph.paragraph_format.left_indent = Inches(0.4 * quote)
            self.inlines(paragraph, block.children)
        elif isinstance(block, n.CodeBlock):
            self.code(block)
        elif isinstance(block, n.BlockQuote):
            self.blocks(block.children, quote + 1)
        elif isinstance(block, n.List):
            self.list_block(block, depth=1, quote=quote)
        elif isinstance(block, n.ThematicBreak):
            self.thematic_break()
        elif isinstance(block, n.HtmlBlock):
            self.doc.add_paragraph(block.text)  # shown as written: Word cannot render HTML
        elif isinstance(block, n.Table):
            self.table(block)

    def heading(self, heading: n.Heading) -> None:
        if not n.plain_text(heading.children).strip():
            return
        paragraph = self.doc.add_paragraph(style=self.style(f"Heading {heading.level}"))
        self.inlines(paragraph, heading.children)

    def code(self, block: n.CodeBlock) -> None:
        if block.fenced and not block.closed:
            logger.warning(
                f"Unclosed code fence at line {block.line} of '{self.name}': "
                "keeping the remaining lines as a code block"
            )
        paragraph = self.doc.add_paragraph(style=self.style(CODE_STYLE))
        paragraph.add_run(block.text)

    def thematic_break(self) -> None:
        paragraph = self.doc.add_paragraph()
        border = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        for key, value in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "999999")):
            bottom.set(qn(f"w:{key}"), value)
        border.append(bottom)
        paragraph._p.get_or_add_pPr().append(border)

    # --- lists ----------------------------------------------------------------------------------

    def list_block(self, node: n.List, depth: int, quote: int) -> None:
        level = min(depth, MAX_LIST_DEPTH)
        base = "List Number" if node.ordered else "List Bullet"
        style = self.style(base if level == 1 else f"{base} {level}")
        numbering = self.restart_numbering(style, node.start or 1) if node.ordered else None
        continuation = self.style("List Continue" if level == 1 else f"List Continue {level}")

        for item in node.children:
            first = True
            for child in item.children:
                if first:
                    paragraph = self.doc.add_paragraph(style=style)
                    if numbering:
                        _set_numbering(paragraph, *numbering)
                    first = False
                    if isinstance(child, n.Paragraph):
                        self.inlines(paragraph, child.children)
                        continue
                if isinstance(child, n.List):
                    self.list_block(child, depth + 1, quote)
                elif isinstance(child, n.Paragraph):
                    self.inlines(self.doc.add_paragraph(style=continuation), child.children)
                else:
                    self.block(child, quote)
            if first:  # an item with no content still keeps its bullet or number
                paragraph = self.doc.add_paragraph(style=style)
                if numbering:
                    _set_numbering(paragraph, *numbering)

    def restart_numbering(self, style_name: str, start: int) -> tuple[int, int] | None:
        """Start a new numbered list from ``start``, so separate lists do not continue each other.

        Returns the ``(numId, ilvl)`` to put on each item, or None if the template cannot do it.
        """
        try:
            properties = self.doc.styles[style_name].element.pPr
            num_pr = properties.find(qn("w:numPr"))
            num_id = int(num_pr.find(qn("w:numId")).get(qn("w:val")))
            ilvl_element = num_pr.find(qn("w:ilvl"))
            ilvl = int(ilvl_element.get(qn("w:val"))) if ilvl_element is not None else 0
            definitions = self.doc.part.numbering_part.numbering_definitions._numbering
            base = next(num for num in definitions.num_lst if num.numId == num_id)
            new = definitions.add_num(base.abstractNumId.val)
            new.add_lvlOverride(ilvl=ilvl).add_startOverride(start)
            return new.numId, ilvl
        except (AttributeError, KeyError, NotImplementedError, StopIteration, TypeError, ValueError):
            if not self.restart_warned:
                logger.warning(
                    "The template's numbered list style cannot be restarted, so separate numbered lists "
                    "may continue each other's numbering"
                )
                self.restart_warned = True
            return None

    # --- tables ---------------------------------------------------------------------------------

    def table(self, node: n.Table) -> None:
        columns = max((len(row.children) for row in node.children), default=0)
        if not columns:
            return
        table = self.doc.add_table(rows=len(node.children), cols=columns)
        if "Table Grid" in self.style_names:
            table.style = "Table Grid"
        for word_row, row in zip(table.rows, node.children):
            for index, cell in enumerate(row.children):
                paragraph = word_row.cells[index].paragraphs[0]
                if cell.align:
                    paragraph.alignment = _ALIGNMENT[cell.align]
                self.inlines(paragraph, cell.children, _Format(bold=row.header))

    # --- inline ---------------------------------------------------------------------------------

    def inlines(self, paragraph, nodes: list[n.Inline], fmt: _Format = _Format()) -> None:
        for node in nodes:
            if isinstance(node, (n.Text, n.HtmlInline)):
                self.run(paragraph, node.text, fmt)
            elif isinstance(node, n.CodeSpan):
                self.run(paragraph, node.text, replace(fmt, code=True))
            elif isinstance(node, n.SoftBreak):
                self.run(paragraph, " ", fmt)
            elif isinstance(node, n.HardBreak):
                paragraph.add_run().add_break()
            elif isinstance(node, n.Emphasis):
                self.inlines(paragraph, node.children, replace(fmt, italic=True))
            elif isinstance(node, n.Strong):
                self.inlines(paragraph, node.children, replace(fmt, bold=True))
            elif isinstance(node, n.Link):
                self.link(paragraph, node, fmt)
            elif isinstance(node, n.Image):
                self.image(paragraph, node, fmt)

    def run(self, paragraph, text: str, fmt: _Format):
        run = paragraph.add_run(text)
        if fmt.bold:
            run.bold = True
        if fmt.italic:
            run.italic = True
        if fmt.code:
            run.font.name = CODE_FONT
        if fmt.link:
            if self.has_link_style:
                run.style = "Hyperlink"
            else:
                run.font.color.rgb = RGBColor(5, 99, 193)
                run.font.underline = True
        return run

    def link(self, paragraph, node: n.Link, fmt: _Format) -> None:
        inner = replace(fmt, link=True)
        if not node.url:
            self.inlines(paragraph, node.children, fmt)
            return
        start = len(paragraph._p)
        self.inlines(paragraph, node.children, inner)
        if len(paragraph._p) == start:  # [](url) has no text, so show the address
            self.run(paragraph, node.url, inner)
        self.wrap_in_hyperlink(paragraph, start, node.url, node.title)

    def wrap_in_hyperlink(self, paragraph, start: int, url: str, title: str | None) -> None:
        """Move the runs added since child index ``start`` inside a ``w:hyperlink`` element."""
        runs = list(paragraph._p)[start:]
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True))
        hyperlink.set(qn("w:history"), "1")
        if title:
            hyperlink.set(qn("w:tooltip"), title)
        paragraph._p.append(hyperlink)
        for element in runs:
            hyperlink.append(element)

    def image(self, paragraph, node: n.Image, fmt: _Format) -> None:
        path = self.local_image(node.url)
        if path is not None:
            try:
                shape = paragraph.add_run().add_picture(str(path))
            except (UnrecognizedImageError, OSError):
                logger.warning(f"Image '{node.url}' in '{self.name}' is not a supported picture")
            else:
                self.fit_to_page(shape)
                shape._inline.docPr.set("descr", node.alt)
                return
        else:
            logger.warning(f"Image '{node.url}' in '{self.name}' is not a local file, so it is not embedded")
        # Keep the alt text, linked to the picture's address, so nothing disappears silently.
        start = len(paragraph._p)
        self.run(paragraph, f"[Image: {node.alt or node.url}]", replace(fmt, italic=True, link=bool(node.url)))
        if node.url:
            self.wrap_in_hyperlink(paragraph, start, node.url, node.title)

    def local_image(self, url: str) -> Path | None:
        # A URL scheme has two or more characters, so a Windows drive such as C: is still a path.
        if not url or re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", url):
            return None
        path = Path(unquote(url))
        if not path.is_absolute():
            path = self.base_dir / path
        return path if path.is_file() else None

    def fit_to_page(self, shape) -> None:
        section = self.doc.sections[-1]
        try:
            available = section.page_width - section.left_margin - section.right_margin
        except TypeError:
            available = Inches(6)
        if shape.width > available:
            ratio = available / shape.width
            shape.height = Emu(int(shape.height * ratio))
            shape.width = Emu(int(available))


def _set_numbering(paragraph, num_id: int, ilvl: int) -> None:
    num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
    num_pr.get_or_add_ilvl().val = ilvl
    num_pr.get_or_add_numId().val = num_id


class DocxConverter:
    """
    Converts Markdown technical documentation into Word (.docx) documents based on createdocs specification.
    """

    def __init__(
        self,
        template_path: Optional[Path] = None,
        allow_missing_template: bool = False,
        keep_template_body: bool = False,
    ):
        """
        Args:
            template_path: Optional reference Word (.docx) template.
            allow_missing_template: If False (the default), a template path that is not
                an existing file raises FileNotFoundError. If True, a warning is logged
                and a default blank document is used instead.
            keep_template_body: If False (the default), the template's body content
                (cover page, placeholder text) is removed and only its styles, page
                setup of the final section, headers, footers and properties are used.
                If True, the converted content is appended after the template body.
        """
        self.template_path = Path(template_path) if template_path else None
        self.allow_missing_template = allow_missing_template
        self.keep_template_body = keep_template_body

    @staticmethod
    def _clear_body(doc):
        """Remove all body content except the final section properties."""
        body = doc.element.body
        for child in list(body):
            if child.tag != qn("w:sectPr"):
                body.remove(child)

    @staticmethod
    def _read_markdown(md_path: Path) -> str:
        """Return the source text, safe to hand to python-docx."""
        try:
            # utf-8-sig drops a byte order mark; universal newlines turn CRLF and CR into LF.
            content = md_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ConversionError(f"Cannot read '{md_path}': it is not valid UTF-8 ({exc.reason})") from exc

        content, removed = XML_INVALID_RE.subn("", content)
        if removed:
            logger.warning(
                f"Removed {removed} control character(s) that Word documents cannot hold from '{md_path.name}'"
            )
        return content

    def convert_file(self, md_path: Path, output_path: Path) -> Path:
        md_path = Path(md_path).resolve()
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")

        logger.info(f"Converting Markdown '{md_path.name}' -> Word '{output_path.name}'...")

        if self.template_path and self.template_path.is_file():
            doc = Document(str(self.template_path))
            logger.info(f"Loaded reference Word template: {self.template_path.name}")
            if not self.keep_template_body:
                self._clear_body(doc)
        elif self.template_path:
            if not self.allow_missing_template:
                raise FileNotFoundError(f"Word template not found: {self.template_path}")
            logger.warning(f"Word template not found, using a default blank document: {self.template_path}")
            doc = Document()
        else:
            doc = Document()

        text = self._read_markdown(md_path)
        try:
            document = parse(text)
            metadata = read_metadata(document)
        except (ParseError, FrontMatterError) as exc:
            raise ConversionError(f"Cannot convert '{md_path}': {exc}") from exc

        renderer = _Renderer(doc, md_path.parent, md_path.name)
        renderer.render(document)
        renderer.set_properties(metadata)

        doc.save(str(output_path))
        logger.info(f"Successfully generated Word document: {output_path}")
        return output_path
