"""Pin the Structurizr Lite image by digest: ``py-doc c4 lock`` writes ``c4-images.lock``, and builds read it."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from py_doc.errors import ConversionError
from py_doc.runtime import Runtime

from .stack import LITE_IMAGE

logger = logging.getLogger(__name__)
LOCK = "c4-images.lock"
_DIGEST = re.compile(r"^[\w./-]+@sha256:[0-9a-f]{64}$")


def read_lock(root: Path) -> dict[str, str]:
    """Image name -> the reference that pins it, from ``c4-images.lock``. A malformed line is an error that names it."""
    path = root / LOCK
    if not path.is_file():
        return {}
    pinned = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or not _DIGEST.match(parts[1]):
            raise ConversionError(f"{path}:{number}: expected 'IMAGE IMAGE@sha256:DIGEST'")
        pinned[parts[0]] = parts[1]
    return pinned


def lock_lite(runtime: Runtime, root: Path, tag: str = "latest") -> str:
    """Pull ``structurizr/lite:tag``, record its digest in the lock file and return the pinned reference."""
    runtime.engine(["pull", f"{LITE_IMAGE}:{tag}"], timeout=1800)
    result = runtime.engine(["image", "inspect", "--format", "{{index .RepoDigests 0}}", f"{LITE_IMAGE}:{tag}"])
    pinned = result.stdout.strip()
    if not _DIGEST.match(pinned):
        raise ConversionError(f"Docker gave no digest for {LITE_IMAGE}:{tag} (got {pinned!r})")
    text = f"# Pinned container images for py-doc c4. Written by `py-doc c4 lock`.\n{LITE_IMAGE} {pinned}\n"
    (root / LOCK).write_text(text, encoding="utf-8")
    return pinned


def resolve_lite(configured: str | None, root: Path) -> str:
    """The Lite image to run: ``c4.lite_image``, else the locked one, else the tag, which moves, with a warning."""
    if configured:
        return configured
    locked = read_lock(root).get(LITE_IMAGE)
    if locked:
        return locked
    logger.warning("%s is not pinned, so a new release can change the pictures. Run `py-doc c4 lock`", LITE_IMAGE)
    return LITE_IMAGE
