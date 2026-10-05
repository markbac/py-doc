"""The old `pydoc2docx` import name and command keep working (full wrappers are tracked in #45)."""

from __future__ import annotations

import subprocess
import sys

import py_doc
import pydoc2docx
from pydoc2docx.cli import main as old_main
from pydoc2docx.converter import DocxConverter as OldConverter
from py_doc.cli import main


def test_old_import_names_are_the_same_objects():
    assert pydoc2docx.DocxConverter is py_doc.DocxConverter
    assert pydoc2docx.ConversionError is py_doc.ConversionError
    assert OldConverter is py_doc.DocxConverter
    assert old_main is main
    assert pydoc2docx.__version__ == py_doc.__version__


def test_old_module_entry_point_still_runs():
    result = subprocess.run(
        [sys.executable, "-m", "pydoc2docx.cli", "--help"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "Markdown" in result.stdout
