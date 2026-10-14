"""Turn the diagram fences of a document into pictures, through the tool container and a cache."""

from __future__ import annotations

import hashlib
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

from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Mount, Runtime

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
_MAGIC = {"png": b"\x89PNG\r\n\x1a\n", "svg": b"<"}


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
        digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()[:12]


def _key(runtime: Runtime, renderer: Renderer, job: Job, text: str) -> str:
    parts = (runtime.image, _tools_revision(), renderer.name, job.kind, str(job.landscape), text)
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
        env = {}
        if renderer.needs_source_dir:
            mounts.append(Mount(source_dir))
            if renderer.environment:
                env = renderer.environment(runtime.container_path(source_dir))
        for command in renderer.commands(job):
            runtime.run(command, mounts=mounts, workdir=work, env=env, timeout=TIMEOUT)
        picture = work / f"diagram.{kind}"
        if not picture.is_file() or picture.stat().st_size == 0:
            raise DiagramError("the tool finished but produced no picture")
        if not picture.read_bytes().lstrip()[:8].startswith(_MAGIC[kind]):
            raise DiagramError(f"the tool wrote a file that is not a {kind.upper()} picture")
        if kind == "png":
            _finish_png(picture, landscape)
        return picture.read_bytes()


def draw_cached(
    runtime: Runtime, renderer: Renderer, text: str, kind: str, landscape: bool, source_dir: Path, info: dict | None = None
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


def _captioned(lines: list[str], block: Block) -> bool:
    """True when a ``[[CAPTION:]]`` line (not a table's) is the nearest text above or below the diagram."""
    before = next((line for line in reversed(lines[: block.start]) if line.strip()), "")
    after = next((line for line in lines[block.end + 1 :] if line.strip()), "")
    return bool(_CAPTION.match(before) or _CAPTION.match(after))


def _alt_text(block: Block, renderer: Renderer) -> str:
    text = block.options.get("caption") or block.options.get("title")
    if not text:
        found = _TITLE.search(block.body)
        text = found["title"] if found else f"{renderer.name} diagram"
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
) -> Rendered:
    """Replace the diagram fences of each ``(file, text)`` part by pictures, and join the parts.

    HTML gets SVG where the tool can write it, everything else PNG. A failure stops the build with the
    file and line of the diagram, or with every failure when ``keep_going`` is set.
    """
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
        for block in find_blocks(text):
            replaced += lines[cursor : block.start]
            cursor = block.end + 1
            for position, name in orientation:
                if position < offsets[block.start]:
                    landscape = name == "LANDSCAPE"
            renderer = BY_FENCE[block.fence]
            kind = "svg" if fmt == "html" and "svg" in renderer.kinds else "png"
            event: dict = {"type": renderer.name, "file": str(file), "line": block.line, "kind": kind}
            started = time.monotonic()
            try:
                picture = draw_cached(runtime(), renderer, block.body, kind, landscape, file.parent, event)
                event.update(status="ok", seconds=round(time.monotonic() - started, 3))
                if events is not None:
                    events.append(event)
            except (ToolFailed, DiagramError) as exc:
                message = f"{file}:{block.line}: {block.fence} diagram failed: {_reason(exc)}"
                event.update(status="failed", cached=False, seconds=round(time.monotonic() - started, 3), error=_reason(exc))
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
                    raise DiagramError(f"{file}:{block.line}: width=\"{width}\" is not a size such as 100%, 12cm or 4in")
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
