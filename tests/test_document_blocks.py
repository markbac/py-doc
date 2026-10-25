"""Poster blocks in documents: a native block fence drawn as a picture, in docx, pptx, pdf, HTML and sites."""

from __future__ import annotations

from pathlib import Path

import pytest

from py_doc.config import load_config
from py_doc.diagrams import DiagramError, blocks, render
from py_doc.diagrams.scan import find_blocks
from py_doc.poster_themes import load_theme

CHART = '```chart unit=" msg"\nOffice | 1440 | 610\n```\n'
CARDS = "```cards cols=2\nSensor | On I2C\nRadio | Sends, then sleeps\n```\n"


@pytest.fixture
def drawn(monkeypatch, tmp_path):
    """Stand in for the container: record what each block would draw, and give back a picture file."""
    calls = []

    def draw(runtime, renderer, text, kind, landscape, source_dir, info=None):
        calls.append({"renderer": renderer.name, "text": text, "kind": kind, "landscape": landscape})
        picture = tmp_path / f"picture{len(calls)}.{kind}"
        picture.write_bytes(b"<svg/>" if kind == "svg" else b"\x89PNG\r\n\x1a\n")
        if info is not None:
            info["cached"] = False
        return picture

    monkeypatch.setattr(render, "draw_cached", draw)
    return calls


def parts(tmp_path, text):
    return [(tmp_path / "doc.md", text)]


# --- preparing a block ---


def test_an_all_svg_block_becomes_an_svg_file():
    renderer, text = blocks.prepare(
        "chart", 'unit=" msg"', "Office | 1440", Path("."), blocks.theme_for(None, Path("."))
    )
    assert renderer is blocks.SVG_BLOCK
    assert text.startswith('<?xml version="1.0"') and 'xmlns="http://www.w3.org/2000/svg"' in text
    assert "1,440 msg" in text and '<rect width="100%" height="100%" fill="#ffffff"/>' in text


def test_an_html_block_becomes_a_page_of_the_poster_styles_at_the_text_width():
    theme = blocks.theme_for(None, Path("."))
    renderer, text = blocks.prepare("cards", "cols=2", "Sensor | On I2C", Path("."), theme)
    assert renderer is blocks.HTML_BLOCK and renderer.env == {"NODE_PATH": "/opt/node/node_modules"}
    assert '<div class="body" id="block"><div class="cards"' in text
    assert "#block{width:640px" in text and theme.css_variables() in text
    _, turned = blocks.prepare("cards", "", "A | b", Path("."), theme, landscape=True)
    assert "#block{width:960px" in turned


def test_blocks_are_drawn_in_the_print_theme_unless_another_is_named(tmp_path):
    assert blocks.theme_for(None, tmp_path).colours == load_theme("print", tmp_path).colours
    assert blocks.theme_for("dark", tmp_path).colours == load_theme("dark", tmp_path).colours


def test_a_mistake_in_a_block_is_a_block_error():
    with pytest.raises(blocks.BlockError, match="needs numbers after the label"):
        blocks.prepare("chart", "", "Office | many", Path("."), blocks.theme_for(None, Path(".")))


def test_bare_options_reach_the_block():
    _, text = blocks.prepare("timeline", "vertical", "2026 | Pilot", Path("."), blocks.theme_for(None, Path(".")))
    assert 'class="timeline vertical"' in text


# --- finding blocks ---


def test_block_fences_are_found_when_asked_for_and_keep_their_options():
    text = '```chart type=bar title="A"\nA | 1\n```\n\n```python\nprint(1)\n```\n'
    assert find_blocks(text) == []
    (found,) = find_blocks(text, blocks.names())
    assert found.fence == "chart" and found.info == 'type=bar title="A"' and found.options["title"] == "A"


def test_a_block_shown_as_an_example_inside_another_fence_is_not_drawn():
    text = "````markdown\n```cards\nA | b\n```\n````\n"
    assert find_blocks(text, blocks.names()) == []


# --- in a document ---


def test_a_document_gets_a_picture_for_each_block(tmp_path, drawn):
    text = "Before.\n\n[[CAPTION:Figure]] Messages\n" + CHART + "\n" + CARDS + "\nAfter.\n"
    rendered = render.render_parts(parts(tmp_path, text), "docx", lambda: None)
    assert [call["renderer"] for call in drawn] == ["block-svg", "block-html"]
    assert [call["kind"] for call in drawn] == ["png", "png"]  # Word gets PNG, from SVG through Inkscape
    assert len(rendered.pictures) == 2 and "```" not in rendered.markdown
    assert "![chart diagram](diagrams/picture1.png)\\ " in rendered.markdown  # captioned: not alone in its paragraph
    assert "![cards diagram](diagrams/picture2.png)" in rendered.markdown


def test_html_and_sites_keep_an_svg_block_as_svg(tmp_path, drawn):
    render.render_parts(parts(tmp_path, CHART + "\n" + CARDS), "html", lambda: None)
    assert [call["kind"] for call in drawn] == ["svg", "png"]


def test_a_deck_gets_its_block_pictures_outside_a_div(tmp_path, drawn):
    rendered = render.render_parts(parts(tmp_path, CARDS), "pptx", lambda: None)
    assert ":::" not in rendered.markdown and "![cards diagram](diagrams/" in rendered.markdown


def test_a_block_after_landscape_is_laid_out_wider(tmp_path, drawn):
    render.render_parts(parts(tmp_path, "[[LANDSCAPE]]\n\n" + CARDS), "docx", lambda: None)
    assert drawn[0]["landscape"] and "#block{width:960px" in drawn[0]["text"]


def test_a_document_block_uses_the_theme_it_is_given(tmp_path, drawn):
    dark = load_theme("dark", tmp_path)
    render.render_parts(parts(tmp_path, CARDS), "docx", lambda: None, theme=dark)
    assert dark.css_variables() in drawn[0]["text"]


def test_a_broken_block_names_its_file_and_line(tmp_path, drawn):
    with pytest.raises(DiagramError, match=r"doc\.md:3: .*needs numbers after the label"):
        render.render_parts(parts(tmp_path, "Text.\n\n```chart\nA | x\n```\n"), "docx", lambda: None)


def test_the_build_report_names_the_block(tmp_path, drawn):
    events = []
    render.render_parts(parts(tmp_path, CARDS), "docx", lambda: None, events=events)
    assert events[0]["type"] == "cards" and events[0]["status"] == "ok"


# --- the setting ---


def test_diagrams_theme_is_a_name_or_a_theme_file(tmp_path):
    (tmp_path / "py-doc.yml").write_text("diagrams:\n  theme: dark\n", encoding="utf-8")
    assert load_config(tmp_path / "py-doc.yml").blocks_theme == "dark"
    (tmp_path / "py-doc.yml").write_text("diagrams:\n  theme: brand/theme.yml\n", encoding="utf-8")
    assert load_config(tmp_path / "py-doc.yml").blocks_theme == tmp_path / "brand" / "theme.yml"
