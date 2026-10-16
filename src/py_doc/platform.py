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


# Console input modes (Windows): Ctrl+C is a signal, input is read a line at a time, and typed keys are echoed.
_PROCESSED_INPUT, _LINE_INPUT, _ECHO_INPUT = 0x0001, 0x0002, 0x0004


def restore_console_input() -> None:
    """Put the Windows console back into line mode, with echo and Ctrl+C, before asking questions.

    A program run earlier in the same console (wsl.exe among them) can leave it raw. ``input()`` then never
    sees the end of a line, nothing typed is shown and Ctrl+C does not stop it. Elsewhere this does nothing.
    """
    if sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-10)  # standard input
    mode = ctypes.c_uint32()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return  # not a console
    wanted = mode.value | _PROCESSED_INPUT | _LINE_INPUT | _ECHO_INPUT
    if wanted != mode.value:
        kernel32.SetConsoleMode(handle, wanted)
