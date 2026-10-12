"""Find workspaces, and run ``structurizr-cli`` (in the tool container, or the one named by ``c4.cli``)."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from py_doc.errors import ConversionError, EnvironmentProblem, ToolFailed
from py_doc.files import DEFAULT_EXCLUDE_DIRS
from py_doc.runtime import Mount, Runtime

logger = logging.getLogger(__name__)

TESTED_VERSIONS = ("2025.11.09",)
TIMEOUT = 600
# What structurizr-cli calls its formats, and the file each one leaves behind
TEXT_FORMATS = {"plantuml": "puml", "c4plantuml": "puml", "mermaid": "mmd", "dot": "dot", "static": "html"}
CLI_FORMAT = {"c4plantuml": "plantuml/c4plantuml"}
_WORKSPACE = re.compile(r"^\s*workspace\b", re.M)
_INCLUDE = re.compile(r"^\s*!(include|docs|adrs)\s+(\"[^\"]+\"|\S+)", re.M)


def _skipped(name: str) -> bool:
    return name.startswith(".") or name in DEFAULT_EXCLUDE_DIRS


def is_workspace(path: Path) -> bool:
    """A ``.dsl`` file that starts a workspace (not one that is only included), or a ``workspace.json`` with a model."""
    try:
        if path.suffix == ".dsl":
            return bool(_WORKSPACE.search(path.read_text(encoding="utf-8", errors="replace")))
        if path.name == "workspace.json":
            return '"model"' in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return False


def find_workspaces(root: Path) -> list[Path]:
    """Workspaces below ``root``, sorted, skipping hidden and vendor folders. A folder's ``.dsl`` wins over its JSON."""
    root = Path(root)
    if root.is_file():
        return [root]
    found: list[Path] = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not _skipped(d))
        here = [Path(folder) / f for f in sorted(files)]
        dsl = [p for p in here if p.suffix == ".dsl" and is_workspace(p)]
        found += dsl or [p for p in here if p.name == "workspace.json" and is_workspace(p)]
    return found


def includes(dsl: Path, seen: set[Path] | None = None) -> list[Path]:
    """Every file the workspace reads: itself, ``!include`` d files and folders, and ``!docs`` and ``!adrs`` folders."""
    seen = set() if seen is None else seen
    path = dsl.resolve()
    if path in seen or not path.is_file():
        return []
    seen.add(path)
    found = [path]
    text = path.read_text(encoding="utf-8", errors="replace")
    for kind, raw in _INCLUDE.findall(text):
        target = raw.strip('"')
        if "://" in target:
            continue
        target_path = (path.parent / target).resolve()
        if target_path.is_dir():
            for sub in sorted(p for p in target_path.rglob("*") if p.is_file()):
                found += includes(sub, seen) if sub.suffix == ".dsl" else [sub.resolve()]
        elif kind == "include":
            found += includes(target_path, seen)
    return found


def workspace_hash(dsl: Path) -> str:
    """A hash of the workspace file and everything it includes, so unchanged workspaces are not exported again."""
    digest = hashlib.sha256()
    for path in sorted(set(includes(dsl))):
        digest.update(path.as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


class StructurizrCli:
    """``structurizr-cli`` in the tool container, or on the host when ``cli`` names it."""

    def __init__(self, runtime: Callable[[], Runtime] | None = None, cli: str | None = None) -> None:
        self._runtime = runtime
        self.cli = cli

    def _run(self, args: list, folder: Path, out: Path | None) -> tuple[str, str]:
        if self.cli:
            command = [self.cli, *[str(a) for a in args]]
            try:
                done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT, check=False)
            except FileNotFoundError as exc:
                raise EnvironmentProblem(
                    f"c4.cli '{self.cli}' was not found. It needs Java 17 or newer and structurizr-cli from "
                    "https://github.com/structurizr/cli/releases. Or remove c4.cli to use the tool container"
                ) from exc
            if done.returncode != 0:
                raise ToolFailed("structurizr-cli", done.returncode, done.stderr + done.stdout)
            return done.stdout, done.stderr
        if self._runtime is None:
            raise EnvironmentProblem("structurizr-cli needs the tool container, but none was given")
        mounts = [Mount(folder)] + ([Mount(out, writable=True)] if out else [])
        result = self._runtime().run(["structurizr-cli", *args], mounts=mounts, workdir=folder, timeout=TIMEOUT)
        return result.stdout, result.stderr

    def version(self) -> str:
        out, err = self._run(["version"], Path.cwd(), None)
        match = re.search(r"\d{4}\.\d+\.\d+", out + err)
        found = match.group(0) if match else "unknown"
        if found not in TESTED_VERSIONS:
            logger.warning("structurizr-cli %s was not tested with py-doc. Tested: %s", found, ", ".join(TESTED_VERSIONS))
        return found

    def export(self, dsl: Path, fmt: str, output: Path) -> list[Path]:
        """Write ``fmt`` (json, plantuml, c4plantuml, mermaid, dot or static) of the workspace into ``output``."""
        dsl = dsl.resolve()
        output.mkdir(parents=True, exist_ok=True)
        before = set(output.iterdir())
        self._run(
            ["export", "-workspace", dsl, "-format", CLI_FORMAT.get(fmt, fmt), "-output", output.resolve()],
            dsl.parent, output.resolve(),
        )  # fmt: skip
        made = sorted(set(output.iterdir()) - before) or sorted(output.iterdir())
        if not made:
            raise ConversionError(f"structurizr-cli wrote no {fmt} output for '{dsl}'")
        return made


def workspace_json(
    workspace: Path, cache: Path, runtime: Callable[[], Runtime] | None = None, cli: str | None = None
) -> Path:
    """The ``workspace.json`` for a workspace: the file itself, or the CLI's export, cached by the hash of the sources."""
    workspace = Path(workspace)
    if workspace.suffix == ".json":
        return workspace
    digest = workspace_hash(workspace)
    cached = cache / f"{workspace.stem}-{digest}.json"
    if cached.exists():
        logger.debug("Using the cached export of %s", workspace.name)
        return cached
    StructurizrCli(runtime, cli).version()
    with tempfile.TemporaryDirectory(prefix="py-doc-c4-") as tmp:
        (made,) = [p for p in StructurizrCli(runtime, cli).export(workspace, "json", Path(tmp)) if p.suffix == ".json"][:1] or [None]
        if made is None:
            raise ConversionError(f"structurizr-cli wrote no JSON for '{workspace}'")
        cache.mkdir(parents=True, exist_ok=True)
        for old in cache.glob(f"{workspace.stem}-*.json"):
            old.unlink()
        shutil.copyfile(made, cached)
    return cached
