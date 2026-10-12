"""Which platform py-doc runs on. Only Linux and Windows are supported by the tool runner.

Commands that need no external tool work wherever Python runs. A command that needs the tool
container calls :func:`require_supported` first, so an unsupported platform is refused before any
tool is started.
"""

from __future__ import annotations

import sys

from .errors import EnvironmentProblem

SUPPORTED = ("linux", "windows")

_NAMES = {"darwin": "macOS", "cygwin": "Cygwin", "msys": "MSYS"}


def current() -> str:
    """``linux`` or ``windows`` where supported, else the name Python reports."""
    name = sys.platform
    if name.startswith("linux"):
        return "linux"
    if name == "win32":
        return "windows"
    return name


def require_supported() -> str:
    """Return the platform name, or raise :class:`EnvironmentProblem` if the tool runner cannot run here."""
    name = current()
    if name not in SUPPORTED:
        shown = _NAMES.get(name, name)
        raise EnvironmentProblem(
            f"This command needs the tool container, which is supported on Linux and Windows only (this is {shown})"
        )
    return name
