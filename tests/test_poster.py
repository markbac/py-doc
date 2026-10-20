"""``py-doc poster``: Markdown to one self-contained HTML poster."""

from __future__ import annotations

import base64
import textwrap
from pathlib import Path

import pytest

from py_doc import poster
from py_doc.app import main
from py_doc.config import ConfigError, parse_config
from py_doc.errors import ToolFailed
from py_doc.poster import PosterError, build
from py_doc.poster_themes import ThemeError

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


EXAMPLES = Path(__file__).parent.parent / "examples" / "poster"


@pytest.mark.parametrize("name, title", [("poster", "SN-100 Sensor Node"), ("landscape", "Commissioning an SN-100 network"), ("release", "SN-100 firmware 2.1")])
def test_the_example_posters_build(drawn, name, title):
    page, ctx = build(EXAMPLES / f"{name}.md", lambda: object())
    assert f"<title>{title}</title>" in page
    assert ctx.failed == 0


# --- orientation and columns ---------------------------------------------------------------------

SECTIONS = "".join(f"## {n}. Part\n\n{'Words. ' * size}\n\n" for n, size in enumerate((10, 10, 10, 10, 10, 10), 1))


def columns(page):
    return [column.count("<section>") for column in page.split('<div class="col">')[1:]]


def test_a_portrait_poster_is_two_columns_on_a_portrait_page(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\npaper: a3\n---\n" + SECTIONS), lambda: object())
    assert columns(page) == [3, 3]
    assert "size:297mm 420mm" in page and "R=1.4142" in page and 'class="poster portrait"' in page


def test_a_landscape_poster_is_three_columns_on_a_landscape_page(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\norientation: landscape\npaper: a3\n---\n" + SECTIONS), lambda: object())
    assert columns(page) == [2, 2, 2]
    assert "size:420mm 297mm" in page and "R=0.7071" in page and "MIN=1800" in page
    assert f"PAPER={420 / 25.4 * 96}" in page


def test_columns_and_split_choose_the_sections_of_each_column(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\ncolumns: 3\nsplit: 1, 4\n---\n" + SECTIONS), lambda: object())
    assert columns(page) == [1, 4, 1]
    page, _ = build(write(tmp_path, "---\nsplit: 2\n---\n" + SECTIONS), lambda: object())
    assert columns(page) == [2, 4]


def test_there_are_never_more_columns_than_sections(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\ncolumns: 4\n---\n## A\n\nOne.\n\n## B\n\nTwo.\n"), lambda: object())
    assert columns(page) == [1, 1]


@pytest.mark.parametrize(
    "front, message",
    [
        ("orientation: sideways", "orientation must be portrait or landscape"),
        ("columns: two", "columns must be a whole number"),
        ("columns: 0", "columns must be at least 1"),
        ("split: 1, 2", "split needs 1 number"),
        ("split: 6", "leaving at least one"),
        ("width: 100", "width must be at least 400"),
    ],
)
def test_a_layout_mistake_is_an_error(tmp_path, front, message):
    with pytest.raises(PosterError, match=message):
        build(write(tmp_path, f"---\n{front}\n---\n" + SECTIONS), lambda: object())


# --- themes --------------------------------------------------------------------------------------

BRAND = """\
extends: dark
colours:
  primary: "#0f5e5e"
palette:
  teal: "#0f5e5e"
fonts:
  body: "'Brand Sans', Arial, sans-serif"
  stylesheet: null
logo: logo.svg
"""


def brand(tmp_path, text=BRAND):
    (tmp_path / "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (tmp_path / "brand.yml").write_text(text, encoding="utf-8")
    return tmp_path / "brand.yml"


def test_the_default_theme_sets_every_colour_and_loads_the_fonts(tmp_path, drawn):
    page, _ = build(write(tmp_path), lambda: object())
    assert "--primary:#2a3150;" in page and "--font-body:'Source Serif 4'" in page
    assert '<link rel="stylesheet" href="https://fonts.googleapis.com/' in page
    assert "#2a3150}" not in page.split(":root{")[1].split("}", 1)[1]  # the CSS itself has no fixed colours


def test_a_built_in_theme_is_named_in_the_front_matter(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\ntheme: dark\n---\n## A\n\nText.\n"), lambda: object())
    assert "--page:#141923;" in page and "--strong:#f2f4f8;" in page


def test_the_print_theme_uses_installed_fonts(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\ntheme: print\n---\n## A\n\nText.\n"), lambda: object())
    assert "--page:#ffffff;" in page and "fonts.googleapis.com" not in page


def test_a_theme_file_extends_a_built_in_theme_and_brings_a_logo_palette_and_fonts(tmp_path, drawn):
    brand(tmp_path)
    text = "---\ntheme: brand.yml\n---\n## A\n\n```flow\n[Start|teal] -> [End|primary]\n```\n\n```mermaid\ngraph LR; A-->B\n```\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert "--primary:#0f5e5e;" in page and "--page:#141923;" in page  # its own colour, and the dark theme's
    assert "--font-body:'Brand Sans', Arial, sans-serif" in page and "fonts.googleapis.com" not in page
    assert '<header class="logo"><img alt="Logo" src="data:image/svg+xml;base64,' in page
    assert page.count('<div class="node" style="background:#0f5e5e">') == 2
    assert '"primaryBorderColor": "#0f5e5e"' in drawn[0][1] and "Brand Sans" in drawn[0][1]


def test_the_front_matter_logo_wins_over_the_themes(tmp_path, drawn):
    brand(tmp_path)
    (tmp_path / "other.png").write_bytes(PNG)
    page, _ = build(write(tmp_path, "---\ntheme: brand.yml\nlogo: other.png\n---\n## A\n\nText.\n"), lambda: object())
    assert 'src="data:image/png;base64,' in page


def test_the_theme_argument_wins_over_the_front_matter_and_the_project_default_comes_last(tmp_path, drawn):
    text = "---\ntheme: dark\n---\n## A\n\nText.\n"
    assert "--page:#ffffff;" in build(write(tmp_path, text), lambda: object(), theme="print")[0]
    assert "--page:#141923;" in build(write(tmp_path, text), lambda: object(), default_theme="print")[0]
    assert "--page:#ffffff;" in build(write(tmp_path, "## A\n\nText.\n"), lambda: object(), default_theme="print")[0]


@pytest.mark.parametrize(
    "text, message",
    [
        ("colours:\n  primery: red\n", "unknown colour 'primery'"),
        ("colours:\n  primary: 'red; x: y'\n", "is not a colour"),
        ("extends: neon\n", "extends 'neon' is not one of"),
        ("fonts:\n  body: '</style>'\n", "a character a font name cannot have"),
        ("fonts:\n  stylesheet: 'javascript:alert(1)'\n", "must be an http or https address"),
        ("logo: missing.png\n", "logo not found"),
        ("colour:\n  primary: red\n", "unknown key 'colour'"),
    ],
)
def test_a_theme_mistake_is_an_error(tmp_path, text, message):
    brand(tmp_path, text)
    with pytest.raises(ThemeError, match=message):
        build(write(tmp_path, "---\ntheme: brand.yml\n---\n## A\n\nText.\n"), lambda: object())


def test_an_unknown_theme_is_an_error(tmp_path):
    with pytest.raises(ThemeError, match="not one of default, dark, print"):
        build(write(tmp_path, "---\ntheme: neon\n---\n## A\n\nText.\n"), lambda: object())


def test_an_unknown_block_colour_is_an_error(tmp_path):
    with pytest.raises(ThemeError, match="'not a colour!' is not a colour"):
        build(write(tmp_path, "## A\n\n```flow\n[Start|not a colour!] -> [End]\n```\n"), lambda: object())


def test_the_project_sets_the_default_theme_and_the_command_line_wins(tmp_path, drawn, monkeypatch):
    monkeypatch.setattr("py_doc.poster_cli.connect", lambda settings: object())
    brand(tmp_path)
    (tmp_path / "py-doc.yml").write_text("poster:\n  theme: brand.yml\n", encoding="utf-8")
    source = write(tmp_path, "## A\n\nText.\n")
    assert main(["poster", str(source)]) == 0
    assert "--primary:#0f5e5e;" in (tmp_path / "poster.html").read_text(encoding="utf-8")
    assert main(["poster", str(source), "--theme", "print"]) == 0
    assert "--page:#ffffff;" in (tmp_path / "poster.html").read_text(encoding="utf-8")


def test_a_project_poster_theme_must_be_text(tmp_path):
    with pytest.raises(ConfigError, match="poster.theme must be str"):
        parse_config({"poster": {"theme": 3}}, tmp_path)
    with pytest.raises(ConfigError, match="unknown key 'colours' in poster"):
        parse_config({"poster": {"colours": {}}}, tmp_path)
    assert parse_config({"poster": {"theme": "brand.yml"}}, tmp_path).poster_theme == tmp_path / "brand.yml"
    assert parse_config({"poster": {"theme": "dark"}}, tmp_path).poster_theme == "dark"
