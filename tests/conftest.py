"""Shared fixtures for the py-doc2docx test suite."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from docx_helpers import outline  # noqa: E402
from pydoc2docx import DocxConverter  # noqa: E402
from py_doc.render.pptx import SlidesConverter  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"
AST_GOLDEN = GOLDEN / "ast"


@pytest.fixture(autouse=True)
def restore_py_doc_logger():
    """Undo the logging setup that CLI tests trigger by calling main() in-process.

    py-logkit replaces the handlers of the ``py_doc`` logger and turns propagation off. Without
    this, a stale handler pointing at a closed capture stream would outlive the test.
    """
    logger = logging.getLogger("py_doc")
    propagate, level = logger.propagate, logger.level
    handlers = list(logger.handlers)
    yield
    for handler in list(logger.handlers):
        if handler not in handlers and type(handler) is logging.StreamHandler:
            logger.removeHandler(handler)
            handler.close()
    logger.propagate = propagate
    logger.setLevel(level)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def convert_text(tmp_path):
    """Convert a Markdown string and return the DOCX path."""

    def _convert(markdown: str | bytes, template: Path | None = None, keep_template_body: bool = False) -> Path:
        src = tmp_path / "doc.md"
        # bytes keep CRLF intact on every Python version and let tests supply invalid UTF-8
        src.write_bytes(markdown if isinstance(markdown, bytes) else markdown.encode("utf-8"))
        converter = DocxConverter(template_path=template, keep_template_body=keep_template_body)
        return converter.convert_file(src, tmp_path / "doc.docx")

    return _convert


@pytest.fixture
def convert_fixture(tmp_path):
    """Convert a named file from tests/fixtures and return the DOCX path."""

    def _convert(name: str) -> Path:
        return DocxConverter().convert_file(FIXTURES / name, tmp_path / (Path(name).stem + ".docx"))

    return _convert


@pytest.fixture
def convert_slides(tmp_path):
    """Convert a Markdown string to a deck and return the PPTX path."""

    def _convert(markdown: str | bytes, **options) -> Path:
        src = tmp_path / "deck.md"
        src.write_bytes(markdown if isinstance(markdown, bytes) else markdown.encode("utf-8"))
        return SlidesConverter(**options).convert_file(src, tmp_path / "deck.pptx")

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


@pytest.fixture
def check_ast_golden():
    """Compare the outline of a parsed fixture with tests/golden/ast/<name>.txt.

    Set UPDATE_GOLDEN=1 to rewrite the golden files after a deliberate change, then review the diff.
    """

    def _check(name: str, outline_text: str) -> None:
        golden = AST_GOLDEN / f"{name}.txt"
        if os.environ.get("UPDATE_GOLDEN") == "1":
            AST_GOLDEN.mkdir(exist_ok=True)
            golden.write_text(outline_text, encoding="utf-8")
        assert golden.exists(), f"Missing golden file {golden}; run with UPDATE_GOLDEN=1"
        assert outline_text == golden.read_text(encoding="utf-8")

    return _check
