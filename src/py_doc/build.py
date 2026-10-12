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
from .pandoc.source import join_sources
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
        )  # fmt: skip
        written.append(output)
        if report is not None:
            report.output(doc.id, fmt, output)
    return written


def render_output(
    fmt, joined, metadata, output, name, source_dirs, template, settings, runtime, keep_going=False, report=None
) -> Path:
    """Draw the diagrams of ``joined`` and have pandoc write ``output``. ``name`` is used in messages."""
    if runtime is None:
        raise ConversionError(f"Building {fmt} needs the tool container, but no runtime was given")
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
        drawn = render_parts(joined.parts, fmt, runtime, keep_going, events)
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
    job = PandocJob(fmt, drawn.markdown, metadata, output, source_dirs, template, settings, drawn.pictures)
    return convert(runtime(), job)


def _settings(config: ProjectConfig, doc: DocumentConfig, fmt: str):
    """The template and options for one output: the project defaults, overridden by the document."""
    default, own = config.outputs.get(fmt), doc.outputs.get(fmt)
    template = (own.template if own else None) or (default.template if default else None)
    options = {**(default.options if default else {}), **(own.options if own else {})}
    return template, options


def _first_word(renderer: str) -> str:
    """The program a diagram renderer runs, for the tool versions of the report."""
    from .diagrams.registry import RENDERERS, Job

    for renderer_ in RENDERERS:
        if renderer_.name == renderer:
            probe = renderer_.commands(Job(Path("d"), Path("d.png"), "png"))
            return str(probe[0][0]) if probe and probe[0] else renderer
    return renderer
