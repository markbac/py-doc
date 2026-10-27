"""The HTML deck: the slides of a deck's Markdown as one self-contained page, its PDF and its settings."""

from __future__ import annotations

import logging
import re
import types
from pathlib import Path

import pytest

from py_doc import deck
from py_doc.app import main
from py_doc.config import ConfigError, parse_config
from py_doc.deck import DeckError, DeckSettings, Slide, build_deck, line_count, split_slides
from py_doc.markdown import Metadata

TALK = """\
# Introduction

## Why

- one
- two

<!-- notes: Say hello -->

## Layout

:::: columns
::: column
Left side
:::
::: column
Right side
:::
::::

::: notes
Pause here
:::

::: {.pagebreak}
:::

After the break

# Design

## Parts

```cards
Sensor | On I2C
Radio | Sends
```

The energy is $E = mc^2$.
"""


def page(markdown=TALK, title="Talk", **settings):
    built, ctx, count = build_deck(
        markdown, Metadata(title=title, subtitle="A subtitle", author="A. Writer", version="2.1"), Path("."),
        DeckSettings(**settings), lambda: None,
    )  # fmt: skip
    return built, count


# --- slides -----------------------------------------------------------------------------------------


def test_slides_start_at_headings_up_to_the_split_level_and_at_page_breaks():
    slides = split_slides(TALK)
    assert [(s.kind, s.title) for s in slides] == [
        ("part", "Introduction"), ("content", "Why"), ("content", "Layout"), ("content", ""), ("part", "Design"),
        ("content", "Parts"),
    ]  # fmt: skip
    assert "After the break" in "\n".join(slides[3].body)
    level_one = split_slides(TALK, 1)
    assert [s.title for s in level_one] == ["Introduction", "", "Design"]  # the page break, then # Design


def test_notes_are_set_aside_from_the_slide():
    slides = split_slides(TALK)
    assert slides[1].notes == ["Say hello"] and "Say hello" not in "\n".join(slides[1].body)
    assert slides[2].notes == ["Pause here"]


def test_code_in_a_slide_is_not_split_or_read_as_notes():
    slides = split_slides("## A\n\n```markdown\n## Not a slide\n::: notes\n```\n")
    assert len(slides) == 1 and slides[0].notes == []


def test_the_lines_of_a_slide_are_counted_as_powerpoint_counts_them():
    assert (
        line_count(Slide("content", "T", ["- a", "", "- b", "| x | y |", "|---|---|", "| 1 | 2 |", "```c", "x", "```"]))
        == 5
    )


def test_a_diagram_on_a_slide_counts_as_one_line_however_long_its_source():
    body = ["Why it matters", "```mermaid", *["  a --> b"] * 30, "```", "```wavedrom", "{}", "```"]
    assert line_count(Slide("content", "T", body)) == 3  # the sentence and two pictures


# --- the page ---------------------------------------------------------------------------------------


def test_the_deck_has_a_title_slide_section_slides_and_its_content():
    html, count = page()
    assert count == 7  # the title slide, then the six of the Markdown
    assert html.count('class="slide title"') == 1 and html.count('class="slide part"') == 2
    assert html.count('class="slide content"') == 4
    assert "<h1>Talk</h1>" in html and "A subtitle" in html and "A. Writer" in html


def test_poster_blocks_are_html_and_maths_is_mathml():
    html, _ = page()
    assert '<div class="cards"' in html and "<math" in html


def test_columns_and_notes_are_kept():
    html, _ = page()
    assert html.count('class="columns"') == 1 and html.count('<div class="column">') == 2
    assert html.count('class="notes"') == 2 and "Pause here" in html


def test_the_page_navigates_presents_and_checks_the_fit():
    """Arrow keys, space, click and swipe; #/12; o for the overview, f full screen, p the presenter view."""
    html, _ = page()
    for key in ("'ArrowRight'", "' '", "'Home'", "'End'", "'o'", "'f'", "'p'", "'Escape'"):
        assert f"k==={key}" in html, key
    assert "touchstart" in html and "#presenter" in html and "BroadcastChannel" in html
    assert "history.replaceState(null,'','#/'+(at+1))" in html
    assert "pyDocOverflow" in html and "console.warn" in html


def test_the_footer_and_slide_numbers():
    html, _ = page(footer="{title} v{version}")
    assert '<div class="foot"><span>Talk v2.1</span><span>2</span></div>' in html


def test_the_aspect_sets_the_size_and_print_page():
    wide, _ = page()
    square, _ = page(aspect="4:3")
    assert "width:1024px;height:576px" in wide and "@page{size:1024px 576px;margin:0}" in wide
    assert "width:1024px;height:768px" in square
    with pytest.raises(DeckError, match="aspect must be 16:9 or 4:3"):
        DeckSettings.from_options({"aspect": "21:9"})


def test_a_theme_colours_the_deck():
    html, _ = page(theme="dark")
    assert "--page:#141923" in html


def test_a_slide_with_too_many_lines_is_named(caplog):
    long = "## Busy\n\n" + "\n".join(f"- item {n}" for n in range(20))
    with caplog.at_level(logging.WARNING):
        page(long)
    assert "slide 2 (Busy) has 20 lines" in caplog.text


# --- PDF ----------------------------------------------------------------------------------------------


def test_the_pdf_is_printed_by_chromium_and_names_the_slides_that_overflow(tmp_path, monkeypatch, caplog):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        output = Path(argv[3])  # deck_pdf.js <deck.html> <deck.pdf> <puppeteer.json>
        output.write_bytes(b"%PDF-1.7 deck")
        return types.SimpleNamespace(returncode=0, stdout="PYDOC-OVERFLOW [3, 5]\n", stderr="")

    runtime = types.SimpleNamespace(run=run)
    joined = types.SimpleNamespace(markdown=TALK)
    with caplog.at_level(logging.WARNING):
        deck.write_deck(
            joined, Metadata(title="Talk"), tmp_path / "talk.html", tmp_path, {"pdf": True}, lambda: runtime
        )
    assert (tmp_path / "talk.pdf").read_bytes() == b"%PDF-1.7 deck"
    assert calls[0][0] == "node" and str(calls[0][1]).endswith("deck_pdf.js")
    assert "slide(s) 3, 5 hold more than they can show" in caplog.text


# --- py-doc.yml and the command line -------------------------------------------------------------


def test_an_html_output_is_a_deck_with_deck_true(tmp_path):
    (tmp_path / "talk.md").write_text("# T\n", encoding="utf-8")
    config = parse_config(
        {"documents": {"talk": {"sources": ["talk.md"], "outputs": {
            "pptx": {"split_level": 1, "footer": "{title}"},
            "html": {"deck": True, "aspect": "4:3", "theme": "brand/theme.yml", "pdf": True},
        }}}},
        tmp_path,
    )  # fmt: skip
    from py_doc.build import _settings

    _, options = _settings(config, config.documents["talk"], "html")
    assert options["split_level"] == 1 and options["footer"] == "{title}"  # shared with the PowerPoint deck
    assert options["aspect"] == "4:3" and Path(options["theme"]) == (tmp_path / "brand" / "theme.yml").resolve()


def test_deck_options_need_deck_true(tmp_path):
    with pytest.raises(ConfigError, match=r"html\.aspect is an option of an HTML deck: add deck: true"):
        parse_config({"documents": {"t": {"sources": ["t.md"], "outputs": {"html": {"aspect": "4:3"}}}}}, tmp_path)
    with pytest.raises(ConfigError, match="aspect must be 16:9 or 4:3"):
        parse_config(
            {"documents": {"t": {"sources": ["t.md"], "outputs": {"html": {"deck": True, "aspect": "1:1"}}}}}, tmp_path
        )


def test_slides_f_html_writes_a_deck(tmp_path, monkeypatch, capsys):
    src = tmp_path / "talk.md"
    src.write_text("---\ntitle: Talk\n---\n\n## One\n\nText\n", encoding="utf-8")
    monkeypatch.setattr("py_doc.convert.connect", lambda *a, **k: None)
    assert main(["slides", str(src), "-f", "html", "--aspect", "4:3", "--footer", "{title}"]) == 0
    html = (tmp_path / "talk.html").read_text(encoding="utf-8")
    assert html.count('class="slide ') == 2 and "height:768px" in html and "<span>Talk</span>" in html


def test_deck_options_are_refused_for_powerpoint(tmp_path, capsys):
    src = tmp_path / "talk.md"
    src.write_text("## One\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="--theme is for an HTML deck: add -f html"):
        main(["slides", str(src), "--theme", "dark"])
    with pytest.raises(SystemExit, match="takes --theme, not a PowerPoint --template"):
        main(["slides", str(src), "-f", "html", "--template", "t.pptx"])


def test_the_example_deck_builds_as_an_html_deck(monkeypatch):
    """examples/py-doc.yml makes its deck an HTML deck too, from the same slides."""
    examples = Path(__file__).parent.parent / "examples"
    text = (examples / "py-doc.yml").read_text(encoding="utf-8")
    assert re.search(r"html:\n\s+deck: true", text)
