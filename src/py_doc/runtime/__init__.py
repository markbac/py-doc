"""Run external tools (pandoc, PlantUML, Mermaid and the rest) inside the tool container.

On Linux the container engine is Docker. On Windows it is Docker inside WSL. Nothing but Python
and the engine has to be installed on the host.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import image
from .engine import Mount, Runtime, ToolResult


@dataclass
class RuntimeSettings:
    """The ``runtime:`` section of py-doc.yml."""

    docker: str | None = None
    wsl_distro: str | None = None


def connect(settings: RuntimeSettings | None = None, *, build_image: bool = True) -> Runtime:
    """A runtime with the tool image ready. Builds the image on first use unless ``build_image`` is False."""
    settings = settings or RuntimeSettings()
    runtime = Runtime(image.image_ref(), docker=settings.docker or "docker", wsl_distro=settings.wsl_distro)
    image.ensure(runtime, allow_build=build_image)
    return runtime


__all__ = ["Mount", "Runtime", "RuntimeSettings", "ToolResult", "connect", "image"]
