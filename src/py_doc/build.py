"""Build the documents of a ``py-doc.yml``: join each document's source files, then render it."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path

from .config import DocumentConfig, ProjectConfig
from .errors import ConversionError
from .markdown import FrontMatterError, Metadata, ParseError, parse, plain_text, read_metadata
from .markdown import nodes as n
from .render.docx import DocxConverter
from .render.pptx import SlidesConverter

logger = logging.getLogger(__name__)

_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")


@dataclass
class Merged:
    document: n.Document
    metadata: Metadata


def _absolute_images(blocks, source_dir: Path) -> None:
    """Point local pictures at their real place, because the joined document has no single folder."""
    for node in n.walk(n.Document(None, blocks)):
        if isinstance(node, n.Image) and node.url and not _SCHEME.match(node.url) and not node.url.startswith("#"):
            path = Path(node.url)
            if not path.is_absolute():
                node.url = (source_dir / path).as_posix()


def _shift_headings(blocks, offset: int, name: str) -> None:
    for node in n.walk(n.Document(None, blocks)):
        if isinstance(node, n.Heading):
            level = node.level + offset
            if not 1 <= level <= 6:
                logger.warning(f"Heading at line {node.line} of '{name}' would be level {level}, so it is kept in 1 to 6")
            node.level = min(6, max(1, level))


def _retitle(blocks: list, title: str) -> list:
    """Replace the first heading's text with ``title``, or put a heading first if the file has none."""
    for block in blocks:
        if isinstance(block, n.Heading):
            block.children = [n.Text(block.line, title)]
            return blocks
    return [n.Heading(1, 1, 1, [n.Text(1, title)]), *blocks]


def merge_document(doc: DocumentConfig) -> Merged:
    """Join the included sources of ``doc`` into one document, with the configured properties applied."""
    blocks: list = []
    first_metadata = Metadata()
    included = [source for source in doc.sources if source.include]
    if not included:
        raise ConversionError(f"Document '{doc.id}' has no sources to build")

    for index, source in enumerate(included):
        if not source.file.is_file():
            raise FileNotFoundError(f"Source for document '{doc.id}' not found: {source.file}")
        text = DocxConverter._read_markdown(source.file)
        try:
            parsed = parse(text)
            metadata = read_metadata(parsed)
        except (ParseError, FrontMatterError) as exc:
            raise ConversionError(f"Cannot convert '{source.file}': {exc}") from exc
        if index == 0:
            first_metadata = metadata
        body = parsed.children
        if source.title:
            body = _retitle(body, source.title)
        if source.heading_offset:
            _shift_headings(body, source.heading_offset, source.file.name)
        _absolute_images(body, source.file.parent)
        if index and source.page_break:
            blocks.append(n.PageBreak(0, 0))
        blocks += body

    configured = doc.metadata()
    merged = Metadata(
        **{
            name: getattr(configured, name) or getattr(first_metadata, name)
            for name in ("title", "subtitle", "author", "date", "version", "status", "document_id", "keywords")
        },
        extra={**first_metadata.extra, **configured.extra},
    )
    if merged.title is None:
        heading = next((b for b in blocks if isinstance(b, n.Heading)), None)
        merged = replace(merged, title=plain_text(heading.children) if heading else doc.id)
    return Merged(n.Document(None, blocks), merged)


def build_document(config: ProjectConfig, doc: DocumentConfig, formats: list[str] | None = None) -> list[Path]:
    """Build one document in each of ``formats`` (default: the ones it lists). Returns the files written."""
    merged = merge_document(doc)
    written: list[Path] = []
    base = doc.sources[0].file.parent
    for fmt in formats or config.output_formats(doc):
        template, settings = _settings(config, doc, fmt)
        if fmt == "docx":
            converter = DocxConverter(
                template_path=template,
                allow_missing_template=settings.get("allow_missing_template", False),
                keep_template_body=settings.get("keep_template_body", False),
            )
        else:
            converter = SlidesConverter(
                template_path=template,
                allow_missing_template=settings.get("allow_missing_template", False),
                keep_template_slides=settings.get("keep_template_slides", False),
                split_level=settings.get("split_level", 2),
                title_layout=settings.get("title_layout"),
                content_layout=settings.get("content_layout"),
            )
        converter.validate_template()
        written.append(
            converter.convert_document(merged.document, merged.metadata, base, doc.id, config.output_path(doc, fmt))
        )
    return written


def _settings(config: ProjectConfig, doc: DocumentConfig, fmt: str):
    """The template and options for one output: the project defaults, overridden by the document."""
    default, own = config.outputs.get(fmt), doc.outputs.get(fmt)
    template = (own.template if own else None) or (default.template if default else None)
    options = {**(default.options if default else {}), **(own.options if own else {})}
    return template, options
