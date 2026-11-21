"""Example projects the page can copy into the workspace: py-doc's own documentation, the examples, posters.

They come from the py-doc repository: from a checkout when py-doc is installed from one, or from the copy
the Docker image keeps (``PYDOC_WEB_SAMPLES``). A sample is copied, never linked, so it can be edited and
built like any other project.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SKIPPED = {"build", ".py-doc", "node_modules", "__pycache__", ".git", ".structurizr"}  # outputs and caches


@dataclass(frozen=True)
class Sample:
    name: str  # the project folder it becomes
    title: str
    description: str
    parts: tuple[tuple[str, str], ...]  # (path in the repository, path in the project); "" is the project itself


SAMPLES = (
    Sample(
        "py-doc-docs",
        "py-doc's own documentation",
        "The user guide, requirements, architecture (with C4 from Structurizr) and the gallery of every diagram "
        "and poster block, with the py-doc.yml that builds them.",
        (("py-doc.yml", "py-doc.yml"), ("docs", "docs")),
    ),
    Sample(
        "sensor-node-examples",
        "Sensor Node examples",
        "A project that uses every feature: Word and PowerPoint templates, conditions and variables, generated "
        "API references, a deck, posters and a web site.",
        (("examples", ""),),
    ),
    Sample(
        "poster-examples",
        "Poster examples",
        "Posters on their own: diagrams, scales, shapes, plots, engineering and space blocks, and a branded "
        "landscape poster. Open one and preview it as a poster.",
        (("examples/poster", ""),),
    ),
)


def source_root() -> Path | None:
    """The folder the samples are copied from, or None when py-doc was installed without them."""
    configured = os.environ.get("PYDOC_WEB_SAMPLES")
    candidates = [Path(configured)] if configured else []
    candidates.append(Path(__file__).resolve().parents[3])  # a checkout: src/py_doc/web/samples.py
    for root in candidates:
        if (root / "examples" / "py-doc.yml").is_file():
            return root
    return None


def available() -> list[Sample]:
    root = source_root()
    if root is None:
        return []
    return [s for s in SAMPLES if all((root / source).exists() for source, _ in s.parts)]


def install(sample: Sample, target: Path) -> list[str]:
    """Copy ``sample`` into the new folder ``target``. Returns what was copied, relative to it."""
    root = source_root()
    if root is None:
        raise FileNotFoundError("The example projects are not installed with this py-doc")
    target.mkdir(parents=True)
    copied: list[str] = []
    for source, destination in sample.parts:
        src = root / source
        dst = target / destination if destination else target
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(destination)
            continue
        for folder, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in SKIPPED)
            for name in sorted(files):
                path = Path(folder, name)
                if path.is_symlink():
                    continue
                relative = path.relative_to(src)
                out = dst / relative
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, out)
                copied.append((Path(destination) / relative).as_posix() if destination else relative.as_posix())
    _commit(target)
    return copied


def _commit(target: Path) -> None:
    """Make the project a Git repository with one commit, as the release notes generator reads the history.
    Without Git it is left a plain folder, and only that generator fails."""
    git = shutil.which("git")
    if git is None:
        return
    identity = ["-c", "user.name=py-doc", "-c", "user.email=py-doc@localhost", "-c", "commit.gpgsign=false"]
    try:
        for args in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-q", "-m", "Example project from py-doc"]):
            subprocess.run([git, *args], cwd=target, check=True, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        pass
