"""Turn a ``structurizr:`` source of py-doc.yml into Markdown files, with their pictures, for the build to join."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from py_doc.config import C4Settings, Source
from py_doc.errors import ConversionError
from py_doc.runtime import Runtime

from .generate import generate
from .model import load_workspace
from .render import render_views
from .lock import resolve_image
from .stack import SERVER_PORT, Stack
from .structurizr import StructurizrCli, workspace_hash, workspace_json

logger = logging.getLogger(__name__)
CACHE = Path(".py-doc") / "c4"


def _sources_of_diagrams(cli: StructurizrCli, dsl: Path, ws, fmt: str, work: Path) -> dict[str, tuple[str, str]]:
    """View key -> (language, diagram source) from the structurizr-cli export."""
    if dsl.suffix != ".dsl":
        raise ConversionError("diagrams.engine 'source' needs the .dsl file, not workspace.json")
    ext = {"plantuml": "puml", "mermaid": "mmd"}[fmt]
    made = {p.name: p for p in cli.export(dsl, fmt, work)}
    found = {}
    for view in ws.views:
        path = made.get(f"structurizr-{view.key}.{ext}")
        if path is None:
            raise ConversionError(f"structurizr-cli wrote no {fmt} for the view '{view.key}'")
        found[view.key] = (fmt, path.read_text(encoding="utf-8"))
    return found


def build_pages(
    source: Source,
    out: Path,
    runtime: Callable[[], Runtime] | None,
    settings: C4Settings,
    cache: Path,
) -> list[Path]:
    """Write the pages of a workspace (and pictures) into ``out``. Unchanged workspaces are not drawn again."""
    spec = source.structurizr
    dsl = source.file
    if not dsl.is_file():
        raise ConversionError(f"The Structurizr workspace '{dsl}' does not exist")
    image = resolve_image(settings.image, cache.parent.parent)
    key = hashlib.sha256(
        json.dumps(
            [
                workspace_hash(dsl) if dsl.suffix == ".dsl" else dsl.read_text("utf-8"),
                spec.levels,
                spec.systems,
                spec.engine,
                spec.format,
                image,
            ]
        ).encode()
    ).hexdigest()[:16]
    marker = out / ".hash"
    listed = sorted(out.glob("*.md")) if out.is_dir() else []
    if marker.is_file() and marker.read_text(encoding="utf-8") == key and listed:
        logger.info("%s is unchanged, so its pages and pictures are reused", dsl.name)
        return listed

    cli = StructurizrCli(runtime, settings.cli)
    ws = load_workspace(workspace_json(dsl, cache / "json", runtime, settings.cli))
    out.mkdir(parents=True, exist_ok=True)
    marker.unlink(missing_ok=True)
    images: dict[str, str] = {}
    sources: dict[str, tuple[str, str]] = {}
    if spec.engine == "browser":
        if runtime is None:
            raise ConversionError("Drawing the views needs the tool container, but no runtime was given")
        box = runtime()
        stack = Stack(box, dsl, image=image, port=settings.port or SERVER_PORT)
        files = render_views(ws, dsl, out / "images", box, formats=(spec.format,), stack=stack)
        images = {p.stem: f"images/{p.name}" for p in files}
    else:
        sources = _sources_of_diagrams(cli, dsl, ws, spec.format, out / "diagrams")

    for old in out.glob("*.md"):
        old.unlink()
    pages = generate(
        ws, dsl.name, levels=spec.levels or None, systems=spec.systems or None, images=images, sources=sources
    )
    written = []
    for name, text in pages.items():
        (out / name).write_text(text, encoding="utf-8")
        written.append(out / name)
    marker.write_text(key, encoding="utf-8")
    return written


def expand(
    sources: list[Source], doc_id: str, root: Path, runtime: Callable[[], Runtime] | None, settings: C4Settings
) -> list[Source]:
    """The sources with each ``structurizr:`` entry replaced by the pages generated from it."""
    expanded: list[Source] = []
    for number, source in enumerate(sources):
        if source.structurizr is None:
            expanded.append(source)
            continue
        out = root / CACHE / doc_id / f"{number:02d}_{source.file.stem}"
        pages = build_pages(source, out, runtime, settings, root / CACHE)
        for index, page in enumerate(pages):
            expanded.append(
                replace(
                    source,
                    file=page,
                    structurizr=None,
                    title=source.title if index == 0 else None,
                    page_break=source.page_break and index == 0,
                )
            )
    return expanded
