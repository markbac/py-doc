"""Convert single Markdown files, for the ``py-doc docx`` and ``py-doc slides`` commands and the Python API.

Both converters are thin: they run the same pandoc pipeline as ``py-doc build``, for one file.
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from .build import render_output
from .config import Source
from .errors import ConversionError
from .pandoc.source import join_sources
from .runtime import Runtime, connect

logger = logging.getLogger(__name__)


class _Converter:
    fmt = ""
    kind = ""
    template_suffixes: tuple[str, ...] = ()

    def __init__(
        self,
        template_path: Path | None = None,
        allow_missing_template: bool = False,
        runtime: Callable[[], Runtime] | None = None,
        **options,
    ) -> None:
        """``runtime`` returns the tool container runtime. By default one is connected on first use."""
        self.template_path = Path(template_path) if template_path else None
        self.options = {"allow_missing_template": allow_missing_template, **options}
        self._runtime = runtime
        self._connected: Runtime | None = None

    def runtime(self) -> Runtime:
        if self._runtime is not None:
            return self._runtime()
        if self._connected is None:
            self._connected = connect()
        return self._connected

    def validate_template(self) -> None:
        """Raise if the template is missing (unless that is allowed) or is not a ``self.kind`` template."""
        path = self.template_path
        if path is None:
            return
        if not path.is_file():
            if self.options["allow_missing_template"]:
                return
            raise FileNotFoundError(f"{self.kind} template not found: {path}")
        if path.suffix.lower() in self.template_suffixes and not zipfile.is_zipfile(path):
            raise ConversionError(
                f"Cannot read {self.kind} template '{path}': it is not a valid {' or '.join(self.template_suffixes)} file"
            )
        if path.suffix.lower() not in self.template_suffixes:
            raise ConversionError(
                f"The {self.kind} template must be one of {', '.join(self.template_suffixes)}: {path}"
            )

    def convert_file(self, md_path: Path, output_path: Path) -> Path:
        return self._render(md_path, output_path, self.fmt, self.template_path, self.options)

    def convert_twin(self, md_path: Path, output_path: Path) -> Path:
        """Write an HTML preview twin of the document or deck: the same Markdown, as a web page, for ``--watch``."""
        preview = "slides" if self.fmt == "pptx" else "document"
        return self._render(md_path, output_path, "html", None, {**self.options, "preview": preview})

    def _render(self, md_path: Path, output_path: Path, fmt: str, template: Path | None, options: dict) -> Path:
        md_path = Path(md_path).resolve()
        if not md_path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        joined = join_sources([Source(md_path)], {}, {}, md_path.name)
        if self.fmt == "pptx" and fmt == "html":  # speaker notes written as comments show in the twin too
            from .pandoc.pptx_finish import notes_to_divs

            joined = replace(joined, parts=[(src, notes_to_divs(md)) for src, md in joined.parts])
        metadata = joined.metadata
        if not metadata.title:
            metadata = replace(metadata, title=joined.first_heading or md_path.stem)
        return render_output(
            fmt, joined, metadata, Path(output_path), md_path.name, [md_path.parent], template,
            options, self.runtime, keep_going=False,
        )  # fmt: skip


class DocxConverter(_Converter):
    """Markdown to a Word document. The template, when given, is the reference document."""

    fmt, kind, template_suffixes = "docx", "Word", (".docx", ".dotx")


class SlidesConverter(_Converter):
    """Markdown to a PowerPoint deck. ``split_level`` is the heading level that starts a slide."""

    fmt, kind, template_suffixes = "pptx", "PowerPoint", (".pptx", ".potx")

    def __init__(self, *args, split_level: int = 2, **options) -> None:
        super().__init__(*args, split_level=split_level, **options)
