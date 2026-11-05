"""[[LISTTABLE]]: tables of paragraphs, lists, merged cells and blocks, as grid tables, laid out in Word."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image

from py_doc.config import Source
from py_doc.directives import DirectiveError, check, expand
from py_doc.listtable import _wrap
from py_doc.pandoc.reference import DEFAULT_TEXT_WIDTH_CM
from py_doc.pandoc.source import join_sources
from py_doc.report import BuildReport

LUA = Path(__file__).parent.parent / "src" / "py_doc" / "pandoc" / "resources" / "listtable.lua"

SAMPLE = """Before.

[[LISTTABLE: widths=5,95]]
| 1 | [Meter installation:]{.underline}<br>The installer attends the premises.<br>Meter default settings:<br>- Mode = PAYG (prepayment)<br>- Meter balance = 15 m3 |
| 2 | Inform DNO about successful installation:<br>The installer notifies the DNO backend. |
| 3 | The message contains the following fields:<br>- Supply Meter Point (SMP)<br>- [Address details (postcode is required)]{custom-style="Highlight Yellow"} |

| Name | Value |
|---|---|
| a | 1 |
"""

needs_pandoc = pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is not installed")


def convert(text: str) -> str:
    return expand(text, Path("t.md"), tables=True)


def grid(text: str) -> list[str]:
    return [line for line in convert(text).splitlines() if line.startswith(("+", "|"))]


def cells(text: str, column: int = 2) -> list[str]:
    """The text of one column of a one-row table, line by line, without its padding on the right."""
    return [line.split("|")[column].rstrip() for line in grid(text)[1:-1]]


class TestConversion:
    def test_the_sample_is_a_grid_table_with_every_line_the_same_width(self):
        lines = grid(SAMPLE.split("\n\n| Name")[0])
        assert lines[0].startswith("+-----+---") and lines[-1] == lines[0]
        assert len({len(line) for line in lines}) == 1
        assert "[[LISTTABLE" not in convert(SAMPLE)

    def test_paragraphs_are_apart_and_bullets_together(self):
        assert cells("[[LISTTABLE]]\n| a | p<br>q<br>- x<br>- y<br>r |\n") == [
            " p",
            "",
            " q",
            "",
            " - x",
            " - y",
            "",
            " r",
        ]

    def test_widths_add_up_to_a_hundred_with_three_at_least(self):
        border = grid("[[LISTTABLE: widths=1,99]]\n| a | b |\n")[0]
        assert [len(part) for part in border.strip("+").split("+")] == [3, 97]
        assert [len(part) for part in grid("[[LISTTABLE]]\n| a | b | c |\n")[0].strip("+").split("+")] == [34, 33, 33]

    def test_a_long_bullet_wraps_inside_its_bullet_and_never_inside_an_attribute(self):
        text = '[[LISTTABLE: widths=1,1]]\n| a | - [some words that go on]{custom-style="Highlight Yellow"} and on and on and on |\n'
        lines = cells(text)
        assert len(lines) > 2
        assert lines[0].startswith(" - ") and all(c.startswith("   ") for c in lines[1:])
        assert any('{custom-style="Highlight Yellow"}' in c for c in lines)

    def test_an_escaped_pipe_is_text(self):
        assert len(grid("[[LISTTABLE]]\n| a \\| b | c |\n")[0].strip("+").split("+")) == 2

    def test_a_short_row_is_padded_and_a_long_one_cut_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            lines = grid("[[LISTTABLE: widths=1,1]]\n| a |\n| a | b | c |\n")
        assert len({len(line) for line in lines}) == 1 and "c" not in "".join(lines)
        assert "t.md:2: [[LISTTABLE]] row has 1 cell(s), not 2, so it is padded" in caplog.text
        assert "t.md:3: [[LISTTABLE]] row has 3 cell(s), not 2, so it is cut" in caplog.text

    def test_a_marker_without_rows_or_with_unknown_options_is_left_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            assert convert("[[LISTTABLE]]\n\ntext\n") == "[[LISTTABLE]]\n\ntext\n"
            assert convert("[[LISTTABLE: wide]]\n| a |\n") == "[[LISTTABLE: wide]]\n| a |\n"
        assert caplog.text.count("[[LISTTABLE]] is left as written") == 2

    def test_a_marker_in_code_is_left_alone(self):
        text = "```markdown\n[[LISTTABLE]]\n| a | b |\n```\n\n`[[LISTTABLE]]`\n"
        assert convert(text) == text

    def test_a_pipe_table_is_unchanged_and_the_count_is_logged(self, caplog):
        with caplog.at_level(logging.INFO):
            out = convert(SAMPLE)
        assert out.endswith("| Name | Value |\n|---|---|\n| a | 1 |\n")
        assert "t.md: 1 [[LISTTABLE]] table(s) converted" in caplog.text

    def test_the_same_input_gives_the_same_output(self):
        assert convert(SAMPLE) == convert(SAMPLE)

    def test_tables_work_in_included_files_and_take_variables(self, tmp_path):
        (tmp_path / "part.md").write_text("[[LISTTABLE]]\n| {{who}} | b |\n", encoding="utf-8")
        (tmp_path / "main.md").write_text("# T\n\n[[INCLUDE: part.md]]\nAfter.\n", encoding="utf-8")
        joined = join_sources([Source(tmp_path / "main.md")], {"who": "Ann"}, {}, "d")
        assert "| Ann" in joined.markdown and "+---" in joined.markdown
        assert "\n\nAfter." in joined.markdown  # not part of the table


class TestLists:
    def test_numbered_items_make_one_list(self):
        assert cells("[[LISTTABLE]]\n| a | Do:<br>1. one<br>2. two |\n") == [" Do:", "", " 1. one", " 2. two"]

    def test_two_spaces_put_an_item_inside_the_one_above(self):
        text = "[[LISTTABLE]]\n| a | - a<br>  - b<br>    - c<br>- d<br>1. e<br>  - f |\n"
        assert cells(text) == [" - a", "   - b", "     - c", " - d", "", " 1. e", "    - f"]

    def test_an_item_cannot_go_more_than_one_level_deeper(self):
        assert cells("[[LISTTABLE]]\n| a | - a<br>      - b |\n") == [" - a", "   - b"]

    def test_a_wrapped_word_that_looks_like_a_list_marker_is_escaped(self):
        assert _wrap("aaaa - b 1. c", 5) == ["aaaa", "\\- b", "1\\. c"]
        assert _wrap("+ starts", 20) == ["\\+ starts"]


class TestHeaderAndMerges:
    def test_a_header_row_is_ruled_off_with_equals_signs(self):
        lines = grid("[[LISTTABLE: header, widths=1,3]]\n| A | B |\n| a | b |\n")
        assert lines[2].startswith("+=") and lines[2].count("+") == 3 and "=" in lines[2] and "-" not in lines[2]
        assert grid("[[LISTTABLE: widths=1,3, header]]\n| A | B |\n| a | b |\n") == lines
        assert convert("[[LISTTABLE: header, header]]\n| a |\n").startswith("[[LISTTABLE: header, header]]")

    def test_a_cell_of_lt_joins_the_cell_on_its_left(self):
        lines = grid("[[LISTTABLE]]\n| a | < |\n| b | c |\n")
        assert lines[0].count("+") == 2 and lines[1].count("|") == 2  # one cell across the top
        assert lines[2].count("+") == 3

    def test_a_cell_of_caret_joins_the_cell_above(self):
        lines = grid("[[LISTTABLE]]\n| a | b |\n| ^ | c |\n")
        assert lines[2].startswith("| ") and "+-" in lines[2]  # no rule under the merged cell

    def test_impossible_merges_are_empty_cells_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            convert("[[LISTTABLE]]\n| < | ^ |\n| a | b |\n")
            convert("[[LISTTABLE]]\n| a | b |\n| ^ | < |\n")
            convert("[[LISTTABLE: header]]\n| A | B |\n| ^ | b |\n")
        assert "t.md:2: '<' in the first column has no cell on its left" in caplog.text
        assert "t.md:2: '^' cannot be merged: the first row has no cell above" in caplog.text
        assert "these merged cells are not a rectangle" in caplog.text
        assert "a body cell cannot join the header row" in caplog.text

    @needs_pandoc
    def test_pandoc_reads_the_merges_and_the_header(self):
        text = "[[LISTTABLE: header]]\n| A | B | C |\n| a | < | b |\n| ^ | ^ | c |\n"
        native = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "native"], input=convert(text), capture_output=True, text=True
        )
        assert native.stderr == ""
        assert "(RowSpan 2)\n" in native.stdout and "(ColSpan 2)" in native.stdout
        assert re.search(r"TableHead.*?Str \"A\".*?TableBody", native.stdout, re.S)


class TestBlocks:
    TEXT = "[[LISTTABLE]]\n| a | See:<br>[[BLOCK: pic]] |\n\n[[BLOCK: pic]]\n![](p.png)\n[[ENDBLOCK]]\n"

    def test_a_block_is_a_slot_in_its_cell_and_a_div_of_its_own(self):
        out = convert(self.TEXT)
        key = re.search(r'::: \{\.listtable blocks="(\w+-pic)"\}', out)[1]
        assert "§1" in out and f'::: {{.listtable-block key="{key}"}}' in out and "![](p.png)" in out

    def test_a_block_used_but_not_defined_or_defined_but_not_used_is_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            convert("[[LISTTABLE]]\n| a | [[BLOCK: gone]] |\n\n[[BLOCK: spare]]\nx\n[[ENDBLOCK]]\n")
        assert "t.md:2: [[BLOCK: gone]] is used in a table, but this file does not define it" in caplog.text
        assert "t.md:4: [[BLOCK: spare]] is defined, but no table in this file uses it" in caplog.text

    def test_an_unclosed_block_or_a_stray_end_stops_the_build(self):
        with pytest.raises(DirectiveError, match="t.md:1: \\[\\[BLOCK: a\\]\\] is never closed"):
            convert("[[BLOCK: a]]\nx\n")
        with pytest.raises(DirectiveError, match="t.md:1: \\[\\[ENDBLOCK\\]\\] has no"):
            convert("[[ENDBLOCK]]\n")

    @needs_pandoc
    def test_the_filter_moves_the_block_into_its_cell(self, tmp_path):
        html = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html", "--lua-filter", str(LUA)],
            input=convert(self.TEXT), capture_output=True, text=True, check=True,
        ).stdout  # fmt: skip
        assert re.search(r"<td><p>See:</p>\s*<p><img src=\"p.png\" /></p></td>", html)
        assert html.count("<img") == 1 and "§" not in html


def test_check_finds_the_mistakes_of_tables_and_blocks():
    problems = check("[[LISTTABLE]]\n| a | b |\n| c |\n\n[[ENDBLOCK]]\n", Path("t.md"))
    assert [(p.line, p.message.split(",")[0]) for p in problems] == [
        (3, "[[LISTTABLE]] row has 1 cell(s)"),
        (5, "[[ENDBLOCK]] has no [[BLOCK:]] before it"),
    ]


def test_the_report_counts_the_tables_of_each_source(tmp_path):
    report = BuildReport(tmp_path)
    report.sources("d", [(tmp_path / "a.md", convert(SAMPLE + "\n" + SAMPLE)), (tmp_path / "b.md", "Text.\n")])
    assert [source["rich_tables"] for source in report.document("d")["sources"]] == [2, 0]


@needs_pandoc
def test_pandoc_reads_the_grid_without_warnings(tmp_path):
    result = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "native"], input=convert(SAMPLE), capture_output=True, text=True
    )
    assert result.returncode == 0 and result.stderr == ""
    assert result.stdout.count("BulletList") == 2


@pytest.fixture
def docx(convert_text):
    out = convert_text(SAMPLE)
    with zipfile.ZipFile(out) as archive:
        body = archive.read("word/document.xml").decode("utf-8")
    return Document(str(out)), body


def test_cells_hold_paragraphs_and_real_list_items(docx):
    document, _ = docx
    rich = document.tables[0]
    paragraphs = rich.rows[0].cells[1].paragraphs
    assert len(paragraphs) == 5
    bullets = [p for p in paragraphs if p._p.find(f"{qn('w:pPr')}/{qn('w:numPr')}") is not None]
    assert [p.text for p in bullets] == ["Mode = PAYG (prepayment)", "Meter balance = 15 m3"]


def test_a_custom_style_span_is_a_run_in_that_style(docx):
    _, body = docx
    assert re.search(r'<w:rStyle w:val="HighlightYellow"\s*/>', body)


def test_a_rich_table_is_headerless_fixed_and_may_split(docx):
    document, body = docx
    rich = document.tables[0]._tbl
    assert rich.tblPr.find(qn("w:tblLook")).get(qn("w:firstRow")) == "0"
    assert rich.tblPr.find(qn("w:tblLayout")).get(qn("w:type")) == "fixed"
    assert rich.xpath(".//w:tblHeader") == [] and rich.xpath(".//w:cantSplit") == []
    assert rich.xpath(".//w:r/w:rPr/w:color[@w:val='FFFFFF']") == []
    assert rich.xpath(".//w:pPr/w:keepLines") == []


def test_a_pipe_table_keeps_its_header_and_rows_together(docx):
    document, _ = docx
    pipe = document.tables[1]._tbl
    assert pipe.tblPr.find(qn("w:tblLook")).get(qn("w:firstRow")) == "1"
    rows = pipe.findall(qn("w:tr"))
    assert rows[0].find(f"{qn('w:trPr')}/{qn('w:tblHeader')}") is not None
    assert all(row.find(f"{qn('w:trPr')}/{qn('w:cantSplit')}") is not None for row in rows)
    layout = pipe.tblPr.find(qn("w:tblLayout"))
    assert layout is None or layout.get(qn("w:type")) == "autofit"


def test_a_narrow_first_column_is_about_five_percent(docx):
    document, _ = docx
    columns = [int(c.get(qn("w:w"))) for c in document.tables[0]._tbl.tblGrid.findall(qn("w:gridCol"))]
    assert 0.04 < columns[0] / sum(columns) < 0.08


def test_lint_reads_each_cell_paragraph_as_prose_of_its_own():
    from py_doc.lint.text import segments
    from py_doc.markdown import parse

    found = [s.text.strip() for s in segments(parse("[[LISTTABLE]]\n| 1 | One.<br>- Two |\n| 2 | Three |\n"))]
    assert found == ["1", "One.", "- Two", "2", "Three"]


RICH = """# T

[[LISTTABLE: header, widths=30,70]]
| Part | Picture |
| Board | [[BLOCK: photo]] |
| ^ | Fitted on the wall:<br>1. Drill<br>2. Fix |
| Spare | < |

[[BLOCK: photo]]
![The board](big.png)
[[ENDBLOCK]]
"""


@pytest.fixture
def rich_docx(tmp_path, convert_text):
    Image.new("RGB", (2000, 800), "red").save(tmp_path / "big.png")
    return Document(str(convert_text(RICH)))


def test_a_rich_header_row_is_a_header_and_the_other_rows_may_split(rich_docx):
    table = rich_docx.tables[0]._tbl
    rows = table.findall(qn("w:tr"))
    assert table.tblPr.find(qn("w:tblLayout")).get(qn("w:type")) == "fixed"
    assert rows[0].find(f"{qn('w:trPr')}/{qn('w:tblHeader')}") is not None
    assert rows[0].find(f"{qn('w:trPr')}/{qn('w:cantSplit')}") is not None
    assert rows[0].xpath(".//w:r/w:rPr/w:color[@w:val='FFFFFF']")
    assert all(row.find(f"{qn('w:trPr')}/{qn('w:cantSplit')}") is None for row in rows[1:])
    assert not rich_docx.element.body.xpath('.//w:bookmarkStart[@w:name="_PyDocRichTable"]')


def test_merged_cells_reach_word(rich_docx):
    rows = rich_docx.tables[0]._tbl.findall(qn("w:tr"))
    assert rows[1].find(qn("w:tc")).xpath("w:tcPr/w:vMerge/@w:val") == ["restart"]
    assert rows[2].find(qn("w:tc")).xpath("w:tcPr/w:vMerge/@w:val") == ["continue"]
    assert rows[3].find(qn("w:tc")).grid_span == 2


def test_a_block_picture_is_in_its_cell_and_no_wider_than_it(rich_docx):
    text_width = Cm(DEFAULT_TEXT_WIDTH_CM)  # pandoc's reference document has no page size
    pictures = rich_docx.element.body.xpath(".//wp:inline")
    assert len(pictures) == 1
    cell = rich_docx.tables[0]._tbl.findall(qn("w:tr"))[1].findall(qn("w:tc"))[1]
    assert cell.xpath(".//wp:inline") == pictures
    assert int(pictures[0].find(qn("wp:extent")).get("cx")) <= text_width * 0.7
    assert not any("§" in p.text or "The board" in p.text for p in rich_docx.paragraphs), "no caption in a cell"
    numbered = rich_docx.tables[0]._tbl.findall(qn("w:tr"))[2].xpath(".//w:numPr")
    assert len(numbered) == 2


def test_each_list_in_a_cell_keeps_its_own_bullets_or_numbers_with_a_template(convert_text):
    template = Path(__file__).parent.parent / "examples" / "templates" / "sensor.docx"
    document = Document(str(convert_text("[[LISTTABLE]]\n| a | - x<br>- y |\n| b | 1. one<br>2. two |\n", template)))
    numbering = document.part.numbering_part.element

    def format_of(paragraph):
        (num_id,) = paragraph._p.xpath("w:pPr/w:numPr/w:numId/@w:val")
        (abstract,) = numbering.xpath(f"w:num[@w:numId='{num_id}']/w:abstractNumId/@w:val")
        return numbering.xpath(f"w:abstractNum[@w:abstractNumId='{abstract}']/w:lvl[@w:ilvl='0']/w:numFmt/@w:val")[0]

    table = document.tables[-1]  # after the template's own
    assert [format_of(p) for p in table.cell(0, 1).paragraphs] == ["bullet", "bullet"]
    assert [format_of(p) for p in table.cell(1, 1).paragraphs] == ["decimal", "decimal"]
