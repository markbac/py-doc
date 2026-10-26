"""``py-doc diagram``: one diagram or poster block as an image file, or every one of a Markdown file."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from py_doc import diagram_cli
from py_doc.app import main
from py_doc.diagram_cli import DiagramCliError, kind_of, padded
from py_doc.diagrams import render


@pytest.fixture
def drawn(monkeypatch, tmp_path):
    """Stand in for the container: an SVG source is its own picture, anything else a small PNG."""
    calls = []

    def draw(runtime, renderer, text, kind, landscape, source_dir, info=None):
        calls.append({"renderer": renderer.name, "kind": kind, "text": text})
        picture = tmp_path / "cache" / f"picture{len(calls)}.{kind}"
        picture.parent.mkdir(exist_ok=True)
        if kind == "svg":
            picture.write_text(
                text if text.lstrip().startswith(("<?xml", "<svg")) else '<svg viewBox="0 0 10 10"/>', encoding="utf-8"
            )
        elif kind == "pdf":
            picture.write_bytes(b"%PDF-1.7 fake")
        else:
            Image.new("RGB", (40, 20), "white").save(picture, "PNG")
        return picture

    monkeypatch.setattr(render, "draw_cached", draw)
    monkeypatch.setattr(diagram_cli, "connect", lambda settings: object())
    monkeypatch.chdir(tmp_path)
    return calls


def test_the_type_comes_from_the_extension_or_is_given():
    assert kind_of(Path("a.mmd"), None) == "mermaid" and kind_of(Path("a.vl.json"), None) == "vega-lite"
    assert kind_of(Path("a.txt"), "gauge") == "gauge" and kind_of(Path("a.txt"), "plot") == "plot"
    with pytest.raises(DiagramCliError, match="give it with --type"):
        kind_of(Path("a.txt"), None)
    with pytest.raises(DiagramCliError, match="not a type py-doc draws"):
        kind_of(Path("a.txt"), "sketch")


def test_a_diagram_file_is_drawn_by_its_tool(drawn, tmp_path, capsys):
    (tmp_path / "flow.mmd").write_text("flowchart LR\n  A --> B", encoding="utf-8")
    assert main(["diagram", "flow.mmd", "-o", "flow.png"]) == 0
    assert drawn[0]["renderer"] == "mermaid" and drawn[0]["kind"] == "png"
    assert (tmp_path / "flow.png").read_bytes().startswith(b"\x89PNG") and "wrote flow.png" in capsys.readouterr().out


def test_an_svg_block_is_a_valid_svg_file_with_padding_and_no_background(drawn, tmp_path):
    (tmp_path / "gauge.txt").write_text("0 | 50 | green\n50 | 100 | red", encoding="utf-8")
    args = ["diagram", "gauge.txt", "--type", "gauge", "--options", "value=40 min=0 max=100", "-o", "g.svg"]
    assert main([*args, "--padding", "10", "--background", "transparent"]) == 0
    svg = (tmp_path / "g.svg").read_text(encoding="utf-8")
    root = ET.fromstring(svg.split("\n", 1)[1])
    assert root.get("viewBox").startswith("-10 -10 ") and '<rect width="100%"' not in svg
    assert drawn == []  # py-doc draws an SVG block itself: no container


def test_an_html_block_is_png_only(drawn, tmp_path, capsys):
    (tmp_path / "cards.txt").write_text("A | b", encoding="utf-8")
    assert main(["diagram", "cards.txt", "--type", "cards", "-o", "cards.svg"]) == 1
    assert "drawn as PNG only" in capsys.readouterr().err
    assert main(["diagram", "cards.txt", "--type", "cards", "-o", "cards.png"]) == 0
    assert drawn[0]["renderer"] == "block-html"


def test_a_plot_is_expanded_in_the_theme_given(drawn, tmp_path):
    (tmp_path / "r.txt").write_text("A | 3\nB | 1", encoding="utf-8")
    assert (
        main(["diagram", "r.txt", "--type", "plot", "--options", "type=pareto", "-o", "r.svg", "--theme", "dark"]) == 0
    )
    spec = json.loads(drawn[0]["text"])
    assert drawn[0]["renderer"] == "vega-lite" and spec["config"]["background"] == "#ffffff"


def test_every_diagram_and_block_of_a_markdown_file_is_written(drawn, tmp_path):
    (tmp_path / "poster.md").write_text(
        '# P\n\n```chart title="Messages a day"\nA | 1\n```\n\n```cards\nA | b\n```\n\n```ditaa\n+--+\n```\n',
        encoding="utf-8",
    )
    assert main(["diagram", "poster.md", "-o", "images"]) == 0
    names = sorted(p.name for p in (tmp_path / "images").iterdir())
    assert names == ["poster-01-messages-a-day.svg", "poster-02-cards.png", "poster-03-ditaa.png"]


def test_a_markdown_file_with_nothing_to_draw_is_an_error(drawn, tmp_path, capsys):
    (tmp_path / "doc.md").write_text("# Only text\n", encoding="utf-8")
    assert main(["diagram", "doc.md"]) == 1 and "no diagram or block" in capsys.readouterr().err


def test_list_and_help_type(capsys):
    assert main(["diagram", "--list"]) == 0
    out = capsys.readouterr().out
    assert "mermaid" in out and "threshold" in out and "pareto" in out
    assert main(["image", "--help-type", "gauge"]) == 0  # image is the same command
    assert "```gauge value=" in capsys.readouterr().out
    assert main(["diagram", "--help-type", "sketch"]) == 1


def test_padding_grows_the_view_box_and_size():
    out = padded('<svg width="100" height="50" viewBox="0 0 100 50"><g/></svg>', 5)
    assert 'viewBox="-5 -5 110 60"' in out and 'width="110"' in out and 'height="60"' in out
    assert padded("<svg><g/></svg>", 5) == "<svg><g/></svg>"


# --- formats, density and the card frame (phase 2) ----------------------------------------------------


def test_an_svg_picture_is_printed_to_pdf_by_chromium(drawn, tmp_path):
    """Chromium draws what Inkscape cannot, such as the HTML labels of Mermaid, and keeps them vector."""
    (tmp_path / "flow.mmd").write_text("flowchart LR\n  A --> B", encoding="utf-8")
    assert main(["diagram", "flow.mmd", "-o", "flow.pdf"]) == 0
    assert [c["renderer"] for c in drawn] == ["mermaid", "browser-pdf-1"]
    assert drawn[0]["kind"] == "svg" and '<div id="block"><svg' in drawn[1]["text"]
    assert (tmp_path / "flow.pdf").read_bytes().startswith(b"%PDF")


def test_dpi_sets_the_scale_chromium_draws_at(drawn, tmp_path):
    (tmp_path / "flow.mmd").write_text("flowchart LR\n  A --> B", encoding="utf-8")
    assert main(["diagram", "flow.mmd", "-o", "flow.png", "--dpi", "288"]) == 0
    assert [c["renderer"] for c in drawn] == ["mermaid", "browser-png-3"]
    (tmp_path / "cards.txt").write_text("A | b", encoding="utf-8")
    assert main(["diagram", "cards.txt", "--type", "cards", "-o", "cards.png", "--dpi", "96"]) == 0
    assert drawn[-1]["renderer"] == "browser-png-1" and 'id="block"' in drawn[-1]["text"]


def test_dpi_is_for_pixels_only(drawn, tmp_path, capsys):
    (tmp_path / "flow.mmd").write_text("flowchart LR\n  A --> B", encoding="utf-8")
    assert main(["diagram", "flow.mmd", "-o", "flow.svg", "--dpi", "300"]) == 1
    assert "no pixels" in capsys.readouterr().err


def test_a_png_only_tool_is_scaled_marked_and_put_in_a_pdf(drawn, tmp_path):
    (tmp_path / "box.ditaa").write_text("+--+\n|  |\n+--+", encoding="utf-8")
    assert main(["diagram", "box.ditaa", "-o", "box.png", "--dpi", "96"]) == 0
    with Image.open(tmp_path / "box.png") as image:
        assert image.size == (20, 10) and round(image.info["dpi"][0]) == 96  # half of 192 dpi
    assert main(["diagram", "box.ditaa", "-o", "box.pdf"]) == 0
    assert (tmp_path / "box.pdf").read_bytes().startswith(b"%PDF")
    assert all(c["renderer"] == "ditaa" for c in drawn)  # Pillow makes the PDF, not the container


def test_webp_is_a_lossless_copy_of_the_png(drawn, tmp_path):
    (tmp_path / "cards.txt").write_text("A | b", encoding="utf-8")
    assert main(["diagram", "cards.txt", "--type", "cards", "-o", "cards.webp"]) == 0
    with Image.open(tmp_path / "cards.webp") as image:
        assert image.format == "WEBP" and image.size == (40, 20)


def test_a_card_frames_an_svg_picture_with_its_title_and_caption(drawn, tmp_path):
    (tmp_path / "gauge.txt").write_text("0 | 50 | green\n50 | 100 | red", encoding="utf-8")
    args = ["diagram", "gauge.txt", "--type", "gauge", "--options", "value=40 min=0 max=100", "-o", "g.svg"]
    assert main([*args, "--chrome", "card", "--title", "Grid load", "--caption", "Measured at noon"]) == 0
    svg = (tmp_path / "g.svg").read_text(encoding="utf-8")
    root = ET.fromstring(svg.split("\n", 1)[1])
    texts = [el.text for el in root.findall("{http://www.w3.org/2000/svg}text")]
    assert texts == ["Grid load", "Measured at noon"]
    assert root.find("{http://www.w3.org/2000/svg}rect") is not None and drawn == []


def test_a_card_of_an_html_block_keeps_the_block_as_html(drawn, tmp_path):
    (tmp_path / "cards.txt").write_text("A | b", encoding="utf-8")
    assert main(["diagram", "cards.txt", "--type", "cards", "-o", "c.png", "--chrome", "card", "--title", "Parts"]) == 0
    page = drawn[-1]["text"]
    assert drawn[-1]["renderer"] == "block-html" and '<div class="fig-title">Parts</div>' in page
    assert '<div class="cards"' in page and "<img" not in page  # its text stays text, vector in a PDF


def test_a_markdown_file_in_webp_takes_its_titles(drawn, tmp_path):
    (tmp_path / "poster.md").write_text('# P\n\n```chart title="Messages a day"\nA | 1\n```\n', encoding="utf-8")
    assert main(["diagram", "poster.md", "-o", "images", "--format", "webp"]) == 0
    assert [p.name for p in (tmp_path / "images").iterdir()] == ["poster-01-messages-a-day.webp"]


# --- the Python API ---------------------------------------------------------------------------------


def test_the_api_draws_an_svg_block_with_no_container():
    import py_doc

    picture = py_doc.render_diagram("0 | 50 | green\n50 | 100 | red", kind="gauge", options="value=40 min=0 max=100")
    assert picture.has_svg and picture.to_svg().startswith("<?xml")
    assert picture._repr_svg_() == picture.to_svg() and picture._repr_png_() is None


def test_the_api_saves_by_extension_and_says_what_it_cannot(drawn, tmp_path):
    from py_doc.diagram_api import DiagramApiError, render_diagram

    picture = render_diagram("A | b", kind="cards", runtime=lambda: object())
    assert not picture.has_svg and picture._repr_svg_() is None
    assert picture._repr_png_().startswith(b"\x89PNG")
    assert picture.save(tmp_path / "c.png").is_file()
    with pytest.raises(DiagramApiError, match="PNG only"):
        picture.to_svg()
    with pytest.raises(DiagramApiError, match=r"\.svg, \.png, \.webp or \.pdf"):
        picture.save(tmp_path / "c.gif")
    with pytest.raises(DiagramApiError, match="not a type"):
        render_diagram("x", kind="sketch")


# --- --watch -----------------------------------------------------------------------------------------


def test_watch_draws_and_shows_the_picture_on_a_page(drawn, tmp_path, monkeypatch):
    import py_doc.watch

    seen = {}

    def watch(build, errors, **kwargs):
        seen["pages"], seen["sources"] = build()
        return 0

    monkeypatch.setattr(py_doc.watch, "watch", watch)
    (tmp_path / "flow.mmd").write_text("flowchart LR\n  A --> B", encoding="utf-8")
    assert main(["diagram", "flow.mmd", "-o", "flow.svg", "--watch", "--no-open"]) == 0
    page = seen["pages"]["flow"]
    assert page == (tmp_path / ".py-doc" / "preview" / "flow-diagram.html").resolve()
    assert "data:image/svg+xml;base64," in page.read_text(encoding="utf-8")
    assert seen["sources"] == {(tmp_path / "flow.mmd").resolve()}
