"""Run external tools (pandoc, PlantUML, Mermaid and the rest) inside the tool container.

On Linux the container engine is Docker. On Windows it is Docker inside WSL. Nothing but Python
and the engine has to be installed on the host.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine import Mount, Runtime, ToolResult


@dataclass
class RuntimeSettings:
    """The ``runtime:`` section of py-doc.yml."""

    docker: str | None = None
    wsl_distro: str | None = None


__all__ = ["Mount", "Runtime", "RuntimeSettings", "ToolResult"]
