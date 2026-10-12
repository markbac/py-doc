"""Run pandoc in the tool container for one output, and finish Word files on the host."""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from py_doc.diagrams import copy_pictures
from py_doc.errors import ConversionError
from py_doc.markdown import Metadata
from py_doc.runtime import Mount, Runtime

logger = logging.getLogger(__name__)

RESOURCES = Path(__file__).parent / "resources"
TIMEOUT = 900  # a large document with many pictures can take minutes in XeLaTeX
DEFAULT_TOC_DEPTH = 3
INPUT_FORMAT = "markdown+fenced_divs+raw_html+raw_attribute+table_captions+strikeout+task_lists"
FILTERS = {
    "docx": ("admonitions.lua", "pagebreak.lua"),
    "pptx": ("admonitions.lua", "pagebreak.lua"),
    "html": ("admonitions.lua", "pagebreak.lua"),
    "pdf": ("admonitions.lua", "pagebreak.lua", "center-div.lua"),
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


def _metadata_file(metadata: Metadata) -> dict[str, Any]:
    """The pandoc metadata for a document. Names with underscores become the dashed names templates use."""
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
    return {key: str(value) for key, value in values.items() if value not in (None, "")}


def _command(job: PandocJob, runtime: Runtime, work: Path) -> tuple[list, list[Mount]]:
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
        "--highlight-style", _required(THEME, "highlight theme"),
        "--output", produced,
    ]  # fmt: skip
    for name in FILTERS[fmt]:
        argv += ["--lua-filter", _required(RESOURCES / name, "Lua filter")]
    toc_depth = job.metadata.extra.get("toc_depth", DEFAULT_TOC_DEPTH)
    argv.append(f"--toc-depth={toc_depth}")

    if fmt == "docx":
        argv.append("--to=docx+native_numbering")
        if job.template is not None:
            argv += ["--reference-doc", job.template]
    elif fmt == "pptx":
        argv.append("--to=pptx")
        argv.append(f"--slide-level={options.get('split_level', 2)}")
        if job.template is not None:
            argv += ["--reference-doc", job.template]
    elif fmt == "html":
        argv += ["--to=html5", "--standalone", "--embed-resources"]
        argv += ["--css", job.template if job.template is not None else _required(RESOURCES / "html.css", "stylesheet")]
        if options.get("toc", False):
            argv.append("--toc")
    else:  # pdf
        argv += ["--pdf-engine=xelatex"]
        argv += ["--template", job.template if job.template is not None else _required(RESOURCES / "latex_template.tex", "LaTeX template")]
        if options.get("toc", True):
            argv.append("--toc")
    return argv, mounts


def convert(runtime: Runtime, job: PandocJob) -> Path:
    """Write ``job.output``. Raises ConversionError (or ToolFailed) with pandoc's own message on failure."""
    if job.template is not None:
        _required(job.template, "template")
    with tempfile.TemporaryDirectory(prefix="py-doc-") as folder:
        work = Path(folder)
        (work / "combined.md").write_text(job.markdown, encoding="utf-8", newline="\n")
        copy_pictures(job.pictures, work)
        (work / "metadata.yaml").write_text(
            yaml.safe_dump(_metadata_file(job.metadata), allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        argv, mounts = _command(job, runtime, work)
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
        job.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(produced, job.output)
        except PermissionError as exc:
            raise ConversionError(f"Cannot write {job.output}: it is locked (open in another program?)") from exc
    logger.info(f"Wrote {job.output}")
    return job.output
