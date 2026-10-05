"""Semantic tests for DocxConverter: they open the generated DOCX and inspect it."""

from __future__ import annotations

import pytest
from docx import Document
from docx.shared import Inches
from docx_helpers import outline, styles, texts
from py_doc import ConversionError, DocxConverter


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


    @pytest.mark.parametrize("line", ["#NoSpace", "#123", "####### seven"])
    def test_hash_without_space_or_beyond_six_levels_is_a_paragraph(self, convert_text, line):
        out = convert_text(f"{line}\n")
        assert styles(out) == ["Normal"]
        assert texts(out) == [line]

    def test_empty_heading_is_skipped(self, convert_text):
        out = convert_text("# Before\n\n##\n\nAfter\n")
        assert texts(out) == ["Before", "After"]


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

    @pytest.mark.parametrize(
        "line", ["10.5 is a number", "2.4.1 fixes the crash", "802.11 is the standard", "1.foo", "1234567890. ten digits"]
    )
    def test_digits_not_followed_by_a_space_after_the_dot_are_a_paragraph(self, convert_text, line):
        out = convert_text(f"{line}\n")
        assert styles(out) == ["Normal"]
        assert texts(out) == [line]

    def test_extra_space_after_the_marker_is_dropped(self, convert_text):
        out = convert_text("1.    Spaced\n")
        assert styles(out) == ["List Number"]
        assert texts(out) == ["Spaced"]


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

    def test_unclosed_fence_keeps_its_content_and_warns(self, convert_text, caplog):
        out = convert_text("Before\n\n```python\nprint('kept')\nmore = 1\n")
        assert texts(out) == ["Before", "print('kept')\nmore = 1"]
        assert outline(out)[1]["font"] == "Consolas"
        assert "Unclosed code fence" in caplog.text

    def test_text_around_blocks_is_kept_in_order(self, convert_text):
        out = convert_text("Before\n\n```\ncode\n```\n\nAfter\n")
        assert texts(out) == ["Before", "code", "After"]


class TestInputReading:
    def test_utf8_byte_order_mark_is_ignored(self, convert_text):
        out = convert_text(b"\xef\xbb\xbf# Heading\n\nText\n")
        assert styles(out) == ["Heading 1", "Normal"]
        assert texts(out) == ["Heading", "Text"]

    def test_invalid_utf8_raises_a_clear_error_and_writes_nothing(self, tmp_path, convert_text):
        with pytest.raises(ConversionError, match=r"doc\.md.*not valid UTF-8"):
            convert_text(b"caf\xe9\n")
        assert not (tmp_path / "doc.docx").exists()

    def test_characters_invalid_in_xml_are_removed_with_a_warning(self, convert_text, caplog):
        out = convert_text("Null\x00 byte and\x0bvertical tab\x1f\n")
        assert texts(out) == ["Null byte andvertical tab"]
        assert "Removed 3 control character(s)" in caplog.text

    def test_clean_input_does_not_warn_about_control_characters(self, convert_text, caplog):
        convert_text("# Fine\n\ttabbed\n")
        assert "control character" not in caplog.text

    @pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\u0085"])
    def test_unicode_line_separators_do_not_split_a_paragraph(self, convert_text, separator):
        out = convert_text(f"one{separator}two\n")
        assert texts(out) == [f"one{separator}two"]

    def test_lone_carriage_returns_are_line_breaks(self, convert_text):
        out = convert_text(b"# Title\r\rText\r")
        assert texts(out) == ["Title", "Text"]


class TestTemplate:
    def _make_template(self, tmp_path):
        template = tmp_path / "template.docx"
        doc = Document()
        doc.core_properties.title = "From template"
        doc.sections[0].left_margin = Inches(1.7)
        doc.sections[0].header.is_linked_to_previous = False
        doc.sections[0].header.paragraphs[0].text = "Corporate header"
        doc.styles["Heading 1"].font.name = "Georgia"
        doc.add_paragraph("Template boilerplate")
        doc.add_table(rows=1, cols=1)
        doc.save(str(template))
        return template

    def test_template_body_is_removed_by_default(self, tmp_path, convert_text):
        out = convert_text("# Body\n", template=self._make_template(tmp_path))
        assert texts(out) == ["Body"]
        assert Document(str(out)).tables == []

    def test_template_styles_page_setup_header_and_properties_are_kept(self, tmp_path, convert_text):
        out = convert_text("# Body\n", template=self._make_template(tmp_path))
        doc = Document(str(out))
        assert doc.core_properties.title == "From template"
        assert doc.sections[0].left_margin == Inches(1.7)
        assert doc.sections[0].header.paragraphs[0].text == "Corporate header"
        assert doc.styles["Heading 1"].font.name == "Georgia"

    def test_template_body_is_kept_when_requested(self, tmp_path, convert_text):
        out = convert_text("# Body\n", template=self._make_template(tmp_path), keep_template_body=True)
        assert texts(out) == ["Template boilerplate", "Body"]
        assert len(Document(str(out)).tables) == 1

    def test_missing_template_raises_by_default(self, tmp_path):
        src = tmp_path / "a.md"
        src.write_text("# A\n", encoding="utf-8")
        converter = DocxConverter(template_path=tmp_path / "does-not-exist.docx")
        with pytest.raises(FileNotFoundError, match="does-not-exist.docx"):
            converter.convert_file(src, tmp_path / "a.docx")
        assert not (tmp_path / "a.docx").exists()

    def test_template_path_that_is_a_directory_raises(self, tmp_path):
        src = tmp_path / "a.md"
        src.write_text("# A\n", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            DocxConverter(template_path=tmp_path).convert_file(src, tmp_path / "a.docx")

    def test_missing_template_can_fall_back_explicitly_with_a_warning(self, tmp_path, caplog):
        src = tmp_path / "a.md"
        src.write_text("# A\n", encoding="utf-8")
        converter = DocxConverter(template_path=tmp_path / "nope.docx", allow_missing_template=True)
        out = converter.convert_file(src, tmp_path / "a.docx")
        assert texts(out) == ["A"]
        assert "Word template not found" in caplog.text

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
