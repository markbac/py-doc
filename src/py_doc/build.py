"""Build the documents of a ``py-doc.yml``: join each document's source files, then render it."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from . import directives
from .config import DocumentConfig, ProjectConfig
from .diagrams import render_parts
from .errors import ConversionError
from .markdown import FrontMatterError, Metadata, ParseError, parse, plain_text, read_metadata
from .markdown import nodes as n
from .pandoc import PandocJob, convert
from .pandoc.source import join_sources
from .runtime import Runtime
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


def _combine_metadata(doc: DocumentConfig, first: Metadata, heading: str | None) -> Metadata:
    """Properties from the configuration, then the first source's front matter, then its first heading."""
    configured = doc.metadata()
    merged = Metadata(
        **{
            name: getattr(configured, name) or getattr(first, name)
            for name in ("title", "subtitle", "author", "date", "version", "status", "document_id", "keywords")
        },
        extra={**first.extra, **configured.extra},
    )
    return replace(merged, title=heading or doc.id) if merged.title is None else merged


def merge_document(doc: DocumentConfig, variables: dict | None = None, conditions: dict | None = None) -> Merged:
    """Join the included sources of ``doc`` into one document, with the configured properties applied.

    ``variables`` and ``conditions`` are added to the document's own, and win over them.
    """
    variables = {**doc.variables, **(variables or {})}
    conditions = {**doc.conditions, **(conditions or {})}
    blocks: list = []
    first_metadata = Metadata()
    included = [source for source in doc.sources if source.include]
    if not included:
        raise ConversionError(f"Document '{doc.id}' has no sources to build")

    for index, source in enumerate(included):
        if not source.file.is_file():
            raise FileNotFoundError(f"Source for document '{doc.id}' not found: {source.file}")
        text = DocxConverter._read_markdown(source.file)
        text = directives.expand(text, source.file, variables, conditions)
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

    heading = next((b for b in blocks if isinstance(b, n.Heading)), None)
    merged = _combine_metadata(doc, first_metadata, plain_text(heading.children) if heading else None)
    return Merged(n.Document(None, blocks), merged)


def _engine(fmt: str, settings: dict) -> str:
    """PDF and HTML are made by pandoc. Word and PowerPoint use the renderer chosen under ``engine``."""
    return "pandoc" if fmt in ("pdf", "html") else settings.get("engine", "native")


def build_document(
    config: ProjectConfig,
    doc: DocumentConfig,
    formats: list[str] | None = None,
    variables: dict | None = None,
    conditions: dict | None = None,
    runtime: Callable[[], Runtime] | None = None,
    keep_going: bool = False,
) -> list[Path]:
    """Build one document in each of ``formats`` (default: the ones it lists). Returns the files written.

    ``runtime`` returns the tool container runtime, and is only called when a pandoc output needs it.
    With ``keep_going`` every broken diagram is reported at once instead of stopping at the first.
    """
    chosen = formats or config.output_formats(doc)
    plans = [(fmt, *_settings(config, doc, fmt)) for fmt in chosen]
    merged = joined = None
    written: list[Path] = []
    for fmt, template, settings in plans:
        if _engine(fmt, settings) == "pandoc":
            if joined is None:
                joined = join_sources(
                    [s for s in doc.sources], {**doc.variables, **(variables or {})}, {**doc.conditions, **(conditions or {})}, doc.id
                )
            written.append(_pandoc_output(config, doc, fmt, template, settings, joined, runtime, keep_going))
            continue
        if merged is None:
            merged = merge_document(doc, variables, conditions)
        base = doc.sources[0].file.parent
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


def _pandoc_output(config, doc, fmt, template, settings, joined, runtime, keep_going) -> Path:
    if runtime is None:
        raise ConversionError(f"Building {fmt} needs the tool container, but no runtime was given")
    if template is not None and not template.is_file() and settings.get("allow_missing_template", False):
        logger.warning(f"Template {template} not found, so {doc.id}.{fmt} is built without it")
        template = None
    metadata = _combine_metadata(doc, joined.metadata, joined.first_heading)
    drawn = render_parts(joined.parts, fmt, runtime, keep_going)
    job = PandocJob(
        fmt, drawn.markdown, metadata, config.output_path(doc, fmt),
        sorted({s.file.parent for s in doc.sources if s.include}), template, settings, drawn.pictures,
    )  # fmt: skip
    return convert(runtime(), job)


def _settings(config: ProjectConfig, doc: DocumentConfig, fmt: str):
    """The template and options for one output: the project defaults, overridden by the document."""
    default, own = config.outputs.get(fmt), doc.outputs.get(fmt)
    template = (own.template if own else None) or (default.template if default else None)
    options = {**(default.options if default else {}), **(own.options if own else {})}
    return template, options
