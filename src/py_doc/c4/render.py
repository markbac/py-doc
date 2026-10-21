"""Draw the views of a workspace as PNG and SVG, and fail loudly when a view cannot be drawn.

Nothing is ever written as a stand-in for a picture that could not be made.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from py_doc.errors import ConversionError
from py_doc.runtime import Mount, Runtime

from .model import View, Workspace
from .stack import ExternalStack, Stack

logger = logging.getLogger(__name__)

SCRIPT = "/opt/node/export-diagrams.js"
TIMEOUT = 1800
FORMATS = ("png", "svg")
_FAILED = re.compile(r"Failed views:\s*(.+)")


class RenderError(ConversionError):
    """One or more views could not be drawn."""


@dataclass
class Plan:
    views: list[View]
    files: list[Path]


def plan(ws: Workspace, out_dir: Path, formats: tuple[str, ...], keys: list[str] | None = None) -> Plan:
    """The views to draw and the files that will be written. Raises for an unknown or empty view."""
    chosen = [v for v in ws.views if keys is None or v.key in keys]
    missing = sorted(set(keys or []) - {v.key for v in chosen})
    if missing:
        raise RenderError(
            f"The workspace has no view '{missing[0]}'. Views: {', '.join(v.key for v in ws.views) or 'none'}"
        )
    empty = [v.key for v in chosen if not v.element_ids and v.kind not in ("filtered", "image")]
    if empty:
        raise RenderError(f"These views are empty, so they cannot be drawn: {', '.join(empty)}")
    if not chosen:
        raise RenderError("The workspace has no views to draw")
    return Plan(chosen, [out_dir / f"{v.key}.{fmt}" for v in chosen for fmt in formats])


def render_views(
    ws: Workspace,
    workspace_file: Path,
    out_dir: Path,
    runtime: Runtime,
    *,
    formats: tuple[str, ...] = FORMATS,
    keys: list[str] | None = None,
    image: str | None = None,
    port: int | None = None,
    stack: Stack | ExternalStack | None = None,
) -> list[Path]:
    """Draw the views with Structurizr Local and headless Chromium. Raises :class:`RenderError` naming what failed."""
    bad = [f for f in formats if f not in FORMATS]
    if bad:
        raise RenderError(f"Cannot draw '{bad[0]}' pictures. Formats: {', '.join(FORMATS)}")
    planned = plan(ws, out_dir, formats, keys)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in planned.files:
        old.unlink(missing_ok=True)  # a leftover from an earlier run must not pass for a new picture
    stack = stack or Stack(
        runtime, workspace_file, **({"image": image} if image else {}), **({"port": port} if port else {})
    )
    started = stack.up()
    failures: dict[str, str] = {}
    try:
        for fmt in formats:
            argv = ["node", SCRIPT, stack.url, fmt, "--output", out_dir.resolve()]
            if keys and len(keys) == 1:
                argv += ["--view", keys[0]]
            result = runtime.run(
                argv,
                mounts=[Mount(out_dir.resolve(), writable=True)],
                network=stack.network,
                timeout=TIMEOUT,
                check=False,
            )
            output = f"{result.stdout}\n{result.stderr}"
            named = _FAILED.search(output)
            if result.returncode == 1 or (result.returncode not in (0, 2)):
                raise RenderError(
                    f"Exporting {fmt} pictures failed (exit status {result.returncode}):\n{output.strip()}"
                )
            if named:
                for key in (k.strip() for k in named.group(1).split(",")):
                    failures[f"{key}.{fmt}"] = "the browser could not draw it"
    finally:
        if started:
            stack.down()
    for path in planned.files:
        if not path.is_file() or path.stat().st_size == 0:
            failures.setdefault(path.name, "no picture was written")
    if failures:
        lines = "\n".join(f"  {name}: {why}" for name, why in sorted(failures.items()))
        raise RenderError(f"{len(failures)} picture(s) could not be made:\n{lines}")
    logger.info("Drew %d picture(s) into %s", len(planned.files), out_dir)
    return planned.files
