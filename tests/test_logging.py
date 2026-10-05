"""Logging is configured by the command line, never by importing the library (#10)."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize("module", ["py_doc", "pydoc2docx"])
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


def test_cli_writes_progress_to_stderr_without_colour_codes_when_piped(tmp_path):
    src = tmp_path / "spec.md"
    src.write_text("# Spec\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "py_doc.cli", str(src)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "[INFO] Converting Markdown 'spec.md'" in result.stderr
    assert result.stdout == ""
    assert "\x1b" not in result.stderr
