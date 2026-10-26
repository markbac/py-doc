"""Turn the diagram fences of a document into pictures, through the tool container and a cache."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Mount, Runtime
from py_doc.runtime import image as runtime_image

from .registry import BY_FENCE, TOOLS, Job, Renderer
from .scan import Block, find_blocks

logger = logging.getLogger(__name__)

TIMEOUT = 300
MAX_WIDTH_PX = {"portrait": 1200, "landscape": 1800}
DPI = 192
_ORIENTATION = re.compile(r"^\s*\[\[(LANDSCAPE|PORTRAIT)\]\]\s*$", re.MULTILINE)
_CAPTION = re.compile(r"^\s*\[\[CAPTION:(?!\s*Table\s*\]\])[^\]]+\]\]")
_WIDTH = re.compile(r"^\d+(?:\.\d+)?(?:%|cm|mm|in|px)$")
_TITLE = re.compile(r"^\s*title(?::|\s)\s*(?P<title>.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_MAGIC = {"png": b"\x89PNG\r\n\x1a\n", "svg": b"<", "pdf": b"%PDF"}
_FRONT = re.compile(r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)


class DiagramError(ConversionError):
    """One or more diagrams could not be drawn. The message names each file, line and tool message."""


def cache_dir() -> Path:
    """The folder pictures are kept in between builds: ``PY_DOC_CACHE``, else the user's cache folder."""
    override = os.environ.get("PY_DOC_CACHE")
    if override:
        return Path(override) / "diagrams"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "py-doc" / "diagrams"


def _tools_revision() -> str:
    digest = hashlib.sha256()
    for path in sorted(TOOLS.iterdir()):
        if path.is_file():  # an installed package can have a __pycache__ folder beside the scripts
            digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()[:12]


def _key(runtime: Runtime, renderer: Renderer, job: Job, text: str) -> str:
    image = runtime_image.science_ref() if renderer.image == "science" else runtime.image
    parts = (image, _tools_revision(), renderer.name, job.kind, str(job.landscape), text)
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:32]


def _finish_png(path: Path, landscape: bool) -> None:
    """Shrink a picture wider than the page can show, and tell pandoc how dense it is (else it assumes 96 dpi)."""
    from PIL import Image

    limit = MAX_WIDTH_PX["landscape" if landscape else "portrait"]
    with Image.open(path) as image:
        image.load()
        if image.width > limit:
            image = image.resize((limit, round(image.height * limit / image.width)), Image.LANCZOS)
        image.save(path, dpi=(DPI, DPI))


def _draw(runtime: Runtime, renderer: Renderer, job_text: str, kind: str, landscape: bool, source_dir: Path) -> bytes:
    """Run the tool for one diagram and return the picture. Raises ToolFailed or DiagramError."""
    with tempfile.TemporaryDirectory(prefix="py-doc-diagram-") as folder:
        work = Path(folder)
        source = work / f"diagram{renderer.suffix}"
        source.write_text(job_text, encoding="utf-8", newline="\n")
        job = Job(source, work / f"diagram.{kind}", kind, landscape, source_dir if renderer.needs_source_dir else None)
        mounts = [Mount(work, writable=True), Mount(TOOLS)]
        env = dict(renderer.env)
        if renderer.needs_source_dir:
            mounts.append(Mount(source_dir))
            if renderer.environment:
                env.update(renderer.environment(runtime.container_path(source_dir)))
        image = runtime_image.ensure_science(runtime) if renderer.image == "science" else None
        for command in renderer.commands(job):
            runtime.run(command, mounts=mounts, workdir=work, env=env, timeout=TIMEOUT, image=image)
        picture = work / f"diagram.{kind}"
        if not picture.is_file() or picture.stat().st_size == 0:
            raise DiagramError("the tool finished but produced no picture")
        if not picture.read_bytes().lstrip()[:8].startswith(_MAGIC[kind]):
            raise DiagramError(f"the tool wrote a file that is not a {kind.upper()} picture")
        if kind == "png" and renderer.finish_png:
            _finish_png(picture, landscape)
        return picture.read_bytes()


def draw_cached(
    runtime: Runtime,
    renderer: Renderer,
    text: str,
    kind: str,
    landscape: bool,
    source_dir: Path,
    info: dict | None = None,
) -> Path:
    """The picture for a diagram: from the cache when the same one was drawn before. ``info`` gets ``cached``."""
    key = _key(runtime, renderer, Job(Path(), Path(), kind, landscape), text)
    folder = cache_dir()
    cached = folder / f"{key}.{kind}"
    use_cache = renderer.cacheable(text)
    if use_cache and cached.is_file() and cached.stat().st_size:
        logger.info(f"Diagram {renderer.name} {key[:8]}: reused from the cache")
        if info is not None:
            info["cached"] = True
        return cached
    if info is not None:
        info["cached"] = False
    picture = _draw(runtime, renderer, text, kind, landscape, source_dir)
    if not use_cache:
        folder = Path(tempfile.mkdtemp(prefix="py-doc-diagram-out-"))
        cached = folder / f"{key}.{kind}"
    folder.mkdir(parents=True, exist_ok=True)
    partial = cached.with_suffix(cached.suffix + f".{os.getpid()}.part")
    partial.write_bytes(picture)
    os.replace(partial, cached)
    logger.info(f"Diagram {renderer.name} {key[:8]}: drawn")
    return cached


def with_mermaid_config(text: str, config: dict | None) -> str:
    """The Mermaid diagram ``text`` with ``config`` (``diagrams.mermaid`` of py-doc.yml) in its front matter.

    The diagram's own front matter wins, key by key, and so does an ``%%{init}%%`` line, which Mermaid reads last.
    """
    if not config:
        return text
    front = _FRONT.match(text)
    try:
        own = (yaml.safe_load(front.group(1)) if front else None) or {}
    except yaml.YAMLError:
        return text  # front matter Mermaid itself will reject, with a clearer message than ours
    if not isinstance(own, dict) or not isinstance(own.get("config") or {}, dict):
        return text
    own["config"] = _deep_merge(config, own.get("config") or {})
    return "---\n" + json.dumps(own) + "\n---\n" + (text[front.end() :] if front else text)


def _deep_merge(low: dict, high: dict) -> dict:
    out = dict(low)
    for key, value in high.items():
        out[key] = _deep_merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def translated(renderer: Renderer, body: str, where: str) -> str:
    """``body`` as its tool reads it: the written form of a specialist fence turned into its runner's input."""
    if renderer.translate is None:
        return body
    from .declarative import DeclarativeError

    try:
        return renderer.translate(body)
    except DeclarativeError as exc:
        raise DiagramError(f"{where}: {renderer.name}: {exc}") from None


def _captioned(lines: list[str], block: Block) -> bool:
    """True when a ``[[CAPTION:]]`` line (not a table's) is the nearest text above or below the diagram."""
    before = next((line for line in reversed(lines[: block.start]) if line.strip()), "")
    after = next((line for line in lines[block.end + 1 :] if line.strip()), "")
    return bool(_CAPTION.match(before) or _CAPTION.match(after))


def _alt_text(block: Block, renderer: Renderer) -> str:
    text = block.options.get("caption") or block.options.get("title")
    if not text:
        found = _TITLE.search(block.body)
        text = found["title"] if found else f"{block.fence if block.fence not in BY_FENCE else renderer.name} diagram"
    return re.sub(r"[\[\]\\]", "", text).strip()


@dataclass
class Rendered:
    markdown: str
    pictures: dict[str, Path] = field(default_factory=dict)  # name inside the document -> file in the cache


def render_parts(
    parts: Iterable[tuple[Path, str]],
    fmt: str,
    runtime: Callable[[], Runtime],
    keep_going: bool = False,
    events: list[dict] | None = None,
    mermaid: dict | None = None,
    theme=None,
) -> Rendered:
    """Replace the diagram fences of each ``(file, text)`` part by pictures, and join the parts.

    HTML gets SVG where the tool can write it, everything else PNG. A failure stops the build with the
    file and line of the diagram, or with every failure when ``keep_going`` is set. ``mermaid`` is the
    Mermaid configuration of every Mermaid diagram (``diagrams.mermaid`` of py-doc.yml). Poster blocks
    (``cards``, ``chart``...) are drawn as pictures too, in ``theme`` (``diagrams.theme``; ``print`` when None).
    """
    from . import blocks as poster_blocks

    natives = poster_blocks.names() | {"plot"}
    block_theme = None
    pictures: dict[str, Path] = {}
    failures: list[str] = []
    landscape = False
    out: list[str] = []
    for file, text in parts:
        lines = text.splitlines()
        replaced: list[str] = []
        cursor = 0
        orientation = [(m.start(), m.group(1)) for m in _ORIENTATION.finditer(text)]
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line) + 1)
        for block in find_blocks(text, natives):
            replaced += lines[cursor : block.start]
            cursor = block.end + 1
            for position, name in orientation:
                if position < offsets[block.start]:
                    landscape = name == "LANDSCAPE"
            started = time.monotonic()
            if block.fence in BY_FENCE:
                renderer = BY_FENCE[block.fence]
                body = with_mermaid_config(block.body, mermaid) if renderer.name == "mermaid" else block.body
                body = translated(renderer, body, f"{file}:{block.line}")
            elif block.fence == "plot":  # a preset, expanded into a Vega-Lite or Vega spec, in the blocks' theme
                if block_theme is None:
                    block_theme = theme if theme is not None else poster_blocks.theme_for(None, file.parent)
                try:
                    renderer, body = poster_blocks.prepare_plot(block.info, block.body, block_theme)
                except poster_blocks.BlockError as exc:
                    raise DiagramError(f"{file}:{block.line}: {exc}") from None
            else:  # a poster block, drawn here first, then made a picture in the container
                if block_theme is None:
                    block_theme = theme if theme is not None else poster_blocks.theme_for(None, file.parent)
                try:
                    renderer, body = poster_blocks.prepare(
                        block.fence, block.info, block.body, file.parent, block_theme, landscape
                    )
                except poster_blocks.BlockError as exc:
                    raise DiagramError(f"{file}:{block.line}: {exc}") from None
            kind = "svg" if fmt == "html" and "svg" in renderer.kinds else "png"
            event: dict = {"type": renderer.name, "file": str(file), "line": block.line, "kind": kind}
            if block.fence not in BY_FENCE:
                event["type"] = block.fence
            try:
                picture = draw_cached(runtime(), renderer, body, kind, landscape, file.parent, event)
                event.update(status="ok", seconds=round(time.monotonic() - started, 3))
                if events is not None:
                    events.append(event)
            except (ToolFailed, DiagramError) as exc:
                message = f"{file}:{block.line}: {block.fence} diagram failed: {_reason(exc)}"
                event.update(
                    status="failed", cached=False, seconds=round(time.monotonic() - started, 3), error=_reason(exc)
                )
                if events is not None:
                    events.append(event)
                if not keep_going:
                    raise DiagramError(message) from exc
                failures.append(message)
                replaced += lines[block.start : cursor]
                continue
            name = f"diagrams/{picture.name}"
            pictures[name] = picture
            picture_line = f"![{_alt_text(block, renderer)}]({name})"
            width = block.options.get("width")
            if width:
                if not _WIDTH.match(width):
                    raise DiagramError(f'{file}:{block.line}: width="{width}" is not a size such as 100%, 12cm or 4in')
                picture_line += f"{{width={width}}}"
            if fmt == "docx" and _captioned(lines, block):
                picture_line += "\\ "  # a no-break space: not alone in its paragraph, so pandoc adds no caption
            if fmt == "pptx":  # pandoc's PowerPoint writer drops a picture inside a div and prints its alt text instead
                replaced += ["", picture_line, ""]
            else:
                replaced += ["", '::: {style="text-align:center;"}', picture_line, ":::", ""]
        replaced += lines[cursor:]
        for position, name in orientation:
            landscape = name == "LANDSCAPE"
        out.append("\n".join(replaced) + "\n")
    if failures:
        raise DiagramError(f"{len(failures)} diagram(s) failed:\n" + "\n".join(failures))
    return Rendered("\n".join(out), pictures)


def _reason(exc: Exception) -> str:
    if isinstance(exc, ToolFailed):
        return (exc.output or str(exc)).strip()
    return str(exc)


def copy_pictures(pictures: dict[str, Path], folder: Path) -> None:
    """Put the pictures where the document refers to them, below ``folder``."""
    for name, source in pictures.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
