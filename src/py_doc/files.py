"""Finding Markdown files, shared by the converters and the linter."""

from __future__ import annotations

import io
import os
import zipfile
from collections.abc import Callable
from pathlib import Path

from .errors import ConversionError

MARKDOWN_SUFFIXES = (".md", ".markdown")

# Directories that are never documentation: hidden ones are skipped as well.
DEFAULT_EXCLUDE_DIRS = frozenset(
    {"node_modules", "venv", "env", "site-packages", "__pycache__", "dist", "build", "vendor"}
)


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() in MARKDOWN_SUFFIXES


def find_markdown(
    directory: Path,
    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS,
    skip: Path | None = None,
) -> list[Path]:
    """Markdown files below ``directory``, sorted by path.

    Hidden directories, ``exclude_dirs`` and the directory ``skip`` (such as an output folder
    inside the input) are not entered.
    """
    skip = skip.resolve() if skip else None
    found: list[Path] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = sorted(
            d
            for d in dirs
            if not d.startswith(".") and d not in exclude_dirs and (skip is None or (Path(root) / d).resolve() != skip)
        )
        found += [Path(root) / name for name in sorted(files) if is_markdown(Path(name))]
    return sorted(found)


def write_output(path: Path, save: Callable[[str], object]) -> None:
    """Create the parent directory and call ``save(path)``, turning OS failures into ``ConversionError``."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        save(str(path))
    except OSError as exc:
        raise ConversionError(f"Cannot write '{path}': {exc.strerror or exc}") from exc


def template_source(path: Path, suffix: str, template_type: bytes, document_type: bytes):
    """What to open for a template: ``path`` itself, or for a template file type (such as ``.dotx``)
    a copy whose content type is changed to the document one, which the Office libraries accept."""
    if path.suffix.lower() != suffix:
        return str(path)
    target = io.BytesIO()
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(template_type, document_type)
            zout.writestr(item, data)
    target.seek(0)
    return target
