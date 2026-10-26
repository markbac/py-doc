"""Build the documents of a ``py-doc.yml``: join each document's source files, then render it."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from .c4 import source as c4_source
from .config import DocumentConfig, ProjectConfig
from .diagrams import render_parts
from .errors import ConversionError
from .markdown import Metadata
from .naming import git_version, status_template
from .pandoc import PandocJob, convert
from .pandoc.source import join_sources, strip_heading_numbers
from .runtime import Runtime
from .report import BuildReport
from .template_check import log_problems

logger = logging.getLogger(__name__)


def _combine_metadata(doc: DocumentConfig, first: Metadata, heading: str | None, root: Path | None = None) -> Metadata:
    """Properties from the configuration, then the first source's front matter, then its first heading.

    A version of ``git`` is replaced by ``git describe`` for the repository of ``root``.
    """
    configured = doc.metadata()
    merged = Metadata(
        **{
            name: getattr(configured, name) or getattr(first, name)
            for name in ("title", "subtitle", "author", "date", "version", "status", "document_id", "keywords")
        },
        extra={**first.extra, **configured.extra},
    )
    if merged.title is None:
        merged = replace(merged, title=heading or doc.id)
    if merged.version == "git":
        merged = replace(merged, version=git_version(root or doc.sources[0].file.parent))
    return merged


def build_document(
    config: ProjectConfig,
    doc: DocumentConfig,
    formats: list[str] | None = None,
    variables: dict | None = None,
    conditions: dict | None = None,
    runtime: Callable[[], Runtime] | None = None,
    keep_going: bool = False,
    report: BuildReport | None = None,
) -> list[Path]:
    """Build one document in each of ``formats`` (default: the ones it lists). Returns the files written.

    ``runtime`` returns the tool container runtime, and is only called when a pandoc output needs it.
    With ``keep_going`` every broken diagram is reported at once instead of stopping at the first.
    A ``report`` collects the outputs, sources, diagrams and template problems.
    """
    chosen = formats or config.output_formats(doc)
    sources = c4_source.expand(list(doc.sources), doc.id, config.root, runtime, config.c4)
    plans = [(fmt, *_settings(config, doc, fmt)) for fmt in chosen]
    joined = None
    written: list[Path] = []
    for fmt, template, settings in plans:
        if joined is None:
            joined = join_sources(
                sources, {**doc.variables, **(variables or {})}, {**doc.conditions, **(conditions or {})}, doc.id
            )
        metadata = _combine_metadata(doc, joined.metadata, joined.first_heading, config.root)
        if report is not None and not report.document(doc.id)["sources"]:
            report.sources(doc.id, joined.parts)
        output = render_output(
            fmt, joined, metadata, config.output_path(doc, fmt, metadata.version), doc.id,
            sorted({s.file.parent for s in sources if s.include}), template, settings, runtime, keep_going, report,
            config.mermaid, blocks_theme(config),
        )  # fmt: skip
        written.append(output)
        if report is not None:
            report.output(doc.id, fmt, output)
    return written


def blocks_theme(config):
    """The theme of the poster blocks a document draws: ``diagrams.theme``, else None (``print``)."""
    if config.blocks_theme is None:
        return None
    from .diagrams.blocks import theme_for

    return theme_for(config.blocks_theme, config.root)


def render_output(
    fmt,
    joined,
    metadata,
    output,
    name,
    source_dirs,
    template,
    settings,
    runtime,
    keep_going=False,
    report=None,
    mermaid=None,
    theme=None,
) -> Path:
    """Draw the diagrams of ``joined`` and have pandoc write ``output``. ``name`` is used in messages."""
    if runtime is None:
        raise ConversionError(f"Building {fmt} needs the tool container, but no runtime was given")
    if fmt == "html" and settings.get("deck"):  # the slides as an HTML deck, drawn by the poster engine
        from .deck import write_deck

        base = joined.parts[0][0].parent if joined.parts else source_dirs[0]
        return write_deck(joined, metadata, output, base, settings, runtime, mermaid, name)
    template = status_template(template, metadata.status)
    if template is not None and not template.is_file() and settings.get("allow_missing_template", False):
        logger.warning(f"Template {template} not found, so {name}.{fmt} is built without it")
        template = None
    if template is not None and template.is_file() and fmt in ("docx", "pptx"):
        checked = log_problems(template, skip=("Callout styles",))  # the converter reports the callouts a document uses
        if report is not None and checked is not None:
            report.template(name, checked)
    events: list[dict] = []
    try:
        drawn = render_parts(joined.parts, fmt, runtime, keep_going, events, mermaid, theme)
    finally:
        if report is not None:
            for event in events:
                report.diagram(name, fmt, event)
    if report is not None:
        report.want_tool("pandoc")
        if fmt == "pdf":
            report.want_tool("xelatex")
        for event in events:
            report.want_tool(_first_word(event["type"]))
    markdown = drawn.markdown
    if _numbers_headings_itself(fmt, template, settings):
        stripped = strip_heading_numbers(markdown)
        if stripped != markdown:
            logger.info(
                f"{name}.{fmt} numbers its headings itself, so the numbers written in the headings are left out"
            )
        markdown = stripped
    job = PandocJob(fmt, markdown, metadata, output, source_dirs, template, settings, drawn.pictures)
    return convert(runtime(), job)


def _numbers_headings_itself(fmt: str, template: Path | None, settings: dict) -> bool:
    """Whether the output numbers its headings, so numbers written in the headings would show twice.

    ``heading_numbers: strip`` or ``keep`` says so. Otherwise (``auto``) a Word template whose heading styles
    are numbered does, and so does PDF or HTML with ``number_sections: true``.
    """
    choice = settings.get("heading_numbers", "auto")
    if choice != "auto":
        return choice == "strip"
    if fmt in ("pdf", "html"):
        return bool(settings.get("number_sections", False))
    if fmt == "docx" and template is not None and template.is_file():
        from .pandoc.reference import numbers_headings

        return numbers_headings(template)
    return False


def _settings(config: ProjectConfig, doc: DocumentConfig, fmt: str):
    """The template and options for one output: the project defaults, overridden by the document."""
    default, own = config.outputs.get(fmt), doc.outputs.get(fmt)
    template = (own.template if own else None) or (default.template if default else None)
    options = {**(default.options if default else {}), **(own.options if own else {})}
    if fmt == "html" and options.get("deck"):
        options = {**deck_options(config, doc), **options}
    return template, options


def deck_options(config: ProjectConfig, doc: DocumentConfig) -> dict:
    """The options of the HTML deck of ``doc``: its html output's, else those its PowerPoint deck shares with it
    (the slide level and footer), so the two decks are split and footed alike."""
    _, pptx = _settings(config, doc, "pptx") if "pptx" in doc.outputs else (None, {})
    shared = {key: pptx[key] for key in ("split_level", "footer") if key in pptx}
    own = doc.outputs.get("html")
    return {**shared, **(own.options if own and own.options.get("deck") else {}), "deck": True}


def deck_page(config: ProjectConfig, doc: DocumentConfig, runtime, variables=None, conditions=None):
    """The HTML deck of ``doc`` as a page, without writing it: for a site. Returns its page and title."""
    from .deck import DeckSettings, build_deck

    joined = join_sources(
        list(doc.sources), {**doc.variables, **(variables or {})}, {**doc.conditions, **(conditions or {})}, doc.id
    )
    metadata = _combine_metadata(doc, joined.metadata, joined.first_heading, config.root)
    settings = DeckSettings.from_options(deck_options(config, doc))
    base = joined.parts[0][0].parent if joined.parts else config.root
    page, _, _ = build_deck(joined.markdown, metadata, base, settings, runtime, config.mermaid, doc.id)
    return page, metadata.title or doc.id


def _first_word(renderer: str) -> str:
    """The program a diagram renderer runs, for the tool versions of the report."""
    from .diagrams.registry import RENDERERS, Job

    for renderer_ in RENDERERS:
        if renderer_.name == renderer:
            probe = renderer_.commands(Job(Path("d"), Path("d.png"), "png"))
            return str(probe[0][0]) if probe and probe[0] else renderer
    return renderer
