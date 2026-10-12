"""Logging is configured by the command line, never by importing the library (#10)."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize("module", ["py_doc", "py_doc.lint", "pydoc2docx"])
def test_importing_the_library_does_not_configure_logging(module):
    code = (
        "import logging\n"
        "before = set(logging.root.manager.loggerDict)\n"
        f"import {module}\n"
        "configured = [n for n, lg in logging.root.manager.loggerDict.items()\n"
        "              if n not in before and getattr(lg, 'handlers', [])]\n"
        "raise SystemExit(1 if configured or logging.root.handlers else 0)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)
    assert result.returncode == 0


def test_cli_writes_messages_to_stderr_without_colour_codes_when_piped(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "py_doc.cli", str(tmp_path)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "[WARNING] No Markdown files found" in result.stderr
    assert result.stdout == ""
    assert "\x1b" not in result.stderr


def _log_once(env_extra: dict[str, str]) -> str:
    code = (
        "import logging\n"
        "from py_doc._logging import configure_logging\n"
        "configure_logging()\n"
        "logging.getLogger('py_doc.t').warning('careful')\n"
    )
    import os

    env = {**os.environ, **env_extra}
    for name in ("NO_COLOR", "FORCE_COLOR"):
        if name not in env_extra:
            env.pop(name, None)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True).stderr


def test_the_compact_layout_is_coloured_when_colour_is_forced():
    text = _log_once({"FORCE_COLOR": "1"})
    assert "\x1b[33mWARNING\x1b[0m" in text and "\x1b[33mcareful\x1b[0m" in text


def test_the_compact_layout_is_plain_when_piped():
    assert _log_once({}) == "[WARNING] careful\n"
    assert _log_once({"NO_COLOR": "1"}) == "[WARNING] careful\n"
