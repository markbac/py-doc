"""The diagrams the tool container draws on a poster: in the poster's theme, and at their own size."""

from __future__ import annotations

import json

from py_doc.diagrams import BY_FENCE
from py_doc.poster_blocks import (
    mermaid_init,
    series_colours,
    sized_svg,
    vega_config,
    with_plantuml_skin,
    with_vega_config,
)
from py_doc.poster_themes import Theme


def config(theme=None):
    return json.loads(mermaid_init(theme or Theme()).split("config: ", 1)[1].split("\n---", 1)[0])


def test_mermaid_charts_maps_and_timelines_get_the_theme_colour_scales():
    theme = Theme()
    variables = config(theme)["themeVariables"]
    scale = series_colours(theme)
    assert variables["pie1"] == scale[0] and variables["cScale0"] == scale[0] and variables["git0"] == scale[0]
    assert {f"pie{n}" for n in range(1, 13)} <= set(variables)
    assert variables["xyChart"]["plotColorPalette"].split(", ") == scale
    assert variables["quadrantPointFill"] == theme.colours["accent"]


def test_series_colours_start_with_the_theme_roles_and_repeat_no_colour():
    theme = Theme()
    scale = series_colours(theme)
    assert scale[:3] == [theme.colours["secondary"], theme.colours["primary"], theme.colours["good"]]
    assert theme.colours["accent"] not in scale  # too like secondary to tell two series apart
    assert len(scale) == len(set(scale))
    assert theme.colours["muted"] not in scale[:5]


def test_a_vega_lite_spec_gets_the_poster_config_under_its_own():
    spec = {"mark": "bar", "config": {"axis": {"labelColor": "red"}}}
    out = json.loads(with_vega_config(json.dumps(spec), Theme()))
    assert out["mark"] == "bar"
    assert out["config"]["axis"]["labelColor"] == "red"  # the spec's own value wins
    assert out["config"]["axis"]["gridColor"] == Theme().colours["border"]  # the rest comes from the theme
    assert out["config"]["range"]["category"] == series_colours(Theme())


def test_a_vega_spec_that_is_not_a_json_object_is_left_alone():
    assert with_vega_config("not json", Theme()) == "not json"
    assert with_vega_config("[1, 2]", Theme()) == "[1, 2]"


def test_vega_config_uses_the_theme_font():
    assert vega_config(Theme())["font"] == Theme().fonts["body"]


def test_plantuml_gets_the_skin_after_its_start_line_unless_it_has_a_theme():
    code = "@startuml\nA -> B\n@enduml"
    out = with_plantuml_skin(code, Theme())
    lines = out.splitlines()
    assert lines[0] == "@startuml" and lines[1].startswith("skinparam ") and lines[-2:] == ["A -> B", "@enduml"]
    assert f"skinparam ArrowColor {Theme().colours['primary']}" in out
    assert "skinparam defaultFontName Source Serif 4" in out
    themed = "@startuml\n!theme cerulean\nA -> B\n@enduml"
    assert with_plantuml_skin(themed, Theme()) == themed
    assert with_plantuml_skin("A -> B", Theme()) == "A -> B"  # no start line: nothing to add to


def test_an_svg_sized_in_percent_gets_the_size_of_its_view_box():
    svg = b'<svg id="x" width="100%" viewBox="-0.5 0 135.1 189.2" style="max-width: 1200px"><g/></svg>'
    out = sized_svg(svg)
    assert out.startswith(b'<svg width="135.1" height="189.2" id="x" viewBox="-0.5 0 135.1 189.2"')
    assert out.endswith(b"<g/></svg>")


def test_an_svg_with_no_width_gets_one_and_one_with_a_size_is_kept():
    assert b'width="700" height="500"' in sized_svg(b'<svg style="a" viewBox="0 0 700 500"></svg>')
    kept = b'<svg width="600" viewBox="0 0 600 400"></svg>'
    assert sized_svg(kept) == kept
    assert sized_svg(b"<svg><g/></svg>") == b"<svg><g/></svg>"  # no viewBox: nothing to size it by


def test_rackdiag_is_a_diagram_fence():
    assert BY_FENCE["rackdiag"].name == "rackdiag"
