"""[[LISTTABLE]]: tables whose cells hold paragraphs and bullets, as grid tables, laid out in Word."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import zipfile

import pytest
from docx import Document
from docx.oxml.ns import qn

from py_doc.config import Source
from py_doc.listtable import convert
from py_doc.pandoc.source import join_sources

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


def grid(text: str) -> list[str]:
    return [line for line in convert(text, "t.md").splitlines() if line.startswith(("+", "|"))]


class TestConversion:
    def test_the_sample_is_a_grid_table_with_every_line_the_same_width(self):
        lines = grid(SAMPLE.split("\n\n| Name")[0])
        assert lines[0].startswith("+-----+---") and lines[-1] == lines[0]
        assert len({len(line) for line in lines}) == 1
        assert "[[LISTTABLE" not in convert(SAMPLE, "t.md")

    def test_paragraphs_are_apart_and_bullets_together(self):
        cells = [
            line.split("|")[2].rstrip() for line in grid("[[LISTTABLE]]\n| a | p<br>q<br>- x<br>- y<br>r |\n")[1:-1]
        ]
        assert cells == [" p", "", " q", "", " - x", " - y", "", " r"]

    def test_widths_add_up_to_a_hundred_with_three_at_least(self):
        border = grid("[[LISTTABLE: widths=1,99]]\n| a | b |\n")[0]
        assert [len(part) for part in border.strip("+").split("+")] == [3, 97]
        assert [len(part) for part in grid("[[LISTTABLE]]\n| a | b | c |\n")[0].strip("+").split("+")] == [34, 33, 33]

    def test_a_long_bullet_wraps_inside_its_bullet_and_never_inside_an_attribute(self):
        text = '[[LISTTABLE: widths=1,1]]\n| a | - [some words that go on]{custom-style="Highlight Yellow"} and on and on and on |\n'
        cells = [line.split("|")[2] for line in grid(text)[1:-1]]
        assert len(cells) > 2
        assert cells[0].startswith(" - ") and all(c.startswith("   ") for c in cells[1:])
        assert any('{custom-style="Highlight Yellow"}' in c for c in cells)

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
            assert convert("[[LISTTABLE]]\n\ntext\n", "t.md") == "[[LISTTABLE]]\n\ntext\n"
            assert convert("[[LISTTABLE: wide]]\n| a |\n", "t.md") == "[[LISTTABLE: wide]]\n| a |\n"
        assert caplog.text.count("[[LISTTABLE]] is left as written") == 2

    def test_a_marker_in_code_is_left_alone(self):
        text = "```markdown\n[[LISTTABLE]]\n| a | b |\n```\n\n`[[LISTTABLE]]`\n"
        assert convert(text, "t.md") == text

    def test_a_pipe_table_is_unchanged_and_the_count_is_logged(self, caplog):
        with caplog.at_level(logging.INFO):
            out = convert(SAMPLE, "t.md")
        assert out.endswith("| Name | Value |\n|---|---|\n| a | 1 |\n")
        assert "t.md: 1 [[LISTTABLE]] table(s) converted" in caplog.text

    def test_the_same_input_gives_the_same_output(self):
        assert convert(SAMPLE, "t.md") == convert(SAMPLE, "t.md")

    def test_tables_work_in_included_files_and_take_variables(self, tmp_path):
        (tmp_path / "part.md").write_text("[[LISTTABLE]]\n| {{who}} | b |\n", encoding="utf-8")
        (tmp_path / "main.md").write_text("# T\n\n[[INCLUDE: part.md]]\nAfter.\n", encoding="utf-8")
        joined = join_sources([Source(tmp_path / "main.md")], {"who": "Ann"}, {}, "d")
        assert "| Ann" in joined.markdown and "+---" in joined.markdown
        assert "\n\nAfter." in joined.markdown  # not part of the table


@needs_pandoc
def test_pandoc_reads_the_grid_without_warnings(tmp_path):
    result = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "native"], input=convert(SAMPLE, "t.md"), capture_output=True, text=True
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
