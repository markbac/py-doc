"""Regression tests for known defects, written as the behaviour we want.

Each test is marked ``xfail(strict=True)`` and names its tracking issue. When
the issue is fixed the test starts passing, strict mode turns that into a
failure, and the fix PR must remove the marker. This keeps every known defect
visible and stops fixes landing without a test.

Fixed defects move to the regular test modules (for example #6 directory
mode in test_cli.py and #49, #53 in test_converter.py).
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from docx import Document
from docx_helpers import styles, texts
from pydoc2docx import DocxConverter


def defect(issue: str):
    return pytest.mark.xfail(strict=True, reason=issue)


@defect("#9")
def test_missing_template_raises_instead_of_silently_falling_back(tmp_path):
    src = tmp_path / "a.md"
    src.write_text("# A\n", encoding="utf-8")
    converter = DocxConverter(template_path=tmp_path / "does-not-exist.docx")
    with pytest.raises(FileNotFoundError):
        converter.convert_file(src, tmp_path / "a.docx")


@defect("#10")
def test_importing_the_library_does_not_configure_logging():
    code = (
        "import logging\n"
        "before = set(logging.root.manager.loggerDict)\n"
        "import pydoc2docx\n"
        "configured = [n for n, lg in logging.root.manager.loggerDict.items()\n"
        "              if n not in before and getattr(lg, 'handlers', [])]\n"
        "raise SystemExit(1 if configured else 0)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)
    assert result.returncode == 0


class TestMarkdownSemantics:
    """Constructs the line-based converter does not understand (#8)."""

    @defect("#8")
    def test_inline_strong_and_emphasis_become_run_formatting(self, convert_text):
        out = convert_text("A **strong** and *emphasised* word.\n")
        runs = Document(str(out)).paragraphs[0].runs
        assert any(r.bold and r.text == "strong" for r in runs)
        assert any(r.italic and r.text == "emphasised" for r in runs)

    @defect("#8")
    def test_inline_code_uses_monospace_run(self, convert_text):
        out = convert_text("Run `make test` now.\n")
        runs = Document(str(out)).paragraphs[0].runs
        assert any(r.font.name == "Consolas" and r.text == "make test" for r in runs)

    @defect("#8")
    def test_links_render_as_hyperlinks_not_raw_markdown(self, convert_text):
        out = convert_text("See [the site](https://example.com).\n")
        assert "](" not in " ".join(texts(out))

    @defect("#8")
    def test_tables_become_word_tables(self, convert_text):
        out = convert_text("| A | B |\n| - | - |\n| 1 | 2 |\n")
        table = Document(str(out)).tables[0]
        assert [c.text for c in table.rows[0].cells] == ["A", "B"]
        assert [c.text for c in table.rows[1].cells] == ["1", "2"]

    @defect("#8")
    def test_block_quotes_use_a_quote_style(self, convert_text):
        out = convert_text("> Quoted words\n")
        assert styles(out) == ["Quote"]
        assert texts(out) == ["Quoted words"]

    @defect("#8")
    def test_thematic_break_is_not_rendered_as_literal_dashes(self, convert_text):
        out = convert_text("Above\n\n---\n\nBelow\n")
        assert "---" not in texts(out)

    @defect("#8")
    def test_nested_lists_use_deeper_list_styles(self, convert_text):
        out = convert_text("- Parent\n  - Child\n")
        assert styles(out) == ["List Bullet", "List Bullet 2"]

    @defect("#8")
    def test_soft_wrapped_lines_join_into_one_paragraph(self, convert_text):
        out = convert_text("Second paragraph\nwrapped over two lines.\n")
        assert texts(out) == ["Second paragraph wrapped over two lines."]
