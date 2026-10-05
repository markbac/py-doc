"""Render Markdown as a PowerPoint (.pptx) deck.

The Markdown is parsed once by :mod:`py_doc.markdown`. The document is cut into slides, and each slide
is written into a layout chosen by its placeholders, so a reference template controls the look.
Nothing is dropped silently: whatever a slide cannot show is moved to a following slide or reported.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from zipfile import BadZipFile

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.exc import PythonPptxError
from pptx.oxml.ns import qn
from pptx.parts.image import Image
from pptx.util import Inches, Pt

from py_doc.errors import ConversionError
from py_doc.files import template_source, write_output
from py_doc.markdown import FrontMatterError, Metadata, ParseError, parse, plain_text, read_metadata
from py_doc.markdown import nodes as n

logger = logging.getLogger(__name__)

# Characters that cannot appear in an XML 1.0 document (python-pptx rejects them).
XML_INVALID_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")

NOTES_RE = re.compile(r"^<!--\s*notes?:\s*(.*?)\s*-->$", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"^<!--.*-->$", re.DOTALL)

CODE_FONT = "Consolas"
CODE_SIZE = Pt(11)
CODE_COLOUR = RGBColor(30, 41, 59)
TABLE_SIZE = Pt(14)
MAX_LEVEL = 8  # PowerPoint paragraph levels run from 0 to 8
LINES_PER_SLIDE = 16  # beyond this a slide is probably too full to read

_TITLE_TYPES = (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)
_BODY_TYPES = (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT)
_ALIGNMENT = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}


@dataclass(frozen=True)
class _Format:
    bold: bool = False
    italic: bool = False
    code: bool = False


@dataclass
class _Slide:
    title: str | None
    blocks: list[n.Block]
    notes: list[str] = field(default_factory=list)
    subtitle: list[str] = field(default_factory=list)  # lines under the title of a title slide
    is_title: bool = False
    title_level: int | None = None  # heading level the title came from, if it came from a heading


@dataclass
class _Floats:
    """Tables and pictures, which are placed below the text because they cannot sit in a text frame."""

    tables: list[n.Table] = field(default_factory=list)
    images: list[tuple[Path, n.Image]] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.tables or self.images)


# --- cutting the document into slides --------------------------------------------------------------


def _chunks(blocks: list[n.Block], split_level: int) -> list[list[n.Block]]:
    """Cut top-level blocks at thematic breaks and at headings of ``split_level`` or shallower."""
    chunks: list[list[n.Block]] = [[]]
    for block in blocks:
        if isinstance(block, (n.ThematicBreak, n.PageBreak)):
            chunks.append([])
            continue
        if isinstance(block, n.Heading) and 0 < block.level <= split_level and chunks[-1]:
            chunks.append([])
        chunks[-1].append(block)
    return [chunk for chunk in chunks if chunk]


def _notes(blocks: list[n.Block]) -> tuple[list[n.Block], list[str]]:
    """Separate speaker notes (an HTML comment starting ``notes:``) and drop other HTML comments."""
    kept: list[n.Block] = []
    notes: list[str] = []
    for block in blocks:
        if isinstance(block, n.HtmlBlock):
            if match := NOTES_RE.match(block.text.strip()):
                notes.append(match.group(1))
                continue
            if COMMENT_RE.match(block.text.strip()):
                continue
        kept.append(block)
    return kept, notes


def build_slides(document: n.Document, metadata: Metadata, split_level: int) -> list[_Slide]:
    """The slides of ``document``. The first one is a title slide if it has a title."""
    slides: list[_Slide] = []
    for chunk in _chunks(document.children, split_level):
        blocks, notes = _notes(chunk)
        title, level = None, None
        for index, block in enumerate(blocks):
            if isinstance(block, n.Heading):
                title, level = plain_text(block.children).strip() or None, block.level
                blocks = blocks[:index] + blocks[index + 1 :]
                break
        slides.append(_Slide(title, blocks, notes, title_level=level))

    if not slides and (metadata.title or document.front_matter):
        slides.append(_Slide(None, []))
    if slides:
        _make_title_slide(slides, metadata)
    for position, slide in enumerate(slides, start=1):
        if slide.title is None:
            slide.title = f"Slide {position}"
    return slides


def _make_title_slide(slides: list[_Slide], metadata: Metadata) -> None:
    """Make the first slide a title slide if it is a top-level title with, at most, a subtitle paragraph.

    A first slide that also holds lists, code or tables stays a content slide, so nothing is lost
    and nothing is pushed onto a second slide. Front matter (subtitle, author, date) always goes on
    a title slide, and any body text then follows on a slide of its own.
    """
    first = slides[0]
    title = first.title or metadata.title
    if not title:
        return
    lines = [line for line in (metadata.subtitle, metadata.author, metadata.date) if line]
    only_a_subtitle = (
        first.title_level in (None, 1)
        and len(first.blocks) <= 1
        and all(isinstance(b, n.Paragraph) for b in first.blocks)
    )
    if not lines and not only_a_subtitle:
        first.title = title
        return
    first.title = title
    first.is_title = True
    if not lines and first.blocks:
        lines = [plain_text(first.blocks[0].children).strip()]
        first.blocks = []
    first.subtitle = lines
    if first.blocks:
        slides.insert(1, _Slide(f"{title} (continued)", first.blocks))
        first.blocks = []


# --- writing a slide -------------------------------------------------------------------------------


def _placeholder(slide, kinds) -> object | None:
    return next((p for p in slide.placeholders if p.placeholder_format.type in kinds), None)


def _remove(shape) -> None:
    element = shape._element
    element.getparent().remove(element)


def _no_bullet(paragraph) -> None:
    properties = paragraph._p.get_or_add_pPr()
    properties.set("marL", "0")
    properties.set("indent", "0")
    etree.SubElement(properties, qn("a:buNone"))


def _numbered(paragraph, start: int) -> None:
    properties = paragraph._p.get_or_add_pPr()
    bullet = etree.SubElement(properties, qn("a:buAutoNum"))
    bullet.set("type", "arabicPeriod")
    if start != 1:
        bullet.set("startAt", str(start))


class _Body:
    """Writes blocks as paragraphs of a text frame, collecting tables and pictures to place later."""

    def __init__(self, text_frame, base_dir: Path, name: str) -> None:
        self.frame = text_frame
        self.base_dir = base_dir
        self.name = name
        self.floats = _Floats()
        self.used_first = False
        self.lines = 0

    def paragraph(self):
        self.lines += 1
        if not self.used_first:
            self.used_first = True
            return self.frame.paragraphs[0]  # the frame starts with one empty paragraph
        return self.frame.add_paragraph()

    @property
    def has_text(self) -> bool:
        return self.used_first

    # blocks

    def blocks(self, blocks: list[n.Block], level: int = 0, quote: bool = False) -> None:
        for block in blocks:
            self.block(block, level, quote)

    def block(self, block: n.Block, level: int, quote: bool) -> None:
        fmt = _Format(italic=quote)
        if isinstance(block, n.Paragraph):
            self.text_paragraph(block.children, level + (1 if quote else 0), fmt)
        elif isinstance(block, n.Heading):
            self.text_paragraph(block.children, level, replace(fmt, bold=True))
        elif isinstance(block, n.CodeBlock):
            self.code(block, level)
        elif isinstance(block, n.List):
            self.list(block, level)
        elif isinstance(block, n.BlockQuote):
            self.blocks(block.children, level, quote=True)
        elif isinstance(block, n.Table):
            self.floats.tables.append(block)
        elif isinstance(block, n.HtmlBlock):
            if not COMMENT_RE.match(block.text.strip()):
                self.text_paragraph([n.Text(block.line, block.text)], level, fmt)

    def text_paragraph(self, nodes: list[n.Inline], level: int, fmt: _Format) -> None:
        """A paragraph with no bullet. A paragraph that holds only pictures adds none."""
        pending = len(self.floats.images)
        before = self.used_first
        paragraph = self.paragraph()
        self.inlines(paragraph, nodes, fmt)
        if len(self.floats.images) > pending and not paragraph.runs and not before:
            self.used_first = False  # nothing was written, so the frame's own paragraph is still free
            self.lines -= 1
            return
        if len(self.floats.images) > pending and not paragraph.runs:
            _remove_paragraph(paragraph)
            self.lines -= 1
            return
        paragraph.level = min(level, MAX_LEVEL)
        _no_bullet(paragraph)

    def code(self, block: n.CodeBlock, level: int) -> None:
        if block.fenced and not block.closed:
            logger.warning(
                f"Unclosed code fence at line {block.line} of '{self.name}': "
                "keeping the remaining lines as a code block"
            )
        paragraph = self.paragraph()
        for index, line in enumerate(block.text.split("\n")):
            if index:
                paragraph.add_line_break()
            if line:
                run = paragraph.add_run()
                run.text = line
                run.font.name = CODE_FONT
                run.font.size = CODE_SIZE
                run.font.color.rgb = CODE_COLOUR
        self.lines += block.text.count("\n")
        paragraph.level = min(level, MAX_LEVEL)
        _no_bullet(paragraph)

    def list(self, node: n.List, level: int) -> None:
        for item in node.children:
            first = True
            for child in item.children:
                if first and isinstance(child, n.Paragraph):
                    paragraph = self.paragraph()
                    self.inlines(paragraph, child.children, _Format())
                    paragraph.level = min(level, MAX_LEVEL)
                    if node.ordered:
                        _numbered(paragraph, node.start or 1)
                    first = False
                elif isinstance(child, n.List):
                    if first:  # an item that starts with a nested list still needs its own marker
                        self.empty_item(node, level)
                        first = False
                    self.list(child, level + 1)
                else:
                    if first:
                        self.empty_item(node, level)
                        first = False
                    self.block(child, level, quote=False)
            if first:
                self.empty_item(node, level)

    def empty_item(self, node: n.List, level: int) -> None:
        paragraph = self.paragraph()
        paragraph.level = min(level, MAX_LEVEL)
        if node.ordered:
            _numbered(paragraph, node.start or 1)

    # inline

    def inlines(self, paragraph, nodes: list[n.Inline], fmt: _Format, link: str | None = None) -> None:
        for node in nodes:
            if isinstance(node, (n.Text, n.HtmlInline)):
                self.run(paragraph, node.text, fmt, link)
            elif isinstance(node, n.CodeSpan):
                self.run(paragraph, node.text, replace(fmt, code=True), link)
            elif isinstance(node, n.SoftBreak):
                self.run(paragraph, " ", fmt, link)
            elif isinstance(node, n.HardBreak):
                paragraph.add_line_break()
            elif isinstance(node, n.Emphasis):
                self.inlines(paragraph, node.children, replace(fmt, italic=True), link)
            elif isinstance(node, n.Strong):
                self.inlines(paragraph, node.children, replace(fmt, bold=True), link)
            elif isinstance(node, n.Link):
                self.inlines(paragraph, node.children or [n.Text(node.line, node.url)], fmt, node.url or link)
            elif isinstance(node, n.Image):
                self.image(paragraph, node, fmt)

    def run(self, paragraph, text: str, fmt: _Format, link: str | None):
        run = paragraph.add_run()
        run.text = text
        if fmt.bold:
            run.font.bold = True
        if fmt.italic:
            run.font.italic = True
        if fmt.code:
            run.font.name = CODE_FONT
        if link:
            run.hyperlink.address = link
        return run

    def image(self, paragraph, node: n.Image, fmt: _Format) -> None:
        path = _local_image(self.base_dir, node.url)
        if path is not None and _is_picture(path):
            self.floats.images.append((path, node))
            return
        reason = "is not a supported picture" if path is not None else "is not a local file, so it is not embedded"
        logger.warning(f"Image '{node.url}' in '{self.name}' {reason}")
        self.run(paragraph, f"[Image: {node.alt or node.url}]", replace(fmt, italic=True), node.url or None)


def _remove_paragraph(paragraph) -> None:
    element = paragraph._p
    element.getparent().remove(element)


def _is_picture(path: Path) -> bool:
    try:
        image = Image.from_file(str(path))
        image.ext, image.size  # python-pptx reads the file lazily, so ask for what it will need
    except Exception:  # python-pptx raises a different error for each unsupported or damaged format
        return False
    return True


def _local_image(base_dir: Path, url: str) -> Path | None:
    # A URL scheme has two or more characters, so a Windows drive such as C: is still a path.
    if not url or re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", url):
        return None
    path = Path(unquote(url))
    if not path.is_absolute():
        path = base_dir / path
    return path if path.is_file() else None


# --- the converter ---------------------------------------------------------------------------------


_POTX_TYPE = b"application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
_PPTX_TYPE = b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"


class SlidesConverter:
    """
    Converts Markdown technical documentation into PowerPoint (.pptx) presentation decks.
    """

    def __init__(
        self,
        template_path: Optional[Path] = None,
        allow_missing_template: bool = False,
        keep_template_slides: bool = False,
        split_level: int = 2,
        title_layout: Optional[str] = None,
        content_layout: Optional[str] = None,
    ):
        """
        Args:
            template_path: Optional reference PowerPoint (.pptx) template.
            allow_missing_template: If False (the default), a template path that is not an
                existing file raises FileNotFoundError. If True, a warning is logged and the
                default blank presentation is used instead.
            keep_template_slides: If False (the default), slides already in the template are
                removed and only its masters and layouts are used.
            split_level: A heading of this level or shallower starts a new slide, as does a
                thematic break (``---``). Use 0 to split on thematic breaks only.
            title_layout: Name of the layout for the title slide. By default the layout named
                "Title Slide", or else the first with a title and a subtitle placeholder.
            content_layout: Name of the layout for other slides. By default "Title and Content",
                or else the first with a title and a body placeholder.
        """
        self.template_path = Path(template_path) if template_path else None
        self.allow_missing_template = allow_missing_template
        self.keep_template_slides = keep_template_slides
        self.split_level = split_level
        self.title_layout = title_layout
        self.content_layout = content_layout

    # reading

    @staticmethod
    def _read_markdown(md_path: Path) -> str:
        try:
            content = md_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ConversionError(f"Cannot read '{md_path}': it is not valid UTF-8 ({exc.reason})") from exc
        content, removed = XML_INVALID_RE.subn("", content)
        if removed:
            logger.warning(
                f"Removed {removed} control character(s) that PowerPoint files cannot hold from '{md_path.name}'"
            )
        return content

    # template

    def _open_template(self):
        if self.template_path and self.template_path.is_file():
            try:
                prs = Presentation(template_source(self.template_path, ".potx", _POTX_TYPE, _PPTX_TYPE))
            except (PythonPptxError, BadZipFile, KeyError, ValueError) as exc:
                raise ConversionError(f"Cannot read PowerPoint template '{self.template_path}': {exc}") from exc
            logger.info(f"Loaded reference PowerPoint template: {self.template_path.name}")
            if not self.keep_template_slides:
                self._remove_slides(prs)
            return prs
        if self.template_path:
            if not self.allow_missing_template:
                raise FileNotFoundError(f"PowerPoint template not found: {self.template_path}")
            logger.warning(f"PowerPoint template not found, using the default presentation: {self.template_path}")
        return Presentation()

    @staticmethod
    def _remove_slides(prs) -> None:
        ids = prs.slides._sldIdLst
        for slide_id in list(ids):
            prs.part.drop_rel(slide_id.rId)
            ids.remove(slide_id)

    @staticmethod
    def _layout_summary(prs) -> str:
        return ", ".join(f"'{layout.name}'" for layout in prs.slide_layouts) or "none"

    def _find_layout(self, prs, wanted: str | None, standard: str, kinds: tuple, role: str):
        """The layout named ``wanted``, else the standard one, else the first with the right placeholders."""

        def suitable(layout) -> bool:
            types = {p.placeholder_format.type for p in layout.placeholders}
            return bool(types & set(_TITLE_TYPES)) and bool(types & set(kinds))

        layouts = list(prs.slide_layouts)
        if wanted:
            for layout in layouts:
                if layout.name.lower() == wanted.lower():
                    if not suitable(layout):
                        raise ConversionError(
                            f"Layout '{layout.name}' cannot be used for {role} slides: it needs a title and a "
                            f"{'subtitle' if role == 'title' else 'body'} placeholder"
                        )
                    return layout
            raise ConversionError(
                f"The template has no layout named '{wanted}' for {role} slides. Layouts: {self._layout_summary(prs)}"
            )
        for layout in layouts:
            if layout.name.lower() == standard.lower() and suitable(layout):
                return layout
        return next((layout for layout in layouts if suitable(layout)), None)

    # converting

    def validate_template(self) -> None:
        """Raise now if the template cannot be used, so a batch fails once instead of for every file."""
        if self.template_path and not self.template_path.is_file() and self.allow_missing_template:
            return
        self._open_template()

    def convert_file(self, md_path: Path, output_path: Path) -> Path:
        md_path = Path(md_path).resolve()
        if not md_path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        text = self._read_markdown(md_path)
        try:
            document = parse(text)
            metadata = read_metadata(document)
        except (ParseError, FrontMatterError) as exc:
            raise ConversionError(f"Cannot convert '{md_path}': {exc}") from exc
        return self.convert_document(document, metadata, md_path.parent, md_path.name, output_path)

    def convert_document(
        self, document: n.Document, metadata: Metadata, base_dir: Path, name: str, output_path: Path
    ) -> Path:
        """Render a parsed document. ``base_dir`` is where relative image paths start, ``name`` is for messages."""
        output_path = Path(output_path).resolve()
        logger.info(f"Converting Markdown '{name}' -> PowerPoint '{output_path.name}'...")
        prs = self._open_template()

        title_layout = self._find_layout(prs, self.title_layout, "Title Slide", (PP_PLACEHOLDER.SUBTITLE,), "title")
        content_layout = self._find_layout(prs, self.content_layout, "Title and Content", _BODY_TYPES, "content")
        if content_layout is None:
            raise ConversionError(
                "The template has no layout with a title and a body placeholder for content slides. "
                f"Layouts: {self._layout_summary(prs)}. Name one with content_layout"
            )

        slides = build_slides(document, metadata, self.split_level)
        if not slides:
            logger.warning(f"'{name}' has no content, so the presentation has no slides")
        if any(slide.is_title for slide in slides) and title_layout is None:
            logger.warning("The template has no title slide layout, so the title slide uses the content layout")

        for slide in slides:
            self._write(prs, slide, title_layout, content_layout, Path(base_dir), name)

        if metadata.title:
            prs.core_properties.title = metadata.title
        if metadata.author:
            prs.core_properties.author = metadata.author
        if metadata.keywords:
            prs.core_properties.keywords = metadata.keywords

        write_output(output_path, prs.save)
        logger.info(f"Successfully generated PowerPoint presentation ({len(slides)} slides): {output_path}")
        return output_path

    def _write(self, prs, slide: _Slide, title_layout, content_layout, base_dir: Path, name: str) -> None:
        if slide.is_title and title_layout is not None:
            self._write_title_slide(prs, slide, title_layout)
        else:
            self._write_content_slide(prs, slide, content_layout, base_dir, name)
        if slide.notes:
            prs.slides[-1].notes_slide.notes_text_frame.text = "\n\n".join(slide.notes)

    @staticmethod
    def _write_title_slide(prs, slide: _Slide, layout) -> None:
        created = prs.slides.add_slide(layout)
        title = _placeholder(created, _TITLE_TYPES)
        title.text = slide.title
        subtitle = _placeholder(created, (PP_PLACEHOLDER.SUBTITLE,))
        if slide.subtitle:
            subtitle.text = "\n".join(slide.subtitle)
        else:
            _remove(subtitle)

    def _write_content_slide(self, prs, slide: _Slide, layout, base_dir: Path, name: str) -> None:
        created = prs.slides.add_slide(layout)
        _placeholder(created, _TITLE_TYPES).text = slide.title
        body_shape = _placeholder(created, _BODY_TYPES)

        frame = body_shape.text_frame
        frame.word_wrap = True
        body = _Body(frame, base_dir, name)
        if slide.is_title:  # a title slide written with the content layout keeps its subtitle lines
            body.blocks([n.Paragraph(0, 0, [n.Text(0, line)]) for line in slide.subtitle])
        body.blocks(slide.blocks)

        if body.lines > LINES_PER_SLIDE:
            logger.warning(
                f"Slide '{slide.title}' in '{name}' has about {body.lines} lines, which may not fit. "
                "Split it with a thematic break or a heading"
            )
        if body.has_text:
            frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        if body.floats:
            self._place_floats(created, body_shape, body)
        if not body.has_text:
            _remove(body_shape)

    # tables and pictures

    def _place_floats(self, slide, body_shape, body: _Body) -> None:
        left, top, width, height = body_shape.left, body_shape.top, body_shape.width, body_shape.height
        if body.has_text:
            text_height = min(Inches(0.38) * max(body.lines, 1) + Inches(0.2), int(height * 0.6))
            body_shape.height = text_height
            top, height = top + text_height + Inches(0.1), height - text_height - Inches(0.1)
        count = len(body.floats.tables) + len(body.floats.images)
        gap = Inches(0.1)
        slice_height = max(int((height - gap * (count - 1)) / count), Inches(0.8))

        for table in body.floats.tables:
            self._table(slide, table, left, top, width, slice_height)
            top += slice_height + gap
        for path, image in body.floats.images:
            self._picture(slide, path, image, left, top, width, slice_height)
            top += slice_height + gap

    @staticmethod
    def _table(slide, node: n.Table, left, top, width, height) -> None:
        columns = max((len(row.children) for row in node.children), default=0)
        if not columns:
            return
        rows = len(node.children)
        shape = slide.shapes.add_table(rows, columns, left, top, width, min(height, Inches(0.4) * rows))
        table = shape.table
        for row_index, row in enumerate(node.children):
            for index, cell in enumerate(row.children):
                frame = table.cell(row_index, index).text_frame
                paragraph = frame.paragraphs[0]
                if cell.align:
                    paragraph.alignment = _ALIGNMENT[cell.align]
                helper = _Body(frame, Path("."), "")
                helper.used_first = True
                helper.inlines(paragraph, cell.children, _Format(bold=row.header))
                for run in paragraph.runs:
                    run.font.size = TABLE_SIZE

    @staticmethod
    def _picture(slide, path: Path, node: n.Image, left, top, width, height) -> None:
        picture = slide.shapes.add_picture(str(path), left, top)
        ratio = min(width / picture.width, height / picture.height, 1.0)
        picture.width = int(picture.width * ratio)
        picture.height = int(picture.height * ratio)
        picture.left = int(left + (width - picture.width) / 2)
        picture._element.nvPicPr.cNvPr.set("descr", node.alt)
