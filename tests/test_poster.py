"""``py-doc poster``: Markdown to one self-contained HTML poster."""

from __future__ import annotations

import base64
import json
import re
import types
import urllib.error
import textwrap
from pathlib import Path

import jsonschema
import pytest
import yaml

import py_doc

from py_doc import poster_blocks
from py_doc.app import main
from py_doc.config import ConfigError, parse_config
from py_doc.errors import ConversionError, ToolFailed
from py_doc.poster import PosterError, build, print_pdf
from py_doc.poster_themes import ThemeError

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'

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
        picture = tmp_path / f"diagram{len(texts)}.{kind}"
        picture.write_bytes(PNG if kind == "png" else SVG)
        return picture

    monkeypatch.setattr(poster_blocks, "draw_cached", draw)
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
    assert '<b class="fl">G460</b><span class="fc"></span><span class="fr">October 2026</span>' in page
    assert "size:420mm 594mm" in page
    assert (ctx.n, ctx.failed) == (1, 0)


def test_a_diagram_is_drawn_as_svg_with_the_poster_theme_and_embedded(tmp_path, drawn):
    page, _ = build(write(tmp_path), lambda: object())
    [(name, text, kind)] = drawn
    assert (name, kind) == ("mermaid", "svg")  # vector, so it prints sharp like the rest of the poster
    assert text.startswith("---\nconfig: {") and text.endswith("---\ngraph LR; A-->B")
    config = yaml.safe_load(text.split("---\n")[1])["config"]  # front matter, not %%{init}%%, which drops a quoted font
    assert config["theme"] == "base" and config["themeVariables"]["fontFamily"].startswith("'Source Serif 4'")
    assert f'src="data:image/svg+xml;base64,{base64.b64encode(SVG).decode()}"' in page


def test_a_tool_that_draws_only_png_gives_a_png(tmp_path, drawn):
    page, _ = build(write(tmp_path, "## A\n\n```ditaa\n+--+\n```\n"), lambda: object())
    assert drawn[0][2] == "png" and 'src="data:image/png;base64,' in page


def test_a_mermaid_diagram_with_its_own_theme_keeps_it(tmp_path, drawn):
    build(write(tmp_path, "## A\n\n```mermaid\n%%{init: {}}%%\ngraph LR; A-->B\n```\n\n```mermaid\n---\nconfig: {look: classic}\n---\ngraph LR; C-->D\n```\n"), lambda: object())
    assert drawn[0][1] == "%%{init: {}}%%\ngraph LR; A-->B"
    assert drawn[1][1] == "---\nconfig: {look: classic}\n---\ngraph LR; C-->D"


def test_a_poster_without_diagrams_does_not_start_the_container(tmp_path, drawn):
    def connect():
        raise AssertionError("the container was started")

    page, ctx = build(write(tmp_path, "## A\n\nNo diagrams.\n"), connect)
    assert "No diagrams." in page and ctx.n == 0


def test_a_broken_diagram_is_shown_as_code_and_the_poster_is_still_built(tmp_path, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise ToolFailed("mmdc", 1, "Parse error on line 1\nmore detail")

    monkeypatch.setattr(poster_blocks, "draw_cached", fail)
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
    assert "size:297mm 420mm" in page and "R=1.4141" in page and 'class="poster portrait"' in page


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
    assert '<header class="align-centre logo-left"><img alt="Logo" src="data:image/svg+xml;base64,' in page
    assert page.count('<div class="node" style="background:#0f5e5e">') == 2
    assert '"primaryBorderColor": "#0f5e5e"' in drawn[0][1] and "Brand Sans" in drawn[0][1]


def test_the_front_matter_logo_wins_over_the_themes(tmp_path, drawn):
    brand(tmp_path)
    (tmp_path / "other.png").write_bytes(PNG)
    page, _ = build(write(tmp_path, "---\ntheme: brand.yml\nlogo: other.png\n---\n## A\n\nText.\n"), lambda: object())
    assert 'src="data:image/png;base64,' in page


def test_settings_win_over_the_front_matter_and_the_defaults_come_last(tmp_path, drawn):
    text = "---\ntheme: dark\n---\n## A\n\nText.\n"
    assert "--page:#ffffff;" in build(write(tmp_path, text), lambda: object(), settings={"theme": "print"})[0]
    assert "--page:#141923;" in build(write(tmp_path, text), lambda: object(), defaults={"theme": "print"})[0]
    assert "--page:#ffffff;" in build(write(tmp_path, "## A\n\nText.\n"), lambda: object(), defaults={"theme": "print"})[0]


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


def test_the_poster_section_takes_every_poster_setting(tmp_path):
    with pytest.raises(ConfigError, match="unknown key 'colors' in poster"):
        parse_config({"poster": {"colors": {}}}, tmp_path)
    with pytest.raises(ConfigError, match="poster.colours must be a mapping"):
        parse_config({"poster": {"colours": "red"}}, tmp_path)
    with pytest.raises(ConfigError, match="poster.columns must be a whole number"):
        parse_config({"poster": {"columns": 2.5}}, tmp_path)
    with pytest.raises(ConfigError, match="unknown key 'middle' in poster.footer"):
        parse_config({"poster": {"footer": {"middle": "x"}}}, tmp_path)
    config = parse_config({"poster": {"theme": "brand.yml", "logo": "logo.svg", "footer": {"logos": ["a.png"]}}}, tmp_path)
    assert config.poster["theme"] == tmp_path / "brand.yml" and config.poster["logo"] == tmp_path / "logo.svg"
    assert config.poster["footer"]["logos"] == [tmp_path / "a.png"]
    assert parse_config({"poster": {"theme": "dark"}}, tmp_path).poster["theme"] == "dark"


# --- py-doc.yml posters ---------------------------------------------------------------------------


def project(tmp_path, posters, defaults=None):
    data = {"posters": posters}
    if defaults:
        data["poster"] = defaults
    (tmp_path / "py-doc.yml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_a_poster_of_py_doc_yml_has_its_source_output_and_settings(tmp_path):
    config = parse_config({"posters": {"sn100": {"source": "p.md", "orientation": "landscape", "colours": {"primary": "#123456"}}}}, tmp_path)
    poster = config.posters["sn100"]
    assert (poster.source, poster.output) == (tmp_path / "p.md", tmp_path / "build" / "sn100.html")
    assert poster.settings == {"orientation": "landscape", "colours": {"primary": "#123456"}}
    with pytest.raises(ConfigError, match="posters.x needs a source"):
        parse_config({"posters": {"x": {"orientation": "landscape"}}}, tmp_path)
    with pytest.raises(ConfigError, match="unknown key 'orientaton' in posters.x"):
        parse_config({"posters": {"x": {"source": "p.md", "orientaton": "landscape"}}}, tmp_path)


def test_every_poster_of_py_doc_yml_is_built_with_its_entry_over_the_front_matter(tmp_path, drawn, monkeypatch, capsys):
    monkeypatch.setattr("py_doc.poster_cli.connect", lambda settings: object())
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "---\norientation: portrait\ncolours: {primary: '#111111', accent: '#222222'}\n---\n## A\n\nText.\n")
    project(
        tmp_path,
        {"wall": {"source": "poster.md", "output": "out/wall.html", "orientation": "landscape", "colours": {"primary": "#333333"}},
         "desk": {"source": "poster.md"}},
        defaults={"colours": {"secondary": "#444444", "accent": "#555555"}},
    )  # fmt: skip
    assert main(["poster"]) == 0
    wall = (tmp_path / "out" / "wall.html").read_text(encoding="utf-8")
    desk = (tmp_path / "build" / "desk.html").read_text(encoding="utf-8")
    assert 'class="poster landscape"' in wall and "--primary:#333333;" in wall
    assert "--accent:#222222;" in wall and "--secondary:#444444;" in wall  # front matter over defaults, defaults kept
    assert 'class="poster portrait"' in desk and "--primary:#111111;" in desk
    assert main(["poster", "desk"]) == 0
    assert main(["poster", "nothing"]) == 1
    assert "is not a Markdown file or a poster of py-doc.yml. The posters of py-doc.yml are: wall, desk" in capsys.readouterr().err
    assert main(["poster", "-o", "x.html"]) == 1


def test_without_posters_the_command_asks_for_one(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["poster"]) == 1
    assert "no poster given" in capsys.readouterr().err


def test_the_command_line_sets_variables_and_conditions(tmp_path, drawn, monkeypatch):
    monkeypatch.setattr("py_doc.poster_cli.connect", lambda settings: object())
    source = write(tmp_path, "## A\n\nVersion {{version}}.\n\n[[IF: internal]]\nSecret.\n[[ENDIF]]\n")
    assert main(["poster", str(source), "--var", "version=2.1", "--condition", "internal=false"]) == 0
    page = (tmp_path / "poster.html").read_text(encoding="utf-8")
    assert "Version 2.1." in page and "Secret." not in page


# --- py-doc syntax --------------------------------------------------------------------------------


def test_includes_conditions_and_variables_from_the_settings(tmp_path, drawn):
    (tmp_path / "part.md").write_text("Included {{name}}.\n", encoding="utf-8")
    (tmp_path / "code.py").write_text("print('hi')\n", encoding="utf-8")
    text = "---\nvariables: {name: text}\nconditions: {internal: true}\n---\n## A\n\n[[INCLUDE: part.md]]\n\n[[INCLUDE-CODE: code.py]]\n\n[[NOT: internal]]\nPublic.\n[[ENDIF]]\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert "Included text." in page and "Public." not in page
    assert '<pre><code class="language-python">print(\'hi\')' in page


def test_a_missing_include_is_an_error_with_the_file(tmp_path):
    with pytest.raises(ConversionError, match="included file not found"):
        build(write(tmp_path, "## A\n\n[[INCLUDE: missing.md]]\n"), lambda: object())


def test_captions_callouts_and_word_markers(tmp_path, drawn):
    text = textwrap.dedent(
        """\
        ## A

        [[CAPTION:Figure]] The valve.

        ```dot
        digraph { a -> b }
        ```

        > [!WARNING]
        > Disconnect the battery first.

        > **Tip:** use the app.

        > A plain quote.

        [[LANDSCAPE]]
        [[STYLE:Lead Paragraph]] Lead text.

        [[PAGEBREAK]]

        ```markdown
        [[CAPTION:Figure]] shown as code
        ```
        """
    )
    page, _ = build(write(tmp_path, text), lambda: object())
    assert '<p class="caption">The valve.</p>' in page
    assert '<blockquote class="callout warning"><p class="callout-title">Warning</p><p>Disconnect the battery first.</p>' in page
    assert '<blockquote class="callout tip">\n<p><strong>Tip:</strong> use the app.</p>' in page
    assert "<blockquote>\n<p>A plain quote.</p>" in page
    assert "<p>Lead text.</p>" in page
    assert "LANDSCAPE" not in page and "pagebreak" not in page and ":::" not in page
    assert "[[CAPTION:Figure]] shown as code" in page


def test_a_front_matter_key_that_is_not_a_setting_is_ignored_with_a_warning(tmp_path, drawn, caplog):
    build(write(tmp_path, "---\nauthor: A. Writer\n---\n## A\n\nText.\n"), lambda: object())
    assert "'author' is not a poster setting, so it is ignored" in caplog.text


def test_front_matter_that_is_not_yaml_is_an_error(tmp_path):
    with pytest.raises(PosterError, match="front matter is not valid YAML"):
        build(write(tmp_path, "---\ntitle: [unclosed\n---\n## A\n\nText.\n"), lambda: object())


# --- layout ---------------------------------------------------------------------------------------


def test_a_wide_section_spans_the_columns_and_splits_them_into_groups(tmp_path, drawn):
    text = "## 1. A\n\nOne.\n\n## 2. B\n\nTwo.\n\n## 3. Wide {.wide colour=red}\n\nAll across.\n\n## 4. C\n\nThree.\n\n## 5. D\n\nFour.\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert page.count('<div class="cols"') == 2
    assert '<section class="wide"><h2 style="background:#a3322b">3. Wide</h2>' in page
    assert page.index("2. B") < page.index("3. Wide") < page.index("4. C")
    with pytest.raises(PosterError, match="split cannot be used with wide sections"):
        build(write(tmp_path, "---\nsplit: 1\n---\n" + text), lambda: object())


def test_an_unknown_heading_attribute_is_a_warning(tmp_path, drawn, caplog):
    page, _ = build(write(tmp_path, "## A {.narrow}\n\nText.\n"), lambda: object())
    assert "<h2>A</h2>" in page and "has '.narrow', which a poster does not use" in caplog.text


def test_the_header_aligns_and_puts_the_logo_on_either_side_or_none(tmp_path, drawn):
    (tmp_path / "logo.png").write_bytes(PNG)
    base = "logo: logo.png\n"
    page, _ = build(write(tmp_path, f"---\n{base}header: {{align: left, logo: right}}\n---\n## A\n\nText.\n"), lambda: object())
    assert '<header class="align-left logo-right"><img alt="Logo"' in page
    page, _ = build(write(tmp_path, f"---\n{base}header: {{logo: none}}\n---\n## A\n\nText.\n"), lambda: object())
    assert '<header class="align-centre"><h1>' in page
    with pytest.raises(PosterError, match="align must be centre or left, not 'middle'"):
        build(write(tmp_path, "---\nheader: {align: middle}\n---\n## A\n\nText.\n"), lambda: object())


def test_the_footer_has_three_texts_logos_and_a_qr_code(tmp_path, drawn):
    (tmp_path / "a.png").write_bytes(PNG)
    text = "---\nfooter: {left: '**SN-100**', centre: Middle, right: Right, logos: [a.png], qr: 'https://example.com/sn100', qr-label: Scan me}\n---\n## A\n\nText.\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert '<b class="fl"><strong>SN-100</strong></b><span class="fc">Middle</span><span class="fr">Right</span>' in page
    assert '<div class="logos"><img alt="Logo" src="data:image/png;base64,' in page
    assert '<div class="fqr"><svg' in page and "<span>Scan me</span>" in page
    with pytest.raises(PosterError, match="footer logo not found"):
        build(write(tmp_path, "---\nfooter: {logos: [missing.png]}\n---\n## A\n\nText.\n"), lambda: object())


def test_the_old_footer_keys_still_work(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\nfooter-left: L\nfooter-right: R\n---\n## A\n\nText.\n"), lambda: object())
    assert '<b class="fl">L</b>' in page and '<span class="fr">R</span>' in page


# --- blocks ---------------------------------------------------------------------------------------


def test_stats_show_a_trend_whose_colour_follows_its_direction_or_verdict(tmp_path, drawn):
    text = "## Stats\n\n| Value | Label | Change | Verdict |\n|---|---|---|---|\n| 5 y | Life | +14 % | |\n| 4 s | Join | -7 s | good |\n| 3 | Faults | +1 | bad |\n| 2 | Same | 0 | |\n\n## A\n\nText.\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert '<em class="trend good">▲ +14 %</em>' in page
    assert '<em class="trend good">▼ -7 s</em>' in page
    assert '<em class="trend bad">▲ +1</em>' in page
    assert '<em class="trend good">▶ 0</em>' in page


def test_a_timeline_is_a_row_or_a_column_of_milestones(tmp_path, drawn):
    code = "Jan 2026 | Design | frozen | coral\nMar 2026 | Pilot"
    page, _ = build(write(tmp_path, f"## A\n\n```timeline\n{code}\n```\n\n```timeline vertical\n{code}\n```\n"), lambda: object())
    assert '<i style="background:coral"></i><b>Jan 2026</b><span>Design</span><small>frozen</small>' in page
    assert '<i style="background:#4a7fc1"></i><b>Mar 2026</b><span>Pilot</span></div>' in page  # the accent by default
    assert '<div class="timeline vertical">' in page


@pytest.mark.parametrize("kind", ["column", "bar", "line"])
def test_a_chart_is_svg_in_the_theme_colours(tmp_path, drawn, kind):
    code = f'```chart type={kind} title="Messages a day" unit=" msg"\nseries: 2.0, 2.1\nMon | 1440 | 900\nTue | 1440 | -50\n```'
    page, _ = build(write(tmp_path, f"## A\n\n{code}\n"), lambda: object())
    svg = page.split('<svg class="chart"', 1)[1].split("</svg>", 1)[0]
    assert '<div class="fig-title">Messages a day</div>' in page
    assert "#3f74b8" in svg and "#4a7fc1" in svg  # secondary, then accent
    assert ">2.0</text>" in svg and ">2.1</text>" in svg and ">Mon</text>" in svg


@pytest.mark.parametrize(
    "code, message",
    [
        ("```chart type=pie\nA | 1\n```", "chart type must be one of column, bar, line"),
        ("```chart\nA | lots\n```", "needs numbers after the label"),
        ("```chart\nA\n```", "has no value"),
        ("```chart\n```", "at least one"),
        ("```qr\n```", "needs the text or address"),
    ],
)
def test_a_block_mistake_is_an_error(tmp_path, code, message):
    with pytest.raises(PosterError, match=message):
        build(write(tmp_path, f"## A\n\n{code}\n"), lambda: object())


def test_a_qr_block_draws_the_code_with_its_label(tmp_path, drawn):
    page, _ = build(write(tmp_path, '## A\n\n```qr size=200 label="The manual"\nhttps://example.com/manual\n```\n'), lambda: object())
    assert '<div class="qr"><svg' in page and '<div class="cap">The manual</div>' in page
    assert 'stroke="#2a3150"' in page


def test_references_are_a_list_above_the_footer(tmp_path, drawn):
    page, _ = build(write(tmp_path, "## A\n\nText [1].\n\n## References\n\n1. SN-100 datasheet, SN-DS-001.\n1. MQTT 5.0, OASIS.\n"), lambda: object())
    refs = page.split('<div class="refs">', 1)[1]
    assert refs.startswith("<b>References</b><ol>") and "<li>MQTT 5.0, OASIS.</li>" in refs
    assert refs.index("</ol>") < refs.index("<footer>")


def test_a_directive_mistake_names_the_line_of_the_file(tmp_path):
    with pytest.raises(ConversionError, match=r"poster.md:7: included file not found"):
        build(write(tmp_path, "---\ntitle: T\n---\n## A\n\nText.\n[[INCLUDE: missing.md]]\n"), lambda: object())


def test_text_too_long_for_a_qr_code_is_an_error(tmp_path):
    with pytest.raises(PosterError, match="too long for a QR code"):
        build(write(tmp_path, "## A\n\n```qr\n" + "x" * 8000 + "\n```\n"), lambda: object())


def test_the_old_and_new_footer_keys_combine(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\nfooter-left: L\nfooter: {right: R}\n---\n## A\n\nText.\n"), lambda: object())
    assert '<b class="fl">L</b>' in page and '<span class="fr">R</span>' in page


@pytest.mark.parametrize("paper", ["a0", "a1", "a2", "a3", "a4"])
@pytest.mark.parametrize("orientation", ["portrait", "landscape"])
def test_the_poster_is_never_taller_than_its_page(tmp_path, drawn, paper, orientation):
    """A poster even a fraction of a millimetre taller than the page prints a second, empty page."""
    page, _ = build(write(tmp_path, f"---\npaper: {paper}\norientation: {orientation}\n---\n## A\n\nText.\n"), lambda: object())
    ratio = float(re.search(r"R=([\d.]+)", page)[1])
    width, height = (int(x) for x in re.search(r"size:(\d+)mm (\d+)mm", page).groups())
    assert width * ratio <= height and height - width * ratio < 0.1  # under a tenth of a millimetre short


# --- PDF ------------------------------------------------------------------------------------------


class PrintingRuntime:
    """Stands in for the tool container: records the command and writes what Chromium would."""

    def __init__(self, output=b"%PDF-1.7\n%fake\n"):
        self.calls, self.output = [], output

    def run(self, argv, *, mounts=(), workdir=None, env=None, timeout=None, **_):
        self.calls.append({"argv": argv, "mounts": mounts, "env": env, "page": Path(argv[2]).read_text(encoding="utf-8")})
        Path(argv[3]).write_bytes(self.output)


def test_a_poster_prints_to_pdf_with_chromium_in_the_container(tmp_path):
    runtime = PrintingRuntime()
    print_pdf(runtime, "<!doctype html><title>T</title>", tmp_path / "out" / "poster.pdf")
    assert (tmp_path / "out" / "poster.pdf").read_bytes().startswith(b"%PDF")
    (call,) = runtime.calls
    assert call["argv"][0] == "node" and Path(call["argv"][1]).name == "poster_pdf.js"
    assert call["page"].startswith("<!doctype html>")
    assert call["argv"][4] == "/etc/py-doc/puppeteer.json" and call["env"] == {"NODE_PATH": "/opt/node/node_modules"}
    assert any(m.writable for m in call["mounts"]) and any(Path(m.source).name == "tools" for m in call["mounts"])


def test_a_pdf_that_is_not_a_pdf_is_an_error(tmp_path):
    with pytest.raises(PosterError, match="Chromium wrote no PDF"):
        print_pdf(PrintingRuntime(b"oops"), "<html>", tmp_path / "poster.pdf")


def test_the_pdf_setting_and_the_pdf_option(tmp_path, drawn, monkeypatch, capsys):
    printed = []
    monkeypatch.setattr("py_doc.poster_cli.connect", lambda settings: object())
    monkeypatch.setattr("py_doc.poster.print_pdf", lambda runtime, page, pdf: printed.append(pdf))
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "## A\n\nText.\n")
    project(tmp_path, {"wall": {"source": "poster.md", "pdf": True}, "desk": {"source": "poster.md", "pdf": "print/desk.pdf"},
                       "screen": {"source": "poster.md"}})  # fmt: skip
    assert main(["poster"]) == 0
    assert printed == [tmp_path / "build" / "wall.pdf", tmp_path / "print" / "desk.pdf"]
    assert "wrote " + str(tmp_path / "build" / "wall.pdf") in capsys.readouterr().out
    printed.clear()
    assert main(["poster", "screen", "--pdf"]) == 0
    assert printed == [tmp_path / "build" / "screen.pdf"]
    printed.clear()
    assert main(["poster", "wall", "--no-pdf"]) == 0
    assert printed == []


def test_the_pdf_setting_is_true_false_or_a_path(tmp_path):
    with pytest.raises(ConfigError, match="posters.x.pdf must be true, false or a path"):
        parse_config({"posters": {"x": {"source": "p.md", "pdf": 3}}}, tmp_path)
    assert parse_config({"poster": {"pdf": "a.pdf"}}, tmp_path).poster["pdf"] == tmp_path / "a.pdf"
    assert parse_config({"poster": {"pdf": False}}, tmp_path).poster["pdf"] is False


def test_the_footer_shows_the_document_and_version_in_small_type(tmp_path, drawn):
    text = "---\nfooter: {left: SN-100, document: SN-PO-003, version: '{{v}}'}\nvariables: {v: '2.1'}\n---\n## A\n\nText.\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert '<div class="docinfo"><span>SN-PO-003</span><span>Version 2.1</span></div>' in page
    assert page.index("</footer>") < page.index('<div class="docinfo">')
    assert ".docinfo{" in page and "font-size:12px" in page.split(".docinfo{", 1)[1].split("}", 1)[0]


def test_the_document_number_and_version_of_the_front_matter_are_the_defaults(tmp_path, drawn):
    page, _ = build(write(tmp_path, "---\ndocument_number: SN-PO-004\nversion: '3.0'\n---\n## A\n\nText.\n"), lambda: object())
    assert '<div class="docinfo"><span>SN-PO-004</span><span>Version 3.0</span></div>' in page
    page, _ = build(write(tmp_path, "---\nversion: '3.0'\nfooter: {version: 3.1}\n---\n## A\n\nText.\n"), lambda: object())
    assert '<div class="docinfo"><span>Version 3.1</span></div>' in page  # the footer's own wins
    page, _ = build(write(tmp_path, "## A\n\nText.\n"), lambda: object())
    assert 'class="docinfo"' not in page


# --- py-doc build ---------------------------------------------------------------------------------


@pytest.fixture
def documents(monkeypatch):
    """py-doc build without pandoc: each document 'builds' and the names are recorded."""
    built = []

    def build_document(config, doc, formats, *args, **kwargs):
        built.append((doc.id, formats))
        return []

    monkeypatch.setattr("py_doc.app.build_document", build_document)
    monkeypatch.setattr("py_doc.app.connect", lambda settings: types.SimpleNamespace(image="tools:test", engine=None))
    monkeypatch.setattr("py_doc.poster.print_pdf", lambda runtime, page, pdf: pdf.write_bytes(b"%PDF-1.7\n"))
    return built


def build_project(tmp_path, documents=True):
    write(tmp_path, "## A\n\nText.\n")
    (tmp_path / "guide.md").write_text("# Guide\n\nText.\n", encoding="utf-8")
    data = {"posters": {"wall": {"source": "poster.md"}, "desk": {"source": "poster.md", "pdf": True}}, "reports": {"path": "build/report.json"}}
    if documents:
        data["documents"] = {"guide": {"sources": ["guide.md"]}}
    (tmp_path / "py-doc.yml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_build_makes_the_documents_then_every_poster(tmp_path, drawn, documents, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build_project(tmp_path)
    assert main(["build"]) == 0
    assert [name for name, _ in documents] == ["guide"]
    assert (tmp_path / "build" / "wall.html").is_file() and (tmp_path / "build" / "desk.html").is_file()
    assert (tmp_path / "build" / "desk.pdf").is_file() and not (tmp_path / "build" / "wall.pdf").exists()
    report = json.loads((tmp_path / "build" / "report.json").read_text(encoding="utf-8"))
    assert [s["step"] for s in report["steps"]][-3:] == ["documents", "posters", "verify"]
    assert {"step": "posters", "status": "ok", "detail": "2 of 2 built"} in report["steps"]
    outputs = {o["path"]: o["format"] for d in report["documents"] for o in d["outputs"]}
    assert outputs == {"build/wall.html": "html", "build/desk.html": "html", "build/desk.pdf": "pdf"}
    jsonschema.validate(report, json.loads((Path(py_doc.__file__).parent / "report.schema.json").read_text(encoding="utf-8")))


def test_build_names_documents_or_posters(tmp_path, drawn, documents, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    build_project(tmp_path)
    assert main(["build", "wall"]) == 0
    assert documents == [] and (tmp_path / "build" / "wall.html").is_file() and not (tmp_path / "build" / "desk.html").exists()
    assert main(["build", "guide"]) == 0
    assert [name for name, _ in documents] == ["guide"] and not (tmp_path / "build" / "desk.html").exists()
    assert main(["build", "nothing"]) == 1
    assert "Unknown document(s) or poster(s): nothing. Defined: guide; posters: wall, desk" in capsys.readouterr().err


def test_build_format_poster_builds_only_the_posters_and_another_format_none(tmp_path, drawn, documents, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build_project(tmp_path)
    assert main(["build", "-f", "poster"]) == 0
    assert documents == [] and (tmp_path / "build" / "wall.html").is_file()
    (tmp_path / "build" / "wall.html").unlink()
    assert main(["build", "-f", "docx"]) == 0
    assert documents == [("guide", ["docx"])] and not (tmp_path / "build" / "wall.html").exists()


def test_build_of_a_project_with_only_posters(tmp_path, drawn, documents, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build_project(tmp_path, documents=False)
    assert main(["build"]) == 0
    assert (tmp_path / "build" / "wall.html").is_file()


def test_build_reports_a_poster_that_fails_and_still_builds_the_others(tmp_path, drawn, documents, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    build_project(tmp_path)
    (tmp_path / "bad.md").write_text("No sections.\n", encoding="utf-8")
    config = yaml.safe_load((tmp_path / "py-doc.yml").read_text(encoding="utf-8"))
    config["posters"]["wall"]["source"] = "bad.md"
    (tmp_path / "py-doc.yml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    assert main(["build"]) == 1
    assert "wall: " in capsys.readouterr().err and (tmp_path / "build" / "desk.html").is_file()
    report = json.loads((tmp_path / "build" / "report.json").read_text(encoding="utf-8"))
    assert {"step": "posters", "status": "failed", "detail": "1 of 2 built"} in report["steps"]


def test_build_passes_variables_and_conditions_to_posters(tmp_path, drawn, documents, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "## A\n\nVersion {{version}}.\n\n[[IF: internal]]\nSecret.\n[[ENDIF]]\n")
    (tmp_path / "py-doc.yml").write_text("posters:\n  wall: {source: poster.md}\n", encoding="utf-8")
    assert main(["build", "--var", "version=3", "--condition", "internal=false"]) == 0
    page = (tmp_path / "build" / "wall.html").read_text(encoding="utf-8")
    assert "Version 3." in page and "Secret." not in page


# --- fonts ----------------------------------------------------------------------------------------

WOFF2 = b"wOF2" + b"\0" * 32
FONT_CSS = """/* latin */
@font-face {
  font-family: 'Brand Sans';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.example.com/brand-400.woff2) format('woff2');
}
@font-face {
  font-family: 'Brand Sans';
  font-weight: 700;
  src: url(https://fonts.example.com/brand-700.woff2) format('woff2');
}
"""


@pytest.fixture
def web(tmp_path, monkeypatch):
    """A stand-in for the web: answers from a dict, and records what was asked."""
    monkeypatch.setenv("PY_DOC_CACHE", str(tmp_path / "cache"))
    pages = {"https://fonts.example.com/css?family=Brand": FONT_CSS.encode(),
             "https://fonts.example.com/brand-400.woff2": WOFF2, "https://fonts.example.com/brand-700.woff2": WOFF2 + b"7"}  # fmt: skip
    asked = []

    class Response:
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout=None):
        asked.append(request.full_url)
        assert "Chrome" in request.get_header("User-agent")
        if request.full_url not in pages:
            raise urllib.error.URLError("no route to host")
        return Response(pages[request.full_url])

    monkeypatch.setattr("py_doc.poster_fonts.urllib.request.urlopen", urlopen)
    return pages, asked


def font_theme(tmp_path, extra=""):
    (tmp_path / "theme.yml").write_text(
        "fonts:\n  body: \"'Brand Sans', Arial, sans-serif\"\n  stylesheet: https://fonts.example.com/css?family=Brand\n" + extra, encoding="utf-8"
    )


def test_a_theme_s_font_files_are_embedded(tmp_path, drawn):
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "Brand-Bold.woff2").write_bytes(WOFF2)
    (tmp_path / "theme.yml").write_text(
        "fonts:\n  heading: \"'Brand', Arial, sans-serif\"\n  files:\n    - {family: Brand, file: fonts/Brand-Bold.woff2, weight: 700}\n", encoding="utf-8"
    )
    page, _ = build(write(tmp_path, "---\ntheme: theme.yml\n---\n## A\n\nText.\n"), lambda: object())
    data = base64.b64encode(WOFF2).decode()
    assert f"@font-face{{font-family:'Brand';font-weight:700;font-style:normal;font-display:swap;src:url(data:font/woff2;base64,{data}) format('woff2')}}" in page
    assert '<link rel="stylesheet" href="https://fonts.googleapis.com/' in page  # the default stylesheet is still linked


def test_font_files_named_in_py_doc_yml_are_from_py_doc_yml(tmp_path):
    (tmp_path / "brand").mkdir()
    (tmp_path / "brand" / "a.ttf").write_bytes(b"\0")
    config = parse_config({"poster": {"fonts": {"files": [{"family": "A", "file": "brand/a.ttf"}]}}}, tmp_path)
    assert config.poster["fonts"]["files"][0]["file"] == str(tmp_path / "brand" / "a.ttf")


@pytest.mark.parametrize(
    "files, message",
    [
        ("files: x", "fonts.files must be a list"),
        ("files:\n    - {file: a.woff2}", r"fonts.files\[1\] needs a family and a file"),
        ("files:\n    - {family: \"A'; }\", file: a.woff2}", "has a character a font name cannot have"),
        ("files:\n    - {family: A, file: a.woff2, weight: bold}", "weight must be 100 to 900"),
        ("files:\n    - {family: A, file: a.woff2, style: oblique}", "style must be normal or italic"),
        ("files:\n    - {family: A, file: a.png}", "is not a font file"),
        ("files:\n    - {family: A, file: missing.woff2}", "font file not found"),
        ("files:\n    - {family: A, file: a.woff2, size: 3}", "unknown key 'size'"),
    ],
)
def test_a_font_file_mistake_is_an_error(tmp_path, files, message):
    (tmp_path / "a.woff2").write_bytes(WOFF2)
    (tmp_path / "a.png").write_bytes(PNG)
    (tmp_path / "theme.yml").write_text("fonts:\n  " + files + "\n", encoding="utf-8")
    with pytest.raises(ThemeError, match=message):
        build(write(tmp_path, "---\ntheme: theme.yml\n---\n## A\n\nText.\n"), lambda: object())


def test_embed_fonts_puts_the_web_fonts_in_the_page_and_keeps_them(tmp_path, drawn, web):
    pages, asked = web
    font_theme(tmp_path)
    text = "---\ntheme: theme.yml\nembed_fonts: true\n---\n## A\n\nText.\n"
    page, _ = build(write(tmp_path, text), lambda: object())
    assert "<link" not in page and "fonts.example.com" not in page
    assert f"url(data:font/woff2;base64,{base64.b64encode(WOFF2).decode()}) format('woff2')" in page
    assert f"url(data:font/woff2;base64,{base64.b64encode(WOFF2 + b'7').decode()})" in page
    assert len(asked) == 3
    build(write(tmp_path, text), lambda: object())
    assert len(asked) == 3  # the second build is from the cache, with no network
    assert len(list((tmp_path / "cache" / "fonts").iterdir())) == 3


def test_a_font_download_that_fails_leaves_the_link_and_warns(tmp_path, drawn, web, caplog):
    pages, _ = web
    del pages["https://fonts.example.com/brand-700.woff2"]
    font_theme(tmp_path)
    page, _ = build(write(tmp_path, "---\ntheme: theme.yml\nembed_fonts: true\n---\n## A\n\nText.\n"), lambda: object())
    assert '<link rel="stylesheet" href="https://fonts.example.com/css?family=Brand">' in page
    assert "could not be embedded, so the page links them instead" in caplog.text


def test_a_stylesheet_that_is_not_font_faces_is_not_put_in_the_page(tmp_path, drawn, web, caplog):
    pages, _ = web
    pages["https://fonts.example.com/css?family=Brand"] = b"</style><script>alert(1)</script>"
    font_theme(tmp_path)
    page, _ = build(write(tmp_path, "---\ntheme: theme.yml\nembed_fonts: true\n---\n## A\n\nText.\n"), lambda: object())
    assert "alert(1)" not in page and "is not a plain list of @font-face rules" in caplog.text


def test_embedded_fonts_over_the_limit_are_a_warning(tmp_path, drawn, web, caplog, monkeypatch):
    monkeypatch.setattr("py_doc.poster_fonts.MAX_BYTES", 10)
    font_theme(tmp_path)
    build(write(tmp_path, "---\ntheme: theme.yml\nembed_fonts: true\n---\n## A\n\nText.\n"), lambda: object())
    assert "the page is slow to send and open" in caplog.text


def test_without_embed_fonts_nothing_is_downloaded(tmp_path, drawn, web):
    _, asked = web
    font_theme(tmp_path)
    page, _ = build(write(tmp_path, "---\ntheme: theme.yml\n---\n## A\n\nText.\n"), lambda: object())
    assert asked == [] and '<link rel="stylesheet" href="https://fonts.example.com/css?family=Brand">' in page


def test_the_embed_fonts_option_wins_over_the_setting(tmp_path, drawn, web, monkeypatch):
    _, asked = web
    monkeypatch.setattr("py_doc.poster_cli.connect", lambda settings: object())
    font_theme(tmp_path)
    source = write(tmp_path, "---\ntheme: theme.yml\nembed_fonts: true\n---\n## A\n\nText.\n")
    assert main(["poster", str(source), "--no-embed-fonts"]) == 0
    assert asked == []
    assert main(["poster", str(write(tmp_path, "---\ntheme: theme.yml\n---\n## A\n\nText.\n")), "--embed-fonts"]) == 0
    assert "<link" not in (tmp_path / "poster.html").read_text(encoding="utf-8")


def test_embed_fonts_is_true_false_or_a_list_of_subsets(tmp_path):
    for bad in ("yes", [], ["Latin!"], [3]):
        with pytest.raises(ConfigError, match="poster.embed_fonts must be true, false or a list of subsets"):
            parse_config({"poster": {"embed_fonts": bad}}, tmp_path)
    assert parse_config({"poster": {"embed_fonts": ["latin", "latin-ext"]}}, tmp_path).poster["embed_fonts"] == ["latin", "latin-ext"]


SUBSET_CSS = """/* cyrillic */
@font-face {
  font-family: 'Brand Sans';
  src: url(https://fonts.example.com/brand-cyrillic.woff2) format('woff2');
}
/* latin */
@font-face {
  font-family: 'Brand Sans';
  src: url(https://fonts.example.com/brand-400.woff2) format('woff2');
}
@font-face {
  font-family: 'Brand Sans';
  font-weight: 700;
  src: url(https://fonts.example.com/brand-700.woff2) format('woff2');
}
"""


def test_embed_fonts_with_subsets_keeps_and_downloads_only_those(tmp_path, drawn, web):
    pages, asked = web
    pages["https://fonts.example.com/css?family=Brand"] = SUBSET_CSS.encode()
    pages["https://fonts.example.com/brand-cyrillic.woff2"] = b"cyrillic"
    font_theme(tmp_path)
    page, _ = build(write(tmp_path, "---\ntheme: theme.yml\nembed_fonts: [latin]\n---\n## A\n\nText.\n"), lambda: object())
    assert "brand-cyrillic" not in " ".join(asked) and base64.b64encode(b"cyrillic").decode() not in page
    assert page.count("@font-face") == 2  # the latin face, and the one with no subset named
    assert "<link" not in page


def test_the_page_balances_the_columns_by_height_unless_split_chooses(tmp_path, drawn):
    page, _ = build(write(tmp_path, SECTIONS), lambda: object())
    assert '<div class="cols" data-balance>' in page
    assert "function balance()" in page and "balance();return p.scrollHeight" in page  # on every width it tries
    page, _ = build(write(tmp_path, "---\nsplit: 2\n---\n" + SECTIONS), lambda: object())
    assert '<div class="cols">' in page and "data-balance>" not in page


# --- lint -----------------------------------------------------------------------------------------

EXAMPLE_POSTERS = Path(__file__).parent.parent / "examples" / "poster"


def test_the_example_posters_lint_clean_without_the_document_structure_rules(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLE_POSTERS.parent)
    assert main(["lint", "poster", "--engine", "builtin", "--strict"]) == 0
    assert "structure/" not in capsys.readouterr().out


def test_the_same_markdown_as_a_document_gets_the_structure_rules(tmp_path, monkeypatch, capsys):
    """A poster has no [[CAPTION:]] markers, which the example project's structure rules ask of a document."""
    import shutil

    copy = tmp_path / "not-a-poster.md"
    shutil.copy(EXAMPLE_POSTERS / "poster.md", copy)
    monkeypatch.chdir(EXAMPLE_POSTERS.parent)
    main(["lint", str(copy), "--engine", "builtin", "--config", "py-doc.yml"])
    assert "structure/diagram-missing-caption" in capsys.readouterr().out


def test_build_lint_reads_the_posters_too(tmp_path, drawn, documents, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "## A\n\nWe do this in order to save power.\n")
    (tmp_path / "py-doc.yml").write_text("posters:\n  wall: {source: poster.md}\n", encoding="utf-8")
    assert main(["build", "--strict"]) == 1
    out = capsys.readouterr()
    assert "poster.md" in out.out and "DOC002" in out.out  # 'in order to' is a wordy phrase
    assert not (tmp_path / "build" / "wall.html").exists()


def test_one_font_file_for_several_weights_is_embedded_once():
    from py_doc.poster_fonts import merge_weights

    rule = "/* latin */\n@font-face {{\n  font-family: 'Mono';\n  font-weight: {w};\n  src: url(https://f.example/mono.woff2) format('woff2');\n}}\n"
    css = merge_weights(rule.format(w=500) + rule.format(w=600) + rule.format(w=700).replace("mono.woff2", "mono-bold.woff2"))
    assert css.count("@font-face") == 2 and css.count("mono.woff2") == 1
    assert "font-weight:500 600;" in css and "font-weight:700;" in css
    assert merge_weights("@font-face { font-weight: bold; src: url(https://f.example/a.woff2); }").count("bold") == 1  # left alone
