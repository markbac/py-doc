"""Run pandoc in the tool container for one output, and finish Word files on the host."""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from py_doc.diagrams import copy_pictures
from py_doc.errors import ConversionError, OutputLocked
from py_doc.files import template_source
from py_doc.markdown import Metadata
from py_doc.runtime import Mount, Runtime

from .pptx_finish import notes_to_divs
from .source import first_heading
from .reference import default_reference, missing_callout_styles, text_width_cm

logger = logging.getLogger(__name__)

RESOURCES = Path(__file__).parent / "resources"
TIMEOUT = 900  # a large document with many pictures can take minutes in XeLaTeX
DEFAULT_TOC_DEPTH = 3
INPUT_FORMAT = "markdown+fenced_divs+raw_html+raw_attribute+table_captions+strikeout+task_lists"
FILTERS = {
    "docx": ("admonitions.lua", "pagebreak.lua", "widths.lua"),
    "pptx": ("admonitions.lua", "pagebreak.lua", "markers.lua"),
    "html": ("admonitions.lua", "pagebreak.lua", "markers.lua"),
    "pdf": ("admonitions.lua", "pagebreak.lua", "center-div.lua", "markers.lua"),
}
THEME = RESOURCES / "createdocs.theme"


@dataclass
class PandocJob:
    """Everything pandoc needs for one output file."""

    fmt: str  # docx, pptx, pdf or html
    markdown: str
    metadata: Metadata
    output: Path
    source_dirs: list[Path] = field(default_factory=list)
    template: Path | None = None  # Word/PowerPoint reference document, LaTeX template for PDF, CSS for HTML
    options: dict[str, Any] = field(default_factory=dict)
    pictures: dict[str, Path] = field(default_factory=dict)  # name in the document -> file, from the diagram renderers


def _required(path: Path, what: str) -> Path:
    if not path.is_file():
        raise ConversionError(f"The {what} was not found: {path}")
    return path


def _metadata_file(metadata: Metadata, fmt: str, markdown: str) -> dict[str, Any]:
    """The pandoc metadata for a document. Names with underscores become the dashed names templates use.

    A title that is the first heading is not given to pandoc as the title, because the document would then
    show it twice (as the title and as the heading). The page title of HTML is still set.
    """
    values: dict[str, Any] = {
        "title": metadata.title,
        "subtitle": metadata.subtitle,
        "author": metadata.author,
        "date": metadata.date,
        "version": metadata.version,
        "status": metadata.status,
        "document-number": metadata.document_id,
        "keywords": metadata.keywords,
    }
    for key, value in metadata.extra.items():
        values.setdefault(str(key).replace("_", "-"), value)
    if values["title"] and values["title"] == first_heading(markdown):
        del values["title"]
        if fmt == "html":
            values["pagetitle"] = metadata.title
    return {key: str(value) for key, value in values.items() if value not in (None, "")}


_OFFICE = "application/vnd.openxmlformats-officedocument"
_TEMPLATE_TYPES = {  # template file type -> (its content type, the document one, the document suffix)
    ".dotx": (f"{_OFFICE}.wordprocessingml.template.main+xml", f"{_OFFICE}.wordprocessingml.document.main+xml", ".docx"),
    ".potx": (f"{_OFFICE}.presentationml.template.main+xml", f"{_OFFICE}.presentationml.presentation.main+xml", ".pptx"),
}


def _as_document(template: Path, work: Path) -> Path:
    """pandoc and the Office libraries only take documents, so a .dotx or .potx is copied as one."""
    if template.suffix.lower() in (".docx", ".dotx", ".pptx", ".potx") and not zipfile.is_zipfile(template):
        raise ConversionError(f"The template '{template}' is not a valid {template.suffix} file")
    kind = _TEMPLATE_TYPES.get(template.suffix.lower())
    if kind is None:
        return template
    copy = work / f"template{kind[2]}"
    copy.write_bytes(template_source(template, template.suffix.lower(), kind[0].encode(), kind[1].encode()).getvalue())
    return copy


def _pandoc_version(runtime: Runtime) -> tuple[int, ...]:
    """The pandoc version, asked once per runtime. The tool image pins a recent one. A host pandoc may be older."""
    known = getattr(runtime, "_pandoc_version", None)
    if known is None:
        try:
            first = runtime.run(["pandoc", "--version"], timeout=60, check=False).stdout.split("\n", 1)[0]
            known = tuple(int(n) for n in re.findall(r"\d+", first.split()[-1]))
        except Exception:  # noqa: BLE001 - an unreadable version means the pinned, recent pandoc
            known = ()
        known = known or (99,)
        try:
            runtime._pandoc_version = known
        except AttributeError:
            pass
    return known


def _highlight_option(runtime: Runtime) -> str:
    """pandoc 3.8 renamed ``--highlight-style`` to ``--syntax-highlighting`` and warns about the old name."""
    return "--syntax-highlighting" if _pandoc_version(runtime) >= (3, 8) else "--highlight-style"


def _command(job: PandocJob, runtime: Runtime, work: Path, reference: Path | None) -> tuple[list, list[Mount]]:
    options = job.options
    fmt = job.fmt
    mounts = [Mount(RESOURCES), Mount(work, writable=True)]
    mounts += [Mount(directory) for directory in dict.fromkeys(job.source_dirs)]
    if job.template is not None:
        mounts.append(Mount(job.template.parent))

    search = [runtime.container_path(work), *(runtime.container_path(d) for d in dict.fromkeys(job.source_dirs))]
    produced = work / f"result.{fmt}"
    argv: list = [
        "pandoc", work / "combined.md", f"--from={INPUT_FORMAT}",
        f"--resource-path={':'.join(search)}",
        "--metadata-file", work / "metadata.yaml",
        _highlight_option(runtime), _required(THEME, "highlight theme"),
        "--output", produced,
    ]  # fmt: skip
    for name in FILTERS[fmt]:
        argv += ["--lua-filter", _required(RESOURCES / name, "Lua filter")]
    toc_depth = job.metadata.extra.get("toc_depth", DEFAULT_TOC_DEPTH)
    argv.append(f"--toc-depth={toc_depth}")

    if fmt == "docx":
        argv.append("--to=docx+native_numbering")
        if reference is not None:
            argv += ["--reference-doc", reference]
        if options.get("toc", False):
            argv.append("--toc")
    elif fmt == "pptx":
        argv.append("--to=pptx")
        argv.append(f"--slide-level={options.get('split_level', 2)}")
        if job.template is not None:
            argv += ["--reference-doc", job.template]
    elif fmt == "html":
        argv += ["--to=html5", "--standalone", "--embed-resources", "--mathml"]
        argv += ["--css", job.template if job.template is not None else _required(RESOURCES / "html.css", "stylesheet")]
        if options.get("preview", False):  # the HTML twin of a document or deck, for --watch
            argv += ["--css", _required(RESOURCES / "preview.css", "stylesheet")]
        if options.get("toc", False):
            argv.append("--toc")
    else:  # pdf
        argv += ["--pdf-engine=xelatex"]
        argv += ["--template", job.template if job.template is not None else _required(RESOURCES / "latex_template.tex", "LaTeX template")]
        if options.get("toc", True):
            argv.append("--toc")
    if fmt in ("pdf", "html") and options.get("number_sections", False):
        argv.append("--number-sections")
    return argv, mounts


def convert(runtime: Runtime, job: PandocJob) -> Path:
    """Write ``job.output``. Raises ConversionError (or ToolFailed) with pandoc's own message on failure."""
    if job.template is not None:
        _required(job.template, "template")
    with tempfile.TemporaryDirectory(prefix="py-doc-") as folder:
        work = Path(folder)
        markdown = notes_to_divs(job.markdown) if job.fmt == "pptx" else job.markdown
        (work / "combined.md").write_text(markdown, encoding="utf-8", newline="\n")
        copy_pictures(job.pictures, work)
        if job.template is not None:
            job = replace(job, template=_as_document(job.template, work))
        metadata = _metadata_file(job.metadata, job.fmt, job.markdown)
        reference = None
        if job.fmt == "docx":
            reference = job.template if job.template is not None else default_reference(runtime, work)
            metadata["text-width-cm"] = f"{text_width_cm(reference):.2f}"  # for widths.lua
            if job.template is not None:
                missing = missing_callout_styles(job.template, job.markdown)
                if missing:
                    logger.warning(
                        f"The template {job.template.name} has no style {', '.join(missing)}, so callouts of "
                        "those kinds are plain paragraphs. Add a paragraph style with that name to give them a box"
                    )
        (work / "metadata.yaml").write_text(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False), encoding="utf-8")
        argv, mounts = _command(job, runtime, work, reference)
        result = runtime.run(argv, mounts=mounts, workdir=work, timeout=TIMEOUT)
        for line in result.stderr.splitlines():
            if line.startswith("[WARNING]"):
                logger.warning(f"pandoc: {line.removeprefix('[WARNING]').strip()}")
        produced = work / f"result.{job.fmt}"
        if not produced.is_file():
            raise ConversionError(f"pandoc finished but wrote no {job.fmt} file")
        if job.fmt == "docx":
            from .docx_finish import finish_docx

            finish_docx(produced, job.template, job.metadata, job.options)
        elif job.fmt == "pptx":
            from .pptx_finish import finish_pptx

            finish_pptx(produced, job.metadata, job.options)
        try:
            job.output.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(produced, job.output)
        except PermissionError as exc:
            raise OutputLocked(f"Cannot write {job.output}: it is locked (open in another program?)") from exc
        except OSError as exc:
            raise ConversionError(f"Cannot write '{job.output}': {exc.strerror or exc}") from exc
    logger.info(f"Wrote {job.output}")
    return job.output
