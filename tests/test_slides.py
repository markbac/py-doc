"""Semantic tests for SlidesConverter: they open the generated PPTX and inspect it."""

from __future__ import annotations

import base64
import re
import struct
import zlib
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Inches
from py_doc import ConversionError
from py_doc.render.pptx import SlidesConverter
from pptx_helpers import (
    all_text,
    body_of,
    body_texts,
    notes_of,
    pictures_of,
    runs_of,
    slides_of,
    tables_of,
    title_of,
    titles,
)

FIXTURES = Path(__file__).parent / "fixtures"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def wide_png(width: int = 2000, height: int = 1000) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


class TestSlideSplitting:
    def test_thematic_break_separates_slides(self, convert_slides):
        out = convert_slides("# A\n\ntext a\n\n---\n\n# B\n\ntext b\n")
        assert titles(out) == ["A", "B"]

    @pytest.mark.parametrize("rule", ["---", "--- ", "----", "***", "___", "- - -", "  ---"])
    def test_every_commonmark_thematic_break_splits(self, convert_slides, rule):
        out = convert_slides(f"# A\n\n{rule}\n\n# B\n\n{rule}\n\n# C\n")
        assert titles(out) == ["A", "B", "C"]

    def test_a_rule_inside_a_code_fence_does_not_split(self, convert_slides):
        out = convert_slides("# Config\n\n```yaml\nname: a\n---\nname: b\n---\n```\n\n## Next\n\ntext\n")
        assert titles(out) == ["Config", "Next"]
        assert body_texts(slides_of(out)[0]) == ["name: a\x0b---\x0bname: b\x0b---"]

    def test_empty_chunks_do_not_make_slides_or_shift_fallback_numbers(self, convert_slides):
        out = convert_slides("# A\n\n---\n\n---\n\nplain text\n")
        assert titles(out) == ["A", "Slide 2"]

    def test_fallback_titles_count_slides_emitted(self, convert_slides):
        out = convert_slides("one\n\n---\n\ntwo\n\n---\n\nthree\n")
        assert titles(out) == ["Slide 1", "Slide 2", "Slide 3"]

    def test_headings_start_new_slides_by_default(self, convert_slides):
        out = convert_slides("# Deck\n\nintro\n\n## One\n\n- a\n\n## Two\n\n- b\n")
        assert titles(out) == ["Deck", "One", "Two"]

    def test_deeper_headings_stay_inside_their_slide(self, convert_slides):
        out = convert_slides("## One\n\n### Detail\n\ntext\n")
        assert titles(out) == ["One"]
        assert body_texts(slides_of(out)[0]) == ["Detail", "text"]

    def test_split_level_zero_uses_thematic_breaks_only(self, convert_slides):
        out = convert_slides("# A\n\n## B\n\ntext\n\n---\n\n# C\n", split_level=0)
        assert titles(out) == ["A", "C"]

    def test_split_level_one_splits_on_top_level_headings_only(self, convert_slides):
        out = convert_slides("# A\n\n## B\n\ntext\n\n# C\n", split_level=1)
        assert titles(out) == ["A", "C"]

    def test_empty_file_makes_no_slides_and_warns(self, convert_slides, caplog):
        out = convert_slides("")
        assert slides_of(out) == []
        assert "has no content" in caplog.text


class TestTitles:
    def test_hash_inside_a_code_fence_is_not_a_title(self, convert_slides):
        out = convert_slides("```bash\necho hi\n# comment\nls\n```\n")
        assert titles(out) == ["Slide 1"]
        assert body_texts(slides_of(out)[0]) == ["echo hi\x0b# comment\x0bls"]

    def test_text_before_the_heading_is_kept_as_body(self, convert_slides):
        out = convert_slides("Intro text before heading\n\n### Real Title\n\nafter\n")
        assert titles(out) == ["Real Title"]
        assert body_texts(slides_of(out)[0]) == ["Intro text before heading", "after"]

    @pytest.mark.parametrize("line", ["#NoSpace", "#123", "####### seven"])
    def test_hash_without_a_space_is_text_not_a_title(self, convert_slides, line):
        out = convert_slides(f"{line}\n")
        assert titles(out) == ["Slide 1"]
        assert line in body_texts(slides_of(out)[0])

    def test_closing_hashes_are_not_part_of_the_title(self, convert_slides):
        assert titles(convert_slides("## Title ##\n")) == ["Title"]

    def test_setext_headings_are_titles(self, convert_slides):
        assert titles(convert_slides("Setext\n======\n\ntext\n")) == ["Setext"]

    def test_formatting_in_a_title_is_dropped_but_its_text_kept(self, convert_slides):
        assert titles(convert_slides("## A **bold** `title`\n")) == ["A bold title"]


class TestTitleSlide:
    def test_first_slide_uses_the_title_slide_layout(self, convert_slides):
        out = convert_slides("# Deck\n\nA subtitle line.\n\n---\n\n# Next\n\n- a\n")
        first, second = slides_of(out)
        assert first.slide_layout.name == "Title Slide"
        assert second.slide_layout.name == "Title and Content"

    def test_first_paragraph_becomes_the_subtitle(self, convert_slides):
        out = convert_slides("# Deck\n\nOverview of the system.\n\n---\n\n# Next\n")
        subtitle = [s for s in slides_of(out)[0].placeholders if s.placeholder_format.idx == 1][0]
        assert subtitle.text_frame.text == "Overview of the system."

    def test_a_document_without_separators_keeps_everything(self, convert_slides):
        text = "# Overview\n\nl1\n\nl2\n\nl3\n\nl4\n\n## Part one\n\n- p1\n- p2\n\n## Part two\n\n```\ncode here\n```\n"
        out = convert_slides(text)
        assert titles(out) == ["Overview", "Part one", "Part two"]
        assert body_texts(slides_of(out)[0]) == ["l1", "l2", "l3", "l4"]
        words = set(re.findall(r"[A-Za-z0-9]+", all_text(out)))
        assert {"l1", "l2", "l3", "l4", "p1", "p2", "code", "here"} <= words

    def test_a_first_slide_with_lists_or_code_is_a_content_slide_that_keeps_everything(self, convert_slides):
        out = convert_slides("# Deck\n\nSubtitle\n\n- one\n- two\n\n```\ncode\n```\n")
        (slide,) = slides_of(out)
        assert slide.slide_layout.name == "Title and Content"
        assert titles(out) == ["Deck"]
        assert body_texts(slide) == ["Subtitle", "one", "two", "code"]

    def test_a_second_level_heading_with_text_is_not_turned_into_a_title_slide(self, convert_slides):
        out = convert_slides("## Topic\n\nSome text.\n")
        assert slides_of(out)[0].slide_layout.name == "Title and Content"
        assert body_texts(slides_of(out)[0]) == ["Some text."]

    def test_front_matter_feeds_the_title_slide(self, convert_slides):
        out = convert_slides("---\ntitle: Front Title\nsubtitle: Sub\nauthor: Mark\ndate: 2026-10-05\n---\n\nBody text\n")
        first = slides_of(out)[0]
        assert title_of(first) == "Front Title"
        assert body_texts(first) == ["Sub", "Mark", "2026-10-05"]
        assert titles(out) == ["Front Title", "Front Title (continued)"]
        assert body_texts(slides_of(out)[1]) == ["Body text"]

    def test_the_heading_wins_over_the_front_matter_title(self, convert_slides):
        out = convert_slides("---\ntitle: Meta\n---\n\n# Heading\n")
        assert titles(out) == ["Heading"]

    def test_front_matter_sets_the_document_properties(self, convert_slides):
        out = convert_slides("---\ntitle: Meta\nauthor: Mark\nkeywords: [a, b]\n---\n\n# Heading\n")
        properties = Presentation(str(out)).core_properties
        assert (properties.title, properties.author, properties.keywords) == ("Meta", "Mark", "a, b")

    def test_a_first_slide_without_any_title_is_a_content_slide(self, convert_slides):
        out = convert_slides("just text\n")
        (slide,) = slides_of(out)
        assert slide.slide_layout.name == "Title and Content"
        assert titles(out) == ["Slide 1"]

    def test_invalid_front_matter_is_a_conversion_error(self, tmp_path, convert_slides):
        with pytest.raises(ConversionError, match=r"Invalid front matter at line 1"):
            convert_slides("---\ntitle: [unclosed\n---\n\n# A\n")
        assert not (tmp_path / "deck.pptx").exists()


class TestCodeFences:
    def test_unclosed_fence_keeps_its_content_and_warns_with_the_file_name(self, convert_slides, caplog):
        out = convert_slides("# Deck\n\n---\n\n# Code\n\n```python\nprint(1)\nprint(2)\n")
        assert body_texts(slides_of(out)[1]) == ["print(1)\x0bprint(2)"]
        assert "Unclosed code fence at line 7 of 'deck.md'" in caplog.text

    def test_a_closed_fence_does_not_warn(self, convert_slides, caplog):
        convert_slides("# A\n\n```\nx\n```\n")
        assert "Unclosed" not in caplog.text

    def test_tilde_and_nested_fences_are_one_code_block(self, convert_slides):
        out = convert_slides("# A\n\n---\n\n## B\n\n````\n```\ninner\n```\n````\n")
        assert body_texts(slides_of(out)[1]) == ["```\x0binner\x0b```"]


class TestBodyRendering:
    def test_no_empty_leading_paragraph(self, convert_slides):
        out = convert_slides("## A\n\n- first\n- second\n")
        assert body_texts(slides_of(out)[0]) == ["first", "second"]

    def test_code_formatting_is_on_the_runs_not_the_paragraph_default(self, convert_slides):
        out = convert_slides("## A\n\n```\ncode line\n```\n")
        slide = slides_of(out)[0]
        runs = [r for r in runs_of(slide) if r.text == "code line"]
        assert runs[0].font.name == "Consolas"
        assert runs[0].font.size.pt == 11
        assert slide._element.xpath(".//a:defRPr") == []

    def test_code_keeps_blank_lines_and_indentation(self, convert_slides):
        out = convert_slides("## A\n\n```\na\n\n  b\n```\n")
        assert body_texts(slides_of(out)[0]) == ["a\x0b\x0b  b"]

    def test_nested_lists_map_to_paragraph_levels(self, convert_slides):
        out = convert_slides("## A\n\n- top\n  - mid\n    - deep\n- next\n")
        assert body_of(slides_of(out)[0]) == [(0, "top"), (1, "mid"), (2, "deep"), (0, "next")]

    def test_ordered_lists_use_automatic_numbers_without_literal_markers(self, convert_slides):
        out = convert_slides("## A\n\n1. one\n2. two\n")
        slide = slides_of(out)[0]
        assert body_texts(slide) == ["one", "two"]
        numbering = slide._element.xpath(".//a:buAutoNum")
        assert [n.get("type") for n in numbering] == ["arabicPeriod", "arabicPeriod"]
        assert all(n.get("startAt") is None for n in numbering)

    def test_ordered_list_start_number_is_kept(self, convert_slides):
        out = convert_slides("## A\n\n5. five\n6. six\n")
        assert {n.get("startAt") for n in slides_of(out)[0]._element.xpath(".//a:buAutoNum")} == {"5"}

    def test_plain_paragraphs_have_no_bullet_and_list_items_keep_theirs(self, convert_slides):
        out = convert_slides("## A\n\nplain\n\n- item\n")
        body = [s for s in slides_of(out)[0].placeholders if s.placeholder_format.idx == 1][0]
        paragraphs = [p for p in body._element.xpath(".//a:p") if p.xpath("string(.)")]
        assert len(paragraphs[0].xpath("./a:pPr/a:buNone")) == 1
        assert paragraphs[1].xpath("./a:pPr/a:buNone") == []

    def test_text_fits_the_shape_automatically(self, convert_slides):
        out = convert_slides("## A\n\ntext\n")
        assert slides_of(out)[0]._element.xpath(".//a:normAutofit")

    def test_a_slide_with_nothing_but_a_title_has_no_empty_body_box(self, convert_slides):
        out = convert_slides("## Only a title\n")
        assert [s.name for s in slides_of(out)[0].shapes] == ["Title 1"]

    def test_a_very_full_slide_is_reported(self, convert_slides, caplog):
        out = convert_slides("## Busy\n\n" + "\n".join(f"- item {i}" for i in range(20)) + "\n")
        assert len(body_texts(slides_of(out)[0])) == 20
        assert "Slide 'Busy' in 'deck.md' has about 20 lines" in caplog.text


class TestMarkdownSemantics:
    def test_inline_formatting_becomes_run_formatting(self, convert_slides):
        out = convert_slides("## A\n\nA **strong**, *soft* and `code` word.\n")
        runs = {r.text: r for r in runs_of(slides_of(out)[0])}
        assert runs["strong"].font.bold
        assert runs["soft"].font.italic
        assert runs["code"].font.name == "Consolas"
        assert not runs["A "].font.bold

    def test_links_are_hyperlinks_on_their_text(self, convert_slides):
        out = convert_slides("## A\n\nSee [the site](https://example.com) and <https://example.com/auto>.\n")
        links = {r.text: r.hyperlink.address for r in runs_of(slides_of(out)[0]) if r.hyperlink.address}
        assert links == {"the site": "https://example.com", "https://example.com/auto": "https://example.com/auto"}

    def test_block_quotes_are_italic_and_indented(self, convert_slides):
        out = convert_slides("## A\n\n> quoted words\n")
        slide = slides_of(out)[0]
        assert body_of(slide) == [(1, "quoted words")]
        assert all(r.font.italic for r in runs_of(slide) if r.text == "quoted words")

    def test_hard_and_soft_breaks(self, convert_slides):
        out = convert_slides("## A\n\nwrapped\nline  \nbreak\n")
        assert body_texts(slides_of(out)[0]) == ["wrapped line\x0bbreak"]

    def test_tables_become_table_shapes_with_a_bold_header(self, convert_slides):
        out = convert_slides("## A\n\n| Name | Type |\n| --- | :-: |\n| id | `int` |\n")
        slide = slides_of(out)[0]
        assert tables_of(slide) == [[["Name", "Type"], ["id", "int"]]]
        header, body = [[r for r in runs_of(slide) if r.text == text][0] for text in ("Name", "id")]
        assert header.font.bold and not body.font.bold

    def test_a_table_is_placed_below_the_text_without_overlapping_it(self, convert_slides):
        out = convert_slides("## A\n\nIntro line.\n\n| a | b |\n| - | - |\n| 1 | 2 |\n")
        slide = slides_of(out)[0]
        body = [s for s in slide.placeholders if s.placeholder_format.idx == 1][0]
        (table,) = [s for s in slide.shapes if s.has_table]
        assert table.top >= body.top + body.height

    def test_a_slide_with_only_a_table_has_no_empty_text_box(self, convert_slides):
        out = convert_slides("## A\n\n| a |\n| - |\n| 1 |\n")
        assert [s.name for s in slides_of(out)[0].shapes if not s.has_table] == ["Title 1"]

    def test_local_pictures_are_embedded_with_alt_text_and_fit_the_slide(self, tmp_path, convert_slides):
        (tmp_path / "wide.png").write_bytes(wide_png())
        out = convert_slides("## A\n\n![A wide chart](wide.png)\n")
        prs = Presentation(str(out))
        (picture,) = pictures_of(prs.slides[0])
        assert picture._element.nvPicPr.cNvPr.get("descr") == "A wide chart"
        assert picture.left >= 0 and picture.left + picture.width <= prs.slide_width
        assert picture.top + picture.height <= prs.slide_height
        assert abs(picture.width / picture.height - 2) < 0.01
        assert body_texts(prs.slides[0]) == []

    def test_text_next_to_a_picture_is_kept(self, tmp_path, convert_slides):
        (tmp_path / "p.png").write_bytes(PNG)
        out = convert_slides("## A\n\nBefore ![alt](p.png) after\n")
        slide = slides_of(out)[0]
        assert len(pictures_of(slide)) == 1
        assert body_texts(slide) == ["Before  after"]

    def test_missing_remote_and_unsupported_pictures_keep_their_alt_text(self, tmp_path, convert_slides, caplog):
        (tmp_path / "logo.svg").write_text("<svg/>", encoding="utf-8")
        out = convert_slides("## A\n\n![Gone](missing.png)\n\n![Badge](https://example.com/b.svg)\n\n![Logo](logo.svg)\n")
        slide = slides_of(out)[0]
        assert body_texts(slide) == ["[Image: Gone]", "[Image: Badge]", "[Image: Logo]"]
        assert pictures_of(slide) == []
        assert "not a local file" in caplog.text and "not a supported picture" in caplog.text

    def test_speaker_notes_come_from_notes_comments(self, convert_slides):
        out = convert_slides("## A\n\ntext\n\n<!-- notes: Say hello\nand smile -->\n\n## B\n\nmore\n")
        first, second = slides_of(out)
        assert notes_of(first) == "Say hello\nand smile"
        assert notes_of(second) is None
        assert "notes" not in " ".join(body_texts(first)).lower()

    def test_other_html_comments_are_ignored_and_other_html_is_shown(self, convert_slides):
        out = convert_slides("## A\n\n<!-- TODO later -->\n\n<div>raw</div>\n")
        assert body_texts(slides_of(out)[0]) == ["<div>raw</div>"]


class TestTemplate:
    @staticmethod
    def make_template(tmp_path, with_sample=True, reorder=False, keep=None):
        prs = Presentation()
        if with_sample:
            sample = prs.slides.add_slide(prs.slide_layouts[1])
            sample.shapes.title.text = "TEMPLATE SAMPLE SLIDE"
        layouts = prs.slide_master.slide_layouts
        if reorder:
            ids = layouts._sldLayoutIdLst
            first = list(ids)[0]
            ids.remove(first)
            ids.append(first)  # "Title Slide" is no longer first
        if keep is not None:
            for layout in list(layouts):
                if layout.name not in keep:
                    layouts.remove(layout)
        path = tmp_path / "template.pptx"
        prs.save(str(path))
        return path

    def convert(self, tmp_path, template, text="# Deck\n\nsub\n\n---\n\n## Next\n\n- a\n", **options):
        src = tmp_path / "deck.md"
        src.write_text(text, encoding="utf-8")
        return SlidesConverter(template_path=template, **options).convert_file(src, tmp_path / "out.pptx")

    def test_a_missing_template_raises_by_default(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="missing.pptx"):
            self.convert(tmp_path, tmp_path / "missing.pptx")
        assert not (tmp_path / "out.pptx").exists()

    def test_a_template_that_is_a_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            self.convert(tmp_path, tmp_path)

    def test_a_missing_template_can_fall_back_explicitly_with_a_warning(self, tmp_path, caplog):
        out = self.convert(tmp_path, tmp_path / "nope.pptx", allow_missing_template=True)
        assert titles(out) == ["Deck", "Next"]
        assert "PowerPoint template not found" in caplog.text

    def test_a_file_that_is_not_a_presentation_is_a_conversion_error(self, tmp_path):
        bad = tmp_path / "bad.pptx"
        bad.write_text("not a zip", encoding="utf-8")
        with pytest.raises(ConversionError, match="Cannot read PowerPoint template"):
            self.convert(tmp_path, bad)

    def test_sample_slides_in_the_template_are_removed_by_default(self, tmp_path):
        out = self.convert(tmp_path, self.make_template(tmp_path))
        assert titles(out) == ["Deck", "Next"]

    def test_template_slides_can_be_kept(self, tmp_path):
        out = self.convert(tmp_path, self.make_template(tmp_path), keep_template_slides=True)
        assert titles(out) == ["TEMPLATE SAMPLE SLIDE", "Deck", "Next"]

    def test_layouts_are_found_by_what_they_contain_not_by_position(self, tmp_path):
        out = self.convert(tmp_path, self.make_template(tmp_path, reorder=True))
        assert [s.slide_layout.name for s in slides_of(out)] == ["Title Slide", "Title and Content"]

    def test_layouts_can_be_chosen_by_name(self, tmp_path):
        out = self.convert(tmp_path, self.make_template(tmp_path), content_layout="Two Content")
        assert slides_of(out)[1].slide_layout.name == "Two Content"

    def test_an_unknown_layout_name_lists_the_layouts(self, tmp_path):
        with pytest.raises(ConversionError, match=r"no layout named 'Nope'.*'Title Slide'"):
            self.convert(tmp_path, self.make_template(tmp_path), content_layout="Nope")

    def test_a_layout_without_a_body_cannot_be_the_content_layout(self, tmp_path):
        with pytest.raises(ConversionError, match="needs a title and a body placeholder"):
            self.convert(tmp_path, self.make_template(tmp_path), content_layout="Title Slide")

    def test_a_template_without_a_content_layout_is_a_clear_error(self, tmp_path):
        template = self.make_template(tmp_path, with_sample=False, keep={"Title Slide"})
        with pytest.raises(ConversionError, match="no layout with a title and a body placeholder"):
            self.convert(tmp_path, template)

    def test_a_template_without_a_title_layout_uses_the_content_layout_with_a_warning(self, tmp_path, caplog):
        template = self.make_template(tmp_path, with_sample=False, keep={"Title and Content"})
        out = self.convert(tmp_path, template)
        assert [s.slide_layout.name for s in slides_of(out)] == ["Title and Content"] * 2
        assert body_texts(slides_of(out)[0]) == ["sub"]
        assert "no title slide layout" in caplog.text

    def test_the_template_masters_and_slide_size_are_used(self, tmp_path):
        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
        path = tmp_path / "wide.pptx"
        prs.save(str(path))
        out = self.convert(tmp_path, path)
        assert Presentation(str(out)).slide_width == Inches(13.333)


class TestConverterBehaviour:
    def test_returns_resolved_output_path_and_creates_directories(self, tmp_path):
        src = tmp_path / "a.md"
        src.write_text("# A\n", encoding="utf-8")
        result = SlidesConverter().convert_file(src, tmp_path / "deep" / "er" / "a.pptx")
        assert result == (tmp_path / "deep" / "er" / "a.pptx").resolve()
        assert result.exists()

    def test_missing_source_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SlidesConverter().convert_file(tmp_path / "missing.md", tmp_path / "out.pptx")

    def test_invalid_utf8_raises_a_clear_error_and_writes_nothing(self, tmp_path, convert_slides):
        with pytest.raises(ConversionError, match=r"deck\.md.*not valid UTF-8"):
            convert_slides(b"caf\xe9\n")
        assert not (tmp_path / "deck.pptx").exists()

    def test_control_characters_are_removed_with_a_warning(self, convert_slides, caplog):
        out = convert_slides("## A\n\nNull\x00 byte\x0b here\n")
        assert body_texts(slides_of(out)[0]) == ["Null byte here"]
        assert "Removed 2 control character(s)" in caplog.text

    def test_byte_order_mark_and_windows_line_endings(self, convert_slides):
        out = convert_slides(b"\xef\xbb\xbf# A\r\n\r\n- one\r\n- two\r\n")
        assert titles(out) == ["A"]
        assert body_texts(slides_of(out)[0]) == ["one", "two"]

    def test_a_converter_can_be_reused_without_state_leaking(self, tmp_path):
        converter = SlidesConverter()
        first, second = tmp_path / "first.md", tmp_path / "second.md"
        first.write_text("# First\n\n---\n\n## Two\n", encoding="utf-8")
        second.write_text("# Second\n", encoding="utf-8")
        assert titles(converter.convert_file(first, tmp_path / "1.pptx")) == ["First", "Two"]
        assert titles(converter.convert_file(second, tmp_path / "2.pptx")) == ["Second"]

    def test_unicode_is_preserved(self, convert_slides):
        out = convert_slides("# Zürich – naïve café\n\n日本語のテキスト\n")
        assert titles(out) == ["Zürich – naïve café"]
        assert body_texts(slides_of(out)[0]) == ["日本語のテキスト"]


FIXTURE_NAMES = sorted(p.name for p in FIXTURES.glob("*.md"))
WORD = re.compile(r"[^\W\d_]{2,}")


def _source_words(markdown: str) -> set[str]:
    """Words a deck must keep. Front matter is metadata and plain HTML comments are not content."""
    match = re.match(r"---\n.*?\n---\n", markdown, re.S)
    markdown = markdown[match.end() :] if match else markdown
    markdown = re.sub(r"<!--(?!\s*notes?:).*?-->", "", markdown, flags=re.S)
    words: set[str] = set()
    for line in markdown.splitlines():
        if line.strip().startswith(("```", "~~~")):
            continue  # the fence line and its info string are not content
        words.update(w.lower() for w in WORD.findall(line))
    return words


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_every_fixture_converts_and_keeps_every_word(name, tmp_path):
    out = SlidesConverter().convert_file(FIXTURES / name, tmp_path / "out.pptx")
    assert out.stat().st_size > 0
    source = _source_words((FIXTURES / name).read_text(encoding="utf-8"))
    kept = {w.lower() for w in WORD.findall(all_text(out))}
    assert source - kept == set()


def test_slide_notes_text_is_part_of_a_slide_not_the_body(convert_slides):
    out = convert_slides("## A\n\nbody\n\n<!-- notes: hidden words -->\n")
    slide = slides_of(out)[0]
    assert "hidden words" not in " ".join(body_texts(slide))
    assert notes_of(slide) == "hidden words"


def test_title_placeholder_shape_text_is_plain(convert_slides):
    out = convert_slides("## Plain title\n")
    assert slides_of(out)[0].shapes.title.text_frame.paragraphs[0]._p.findall(qn("a:r"))
