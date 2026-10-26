"""The shared preview cases of tests/fixtures/preview/cases.json, through the HTML twin that --watch builds.

editors/vscode/test/cases.test.js checks that the VS Code live preview picks the command each case is built with.
Here the twin shows what each case expects: callouts, page breaks, slides, speaker notes, columns and text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from py_doc.convert import DocxConverter, SlidesConverter

CASES = json.loads((Path(__file__).parent / "fixtures" / "preview" / "cases.json").read_text(encoding="utf-8"))["cases"]

pytestmark = pytest.mark.usefixtures("pandoc_runtime")


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_the_html_twin_shows_each_case(case, tmp_path):
    md = tmp_path / "case.md"
    md.write_text(case["markdown"], encoding="utf-8")
    if case["command"] == "slides":
        converter = SlidesConverter(split_level=case.get("split_level", 2))
    else:
        converter = DocxConverter()
    html = converter.convert_twin(md, tmp_path / "case.html").read_text(encoding="utf-8")
    expect = case["expect"]

    for kind in expect.get("callouts", []):
        assert f'class="admonition {kind}"' in html, kind
    assert html.count('class="pagebreak"') == expect.get("pagebreaks", 0)
    content, parts = html.count('class="slide content"'), html.count('class="slide part"')
    assert content + parts == expect.get("slides", 0)
    assert parts == expect.get("parts", 0)
    assert html.count('class="notes"') == expect.get("notes", 0)
    assert html.count('class="columns"') == expect.get("columns", 0)
    for text in expect.get("text", []):
        assert text in html, text
