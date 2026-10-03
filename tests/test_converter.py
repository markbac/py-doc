"""Semantic tests for DocxConverter: they open the generated DOCX and inspect it."""

from __future__ import annotations

import pytest
from docx import Document
from docx_helpers import outline, styles, texts
from pydoc2docx import DocxConverter


class TestHeadings:
    def test_levels_one_to_four_map_to_heading_styles(self, convert_text):
        out = convert_text("# One\n\n## Two\n\n### Three\n\n#### Four\n")
        assert styles(out) == ["Heading 1", "Heading 2", "Heading 3", "Heading 4"]
        assert texts(out) == ["One", "Two", "Three", "Four"]

    def test_levels_above_four_are_clamped_to_heading_4(self, convert_text):
        out = convert_text("##### Five\n\n###### Six\n")
        assert styles(out) == ["Heading 4", "Heading 4"]

    def test_heading_text_is_stripped(self, convert_text):
        out = convert_text("##    Spaced out   \n")
        assert texts(out) == ["Spaced out"]


class TestParagraphs:
    def test_blank_lines_are_not_emitted(self, convert_text):
        out = convert_text("One.\n\n\n\nTwo.\n")
        assert texts(out) == ["One.", "Two."]
        assert styles(out) == ["Normal", "Normal"]

    def test_empty_file_produces_no_paragraphs(self, convert_text):
        assert texts(convert_text("")) == []


class TestLists:
    def test_dash_and_star_bullets_use_list_bullet(self, convert_text):
        out = convert_text("- Dash\n* Star\n")
        assert styles(out) == ["List Bullet", "List Bullet"]
        assert texts(out) == ["Dash", "Star"]

    def test_ordered_items_use_list_number_without_marker(self, convert_text):
        out = convert_text("1. First\n2. Second\n10. Tenth\n")
        assert styles(out) == ["List Number"] * 3
        assert texts(out) == ["First", "Second", "Tenth"]


class TestCodeBlocks:
    def test_code_block_is_monospaced_and_indented(self, convert_text):
        out = convert_text("```python\nprint('x')\n```\n")
        (item,) = outline(out)
        assert item["text"] == "print('x')"
        assert item["font"] == "Consolas"
        assert item["size_pt"] == 9.5
        assert item["left_indent_in"] == 0.4

    def test_multiline_content_and_blank_lines_are_preserved(self, convert_text):
        out = convert_text("```\na\n\n  b\n```\n")
        assert texts(out) == ["a\n\n  b"]

    def test_fence_info_string_is_not_rendered(self, convert_text):
        out = convert_text("```python\nx = 1\n```\n")
        assert "python" not in " ".join(texts(out))

    def test_markdown_inside_fence_is_not_interpreted(self, convert_text):
        out = convert_text("```\n# not a heading\n- not a bullet\n```\n")
        assert styles(out) == ["Normal"]
        assert texts(out) == ["# not a heading\n- not a bullet"]

    def test_text_around_blocks_is_kept_in_order(self, convert_text):
        out = convert_text("Before\n\n```\ncode\n```\n\nAfter\n")
        assert texts(out) == ["Before", "code", "After"]


class TestTemplate:
    def _make_template(self, tmp_path):
        template = tmp_path / "template.docx"
        doc = Document()
        doc.core_properties.title = "From template"
        doc.add_paragraph("Template boilerplate")
        doc.save(str(template))
        return template

    def test_template_content_and_properties_are_kept(self, tmp_path, convert_text):
        out = convert_text("# Body\n", template=self._make_template(tmp_path))
        doc = Document(str(out))
        assert doc.core_properties.title == "From template"
        assert texts(out) == ["Template boilerplate", "Body"]

    def test_without_template_document_is_empty_apart_from_content(self, convert_text):
        assert texts(convert_text("# Body\n")) == ["Body"]


class TestConverterBehaviour:
    def test_returns_resolved_output_path(self, tmp_path):
        src = tmp_path / "a.md"
        src.write_text("# A\n", encoding="utf-8")
        result = DocxConverter().convert_file(src, tmp_path / "a.docx")
        assert result == (tmp_path / "a.docx").resolve()
        assert result.exists()

    def test_creates_missing_output_directories(self, tmp_path):
        src = tmp_path / "a.md"
        src.write_text("# A\n", encoding="utf-8")
        result = DocxConverter().convert_file(src, tmp_path / "deep" / "er" / "a.docx")
        assert result.exists()

    def test_missing_source_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DocxConverter().convert_file(tmp_path / "missing.md", tmp_path / "out.docx")

    def test_converter_instance_can_be_reused_without_state_leaking(self, tmp_path):
        converter = DocxConverter()
        first, second = tmp_path / "first.md", tmp_path / "second.md"
        first.write_text("# First doc\n\n```\nunclosed-looking\n```\n", encoding="utf-8")
        second.write_text("# Second doc\n", encoding="utf-8")
        out1 = converter.convert_file(first, tmp_path / "first.docx")
        out2 = converter.convert_file(second, tmp_path / "second.docx")
        assert texts(out1) == ["First doc", "unclosed-looking"]
        assert texts(out2) == ["Second doc"]

    def test_unicode_is_preserved(self, convert_text):
        out = convert_text("# Zürich – naïve café\n\n日本語のテキスト\n")
        assert texts(out) == ["Zürich – naïve café", "日本語のテキスト"]

    def test_windows_line_endings_are_handled(self, convert_text):
        out = convert_text("# Title\r\n\r\n- One\r\n- Two\r\n")
        assert texts(out) == ["Title", "One", "Two"]
        assert styles(out) == ["Heading 1", "List Bullet", "List Bullet"]
