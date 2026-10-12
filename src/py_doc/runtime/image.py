"""The tool image: where its definition lives, how it is tagged, and how it is built.

The ``Dockerfile`` and the files it copies ship inside the package (``runtime/definition/``). The image
tag is a hash of that folder, so a new py-doc release that changes the toolchain gets a new tag and
rebuilds, and one that does not reuses the image. Nothing has to be published or stored.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..errors import ConversionError, EnvironmentProblem
from .engine import Runtime

logger = logging.getLogger(__name__)

IMAGE_NAME = "py-doc-tools"
IMAGE_DIR = Path(__file__).parent / "definition"
LOCK_FILE = IMAGE_DIR / "tools.lock"
BUILD_TIMEOUT = 3 * 3600.0
_PROXY_VARIABLES = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy")


def _definition_files() -> list[Path]:
    return sorted(p for p in IMAGE_DIR.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def content_hash() -> str:
    """A short hash of every file in the image folder: names and bytes, in a fixed order."""
    digest = hashlib.sha256()
    for path in _definition_files():
        digest.update(path.relative_to(IMAGE_DIR).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")  # the same hash after a Windows checkout
    return digest.hexdigest()[:12]


def image_ref() -> str:
    return f"{IMAGE_NAME}:{content_hash()}"


# --- tools.lock ----------------------------------------------------------------------------------


@dataclass
class LockEntry:
    name: str
    version: str
    url: str
    sha256: str

    @property
    def recorded(self) -> bool:
        return self.sha256 != "-"


def read_lock(path: Path | None = None) -> list[LockEntry]:
    path = path or LOCK_FILE
    entries = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 4:
            raise ConversionError(f"{path}:{number}: expected 'name version url sha256', got '{line}'")
        entries.append(LockEntry(*parts))
    return entries


def write_lock(entries: list[LockEntry], path: Path | None = None) -> None:
    path = path or LOCK_FILE
    header = [line for line in path.read_text(encoding="utf-8").splitlines() if line.lstrip().startswith("#")]
    rows = [f"{e.name} {e.version} {e.url} {e.sha256}" for e in entries]
    path.write_text("\n".join([*header, *rows]) + "\n", encoding="utf-8")


def unlocked(path: Path | None = None) -> list[str]:
    return [e.name for e in read_lock(path) if not e.recorded]


def lock(path: Path | None = None, *, opener=urllib.request.urlopen) -> list[str]:
    """Download each tool that has no recorded checksum and record it. Returns the names recorded.

    A checksum that is already recorded is never changed: the download is checked against it, and a
    difference is an error, because it means the file behind the url is no longer the one reviewed.
    """
    path = path or LOCK_FILE
    entries = read_lock(path)
    recorded = []
    for entry in entries:
        digest = hashlib.sha256()
        with opener(entry.url, timeout=120) as response:  # noqa: S310 - the urls are in tools.lock
            for block in iter(lambda: response.read(1 << 20), b""):
                digest.update(block)
        found = digest.hexdigest()
        if entry.recorded and entry.sha256 != found:
            raise ConversionError(
                f"{entry.name} {entry.version}: the file at {entry.url} has checksum {found}, "
                f"but tools.lock records {entry.sha256}. Check the change before updating the lock"
            )
        if not entry.recorded:
            entry.sha256 = found
            recorded.append(entry.name)
    write_lock(entries, path)
    return recorded


# --- building ------------------------------------------------------------------------------------


def exists(runtime: Runtime) -> bool:
    return runtime.engine(["image", "inspect", runtime.image], check=False).returncode == 0


def build(runtime: Runtime, *, ca_file: Path | None = None, no_cache: bool = False) -> None:
    """Build the image from the packaged definition. Slow the first time, cached after."""
    missing = unlocked()
    if missing:
        raise EnvironmentProblem(
            f"tools.lock has no checksum for {', '.join(missing)}. Run `py-doc tools lock` to record them"
        )
    with tempfile.TemporaryDirectory(prefix="py-doc-image-") as folder:
        context = Path(folder) / "context"
        shutil.copytree(IMAGE_DIR, context, ignore=shutil.ignore_patterns("__pycache__"))
        for path in context.rglob("*"):  # a Windows checkout may have CRLF, which breaks shell scripts in the image
            if path.is_file():
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        if ca_file is not None:
            if not ca_file.is_file():
                raise EnvironmentProblem(f"Certificate file not found: {ca_file}")
            shutil.copy2(ca_file, context / "extra-ca" / "extra-ca.crt")
        where = runtime.container_path(context)
        args = ["build", "--tag", runtime.image, "--file", f"{where}/Dockerfile"]
        for name in _PROXY_VARIABLES:
            if os.environ.get(name):
                args += ["--build-arg", f"{name}={os.environ[name]}"]
        if no_cache:
            args.append("--no-cache")
        logger.info("Building %s. The first build downloads several GB and can take 10 to 30 minutes", runtime.image)
        runtime.engine([*args, where], timeout=BUILD_TIMEOUT, stream=True)
    logger.info("Built %s", runtime.image)


def ensure(runtime: Runtime, *, allow_build: bool = True) -> None:
    """Make sure the image exists, building it when allowed. Otherwise say what to run."""
    if exists(runtime):
        return
    if not allow_build:
        raise EnvironmentProblem(f"The tool image '{runtime.image}' is not built here. Run `py-doc tools build`")
    logger.info("The tool image %s is not built here yet, so it is being built now", runtime.image)
    build(runtime)


def tags(runtime: Runtime) -> list[str]:
    result = runtime.engine(["image", "ls", "--format", "{{.Repository}}:{{.Tag}}", IMAGE_NAME])
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip().startswith(IMAGE_NAME + ":")})


def prune(runtime: Runtime) -> list[str]:
    """Remove every py-doc tool image except the current one. Returns what was removed."""
    old = [tag for tag in tags(runtime) if tag != runtime.image]
    for tag in old:
        runtime.engine(["image", "rm", tag])
    return old


def save(runtime: Runtime, target: Path) -> None:
    """Write the image to a file, for machines that cannot build it."""
    runtime.engine(["save", "--output", runtime.container_path(target), runtime.image], timeout=1800)


def load(runtime: Runtime, source: Path) -> None:
    if not source.is_file():
        raise EnvironmentProblem(f"Image file not found: {source}")
    runtime.engine(["load", "--input", runtime.container_path(source)], timeout=1800)
