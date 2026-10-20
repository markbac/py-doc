"""``py-doc poster``: Markdown to one self-contained HTML poster."""

from __future__ import annotations

import base64
import textwrap

import pytest

from py_doc import poster
from py_doc.app import main
from py_doc.errors import ToolFailed
from py_doc.poster import PosterError, build

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16

POSTER = textwrap.dedent(
    """\
    ---
    title: Smart Gas Meter
    subtitle: How the valve decides
    byline: A. Author
    footer-left: G460
    footer-right: October 2026
    paper: a2
    ---

    ## Stats

    | Value | Label |
    |---|---|
    | 12 | Months |
    | 3 | Windows |

    ## Abstract

    The meter closes its **valve** on credit.

    ## 1. Valve: when it closes

    Text with `code`.

    ```mermaid
    graph LR; A-->B
    ```

    Fig. 1 The valve states.

    ```cards cols=2 style=top
    Credit | Supply on | green
    Debt | Supply off | red
    ```

    > Never open the valve remotely.

    ## 2. Screens

    ```lcd
    C 0012.340m3
    Gas ON
    -- Credit, supply on
    ```

    ```figure
    @segments
    title: Day
    5 | Unavailable | | blue
    3 | Available | detail | navy
    +++
    @flow
    [OPEN|navy] -closure-> [CLOSED|red]
    +++
    @lanes
    Window 1 | *Scheduled wake-up | Consumer wake-up
    A note under the lanes.
    ```

    ## Summary

    The valve is safe.

    ### Safe

    It fails closed.
    """
)


@pytest.fixture
def drawn(tmp_path, monkeypatch):
    """Diagrams drawn without the tool container: each one is a small PNG, and the text it got is kept."""
    texts = []

    def draw(runtime, renderer, text, kind, landscape, source_dir):
        texts.append((renderer.name, text, kind))
        picture = tmp_path / f"diagram{len(texts)}.png"
        picture.write_bytes(PNG)
        return picture

    monkeypatch.setattr(poster, "draw_cached", draw)
    return texts


def write(tmp_path, text=POSTER):
    path = tmp_path / "poster.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_page_has_every_part_of_the_poster(tmp_path, drawn):
    page, ctx = build(write(tmp_path), lambda: object())
    assert "<title>Smart Gas Meter</title>" in page
    assert '<div class="subtitle">How the valve decides</div>' in page
    assert '<div class="stat"><b>12</b><span>Months</span></div>' in page
    assert '<div class="abstract"><p>The meter closes its <strong>valve</strong> on credit.</p>' in page
    assert "1. Valve: <span>when it closes</span>" in page
    assert '<p class="caption">Fig. 1 The valve states.</p>' in page
    assert 'class="cards" style="grid-template-columns:repeat(2,minmax(0,1fr))"' in page
    assert 'border-top:4px solid #2e6b3a' in page
    assert "<blockquote>" in page
    assert '<div class="lcd"><div class="scr"><div>C 0012.340m3</div><div>Gas ON</div></div><div class="cap">Credit, supply on</div>' in page
    assert '<div class="fig-title">Day</div>' in page and 'class="bar" style="min-height:64px"' in page
    assert '<div class="node" style="background:#a3322b">CLOSED</div>' in page
    assert '<div class="cell fill">Scheduled wake‑up</div>' in page
    assert '<div class="fig-notes"><p>A note under the lanes.</p>' in page
    assert '<div class="banner">The valve is safe.</div>' in page and "<h3>Safe</h3>" in page
    assert "<b>G460</b><span>October 2026</span>" in page
    assert "size:420mm 594mm" in page
    assert (ctx.n, ctx.failed) == (1, 0)


def test_a_diagram_is_drawn_as_png_with_the_poster_theme_and_embedded(tmp_path, drawn):
    page, _ = build(write(tmp_path), lambda: object())
    [(name, text, kind)] = drawn
    assert (name, kind) == ("mermaid", "png")
    assert text.startswith("%%{init:") and text.endswith("graph LR; A-->B")
    assert f'src="data:image/png;base64,{base64.b64encode(PNG).decode()}"' in page


def test_a_mermaid_diagram_with_its_own_theme_keeps_it(tmp_path, drawn):
    build(write(tmp_path, "## A\n\n```mermaid\n%%{init: {}}%%\ngraph LR; A-->B\n```\n"), lambda: object())
    assert drawn[0][1] == "%%{init: {}}%%\ngraph LR; A-->B"


def test_a_poster_without_diagrams_does_not_start_the_container(tmp_path, drawn):
    def connect():
        raise AssertionError("the container was started")

    page, ctx = build(write(tmp_path, "## A\n\nNo diagrams.\n"), connect)
    assert "No diagrams." in page and ctx.n == 0


def test_a_broken_diagram_is_shown_as_code_and_the_poster_is_still_built(tmp_path, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise ToolFailed("mmdc", 1, "Parse error on line 1\nmore detail")

    monkeypatch.setattr(poster, "draw_cached", fail)
    page, ctx = build(write(tmp_path), lambda: object())
    assert ctx.failed == 1
    assert "<pre><code>graph LR; A--&gt;B</code></pre>" in page
    assert "mermaid diagram could not be rendered: Parse error on line 1" in page
    assert "mermaid diagram not rendered: Parse error on line 1" in caplog.text


def test_a_local_picture_is_embedded(tmp_path, drawn):
    (tmp_path / "logo.png").write_bytes(PNG)
    page, _ = build(write(tmp_path, "## A\n\n![Logo](logo.png)\n"), lambda: object())
    assert 'src="data:image/png;base64,' in page and "logo.png" not in page


@pytest.mark.parametrize(
    "text, message",
    [("No sections here.\n", "no sections found"), ("---\npaper: b5\n---\n## A\n\nText.\n", "paper must be one of")],
)
def test_a_poster_that_cannot_be_built_is_an_error(tmp_path, text, message):
    with pytest.raises(PosterError, match=message):
        build(write(tmp_path, text), lambda: object())


def test_the_command_writes_the_page_next_to_the_markdown(tmp_path, drawn, monkeypatch, capsys):
    monkeypatch.setattr("py_doc.poster_cli.connect", lambda settings: object())
    source = write(tmp_path)
    assert main(["poster", str(source)]) == 0
    assert (tmp_path / "poster.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    assert "(1 diagrams, 0 failed)" in capsys.readouterr().out
    assert main(["poster", str(source), "-o", str(tmp_path / "out.html")]) == 0
    assert (tmp_path / "out.html").is_file()


def test_the_command_reports_a_missing_file(tmp_path, capsys):
    assert main(["poster", str(tmp_path / "missing.md")]) == 1
    assert "not found" in capsys.readouterr().err
