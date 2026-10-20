"""The page script of a poster, run in Chromium: column balancing, sections that flow, and the fit to the paper.

A browser is found in this order: ``PY_DOC_CHROMIUM`` (a path), Playwright's own Chromium, then an installed
Chrome. Without one the tests are skipped, unless ``PY_DOC_BROWSER_TESTS=1`` (as in CI) makes that a failure.
"""

from __future__ import annotations

import os
import textwrap

import pytest

from py_doc.poster import build

playwright = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")

WORDS = "The node wakes, measures, sends and goes back to sleep. "


@pytest.fixture(scope="module")
def browser():
    attempts = []
    if os.environ.get("PY_DOC_CHROMIUM"):
        attempts.append({"executable_path": os.environ["PY_DOC_CHROMIUM"]})
    attempts += [{}, {"channel": "chrome"}]
    with playwright.sync_playwright() as pw:
        errors = []
        for options in attempts:
            try:
                found = pw.chromium.launch(**options)
                break
            except playwright.Error as exc:
                errors.append(str(exc).splitlines()[0])
        else:
            if os.environ.get("PY_DOC_BROWSER_TESTS") == "1":
                pytest.fail(f"no browser for the poster tests: {'; '.join(errors)}")
            pytest.skip("no Chromium or Chrome for the poster tests")
        yield found
        found.close()


def open_poster(browser, tmp_path, body, front="paper: a3\n"):
    """The poster page in a browser, after its script has fitted it. The print theme loads no web fonts."""
    source = tmp_path / "poster.md"
    source.write_text(f"---\ntheme: print\n{front}---\n{textwrap.dedent(body)}", encoding="utf-8")
    page_html, _ = build(source, lambda: object())
    (tmp_path / "poster.html").write_text(page_html, encoding="utf-8")
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.goto((tmp_path / "poster.html").as_uri())
    page.wait_for_function("() => document.querySelector('.poster').dataset.w")
    return page


def layout(page):
    """For each column: its height, and its sections as (heading, continued, blocks)."""
    return page.evaluate(
        """() => [...document.querySelectorAll('.cols>.col')].map(c => ({
            height: c.getBoundingClientRect().height,
            sections: [...c.querySelectorAll(':scope>section')].map(s => [
                s.querySelector('h2').textContent, s.classList.contains('continued'),
                [...s.querySelectorAll(':scope>.body>*')].map(b => b.textContent.replace(/\s+/g, ' ').trim().slice(0, 12))])}))"""
    )


def section(name, paragraphs, attrs=""):
    text = "\n\n".join(f"P{n}. {WORDS * 5}" for n in range(1, paragraphs + 1))
    return f"## {name}{' ' + attrs if attrs else ''}\n\n{text}\n\n"


def test_the_sections_keep_their_order_and_the_tallest_column_is_as_short_as_it_can_be(browser, tmp_path):
    page = open_poster(browser, tmp_path, section("A", 8) + section("B", 1) + section("C", 1) + section("D", 1))
    columns = layout(page)
    assert [[name for name, _, _ in col["sections"]] for col in columns] == [["A"], ["B", "C", "D"]]


def test_of_the_splits_with_the_shortest_tallest_column_the_most_even_is_taken(browser, tmp_path):
    body = section("A", 10) + "".join(section(name, 1) for name in "BCDE")
    page = open_poster(browser, tmp_path, body, "paper: a3\ncolumns: 3\n")
    assert [len(col["sections"]) for col in layout(page)] == [1, 2, 2]


def test_a_flow_section_goes_on_in_the_next_columns_with_its_blocks_in_order(browser, tmp_path):
    table = "[[CAPTION:Table]] Pins\n\n| Pin | Use |\n|---|---|\n| 1 | Power |\n\n"
    body = section("Long", 12, "{.flow}") + table + section("B", 1) + section("C", 1)
    page = open_poster(browser, tmp_path, body, "paper: a3\ncolumns: 3\n")
    columns = layout(page)
    parts = [(name, continued) for col in columns for name, continued, _ in col["sections"]]
    assert parts[0] == ("Long", False) and ("Long", True) in parts
    assert [name for name, _ in parts if name != "Long"] == ["B", "C"]
    blocks = [block for col in columns for name, _, body in col["sections"] if name == "Long" for block in body]
    assert blocks == [f"P{n}. The node"[:12] for n in range(1, 13)] + ["Table 1: Pin", "Pin Use 1 Po"]
    heights = [col["height"] for col in columns]
    assert max(heights) < 0.5 * sum(heights), "the long section is shared out"
    assert page.evaluate("() => getComputedStyle(document.querySelector('section.continued h2'), '::after').content") == '" (continued)"'


def test_a_caption_is_never_parted_from_its_table(browser, tmp_path):
    body = section("Long", 7, "{.flow}").replace("P4.", "[[CAPTION:Table]] Pins\n\n| Pin |\n|---|\n| 1 |\n\nP4.") + section("B", 1)
    page = open_poster(browser, tmp_path, body)
    for col in layout(page):
        for name, _, blocks in col["sections"]:
            if "Table 1: Pin" in blocks:
                assert blocks[blocks.index("Table 1: Pin") + 1] == "Pin 1", "the table follows its caption in one column"


def test_balancing_again_gives_the_same_layout(browser, tmp_path):
    page = open_poster(browser, tmp_path, section("Long", 12, "{.flow}") + section("B", 1), "paper: a3\ncolumns: 3\n")
    before = layout(page)
    page.evaluate("() => window.dispatchEvent(new Event('load'))")  # fits again: undoes and redoes every split
    assert layout(page) == before


def test_the_poster_fits_its_paper_and_scales_to_the_window(browser, tmp_path):
    page = open_poster(browser, tmp_path, "".join(section(name, 3) for name in "ABCDEF"))
    width, height, ratio = page.evaluate(
        "() => { const p = document.querySelector('.poster'); return [+p.dataset.w, p.scrollHeight, +p.style.height.slice(0, -2) / +p.dataset.w]; }"
    )
    assert height <= width * ratio + 1 and abs(ratio - 1.4141) < 0.001, "one A3 page, no taller"
    assert page.evaluate("() => +getComputedStyle(document.querySelector('.poster')).zoom") == pytest.approx(1400 / width, rel=0.01)
