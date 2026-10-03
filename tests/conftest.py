"""Shared fixtures for the py-doc2docx test suite."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from docx_helpers import outline  # noqa: E402
from pydoc2docx import DocxConverter  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def convert_text(tmp_path):
    """Convert a Markdown string and return the DOCX path."""

    def _convert(markdown: str, template: Path | None = None) -> Path:
        src = tmp_path / "doc.md"
        src.write_text(markdown, encoding="utf-8", newline="")
        return DocxConverter(template_path=template).convert_file(src, tmp_path / "doc.docx")

    return _convert


@pytest.fixture
def convert_fixture(tmp_path):
    """Convert a named file from tests/fixtures and return the DOCX path."""

    def _convert(name: str) -> Path:
        return DocxConverter().convert_file(FIXTURES / name, tmp_path / (Path(name).stem + ".docx"))

    return _convert


@pytest.fixture
def check_golden():
    """Compare a DOCX outline with tests/golden/<name>.json.

    Set UPDATE_GOLDEN=1 to rewrite the golden files after a deliberate change.
    """

    def _check(name: str, docx_path: Path) -> None:
        actual = outline(docx_path)
        golden = GOLDEN / f"{name}.json"
        if os.environ.get("UPDATE_GOLDEN") == "1":
            golden.write_text(json.dumps(actual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        assert golden.exists(), f"Missing golden file {golden}; run with UPDATE_GOLDEN=1"
        assert actual == json.loads(golden.read_text(encoding="utf-8"))

    return _check
