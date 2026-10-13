"""Shared fixtures for the py-doc2docx test suite."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from fake_engine import install  # noqa: E402
from py_doc import app  # noqa: E402
from py_doc import convert as converters  # noqa: E402
from py_doc.convert import DocxConverter, SlidesConverter  # noqa: E402
from py_doc.runtime import Runtime  # noqa: E402

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
def pandoc_runtime(tmp_path, monkeypatch):
    """Converters run pandoc for real: the fake container engine executes the tool on the host."""
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc is not installed")
    engine = install(tmp_path, monkeypatch, mode="host")
    runtime = Runtime("tools:test", docker=engine.docker, platform_name="linux")
    monkeypatch.setattr(converters, "connect", lambda *args, **kwargs: runtime)
    monkeypatch.setattr(app, "connect", lambda *args, **kwargs: runtime)
    return runtime


@pytest.fixture
def convert_text(tmp_path, pandoc_runtime):
    """Convert a Markdown string and return the DOCX path."""

    def _convert(markdown: str | bytes, template: Path | None = None) -> Path:
        src = tmp_path / "doc.md"
        # bytes keep CRLF intact on every Python version and let tests supply invalid UTF-8
        src.write_bytes(markdown if isinstance(markdown, bytes) else markdown.encode("utf-8"))
        return DocxConverter(template_path=template).convert_file(src, tmp_path / "doc.docx")

    return _convert


@pytest.fixture
def convert_fixture(tmp_path, pandoc_runtime):
    """Convert a named file from tests/fixtures and return the DOCX path."""

    def _convert(name: str) -> Path:
        return DocxConverter().convert_file(FIXTURES / name, tmp_path / (Path(name).stem + ".docx"))

    return _convert


@pytest.fixture
def convert_slides(tmp_path, pandoc_runtime):
    """Convert a Markdown string to a deck and return the PPTX path."""

    def _convert(markdown: str | bytes, **options) -> Path:
        src = tmp_path / "deck.md"
        src.write_bytes(markdown if isinstance(markdown, bytes) else markdown.encode("utf-8"))
        return SlidesConverter(**options).convert_file(src, tmp_path / "deck.pptx")

    return _convert


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


@pytest.fixture(autouse=True)
def _posix_ids(monkeypatch):
    """Windows has no os.getuid. The tests that pretend to be on Linux (a fake docker on the host) need one."""
    if not hasattr(os, "getuid"):
        monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
        monkeypatch.setattr(os, "getgid", lambda: 1000, raising=False)


def tex_packages_found(*packages: str) -> bool:
    """xelatex, and ``kpsewhich`` finds ``packages``. MiKTeX can stop to ask about installing a package, so a slow answer is no."""
    if shutil.which("xelatex") is None or shutil.which("kpsewhich") is None:
        return False
    try:
        found = subprocess.run(["kpsewhich", *packages], capture_output=True, text=True, timeout=15).stdout.split()
    except subprocess.TimeoutExpired:
        return False
    return len(found) == len(packages)
