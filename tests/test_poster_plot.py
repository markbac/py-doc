"""``plot``: presets expanded into Vega-Lite or Vega, for posters and documents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from py_doc import poster_blocks
from py_doc.diagrams import render
from py_doc.poster_blocks import Ctx, PosterError, block_html, parse_opts
from py_doc.poster_plot import TYPES, PlotError, expand
from py_doc.poster_themes import Theme

EXAMPLES = {
    "pareto": "A | 30\nB | 50\nC | 20",
    "spc": "1 | 0.1\n2 | 0.2\n3 | 0.15\n4 | 0.9",
    "boxplot": "A | 1 2 3 4 5\nB | 2 3 4",
    "violin": "A | 1 2 3 4 5",
    "scatter": "P | 1 | 2 | 3 | g\nQ | 2 | 4",
    "function": "curve: Line | 2 * x + 1",
    "heatmap": "| a | b\nX | 1 | 2\nY | 3 | 4",
    "polar": "N | 3\nS | 5",
    "slope": "| 2020 | 2025\nA | 1 | 2\nB | 3 | 1",
    "parallel": "| a | b\nX | 1 | 2\nY | 3 | 1",
    "fan": "history: 1 | 10\nforecast: 2 | 11 | 10 | 12 | 9 | 13 | 8 | 14",
    "sunburst": "G / A | 1\nG / B | 2\nH | 3",
    "icicle": "G / A | 1\nH | 3",
    "pack": "G / A | 1\nH | 3",
}


def spec(kind, code=None, **opts):
    fence, text = expand(EXAMPLES[kind] if code is None else code, {"type": kind, **opts})
    return fence, json.loads(text)


@pytest.mark.parametrize("kind", TYPES)
def test_every_preset_expands_to_a_spec(kind):
    fence, out = spec(kind)
    assert fence == ("vega" if kind in ("sunburst", "icicle", "pack") else "vega-lite")
    assert out["$schema"].endswith("vega/v5.json" if fence == "vega" else "vega-lite/v5.json")


def test_a_pareto_sorts_its_causes_and_adds_their_running_share():
    _, out = spec("pareto")
    values = out["data"]["values"]
    assert [v["cause"] for v in values] == ["B", "A", "C"]
    assert [round(v["share"], 2) for v in values] == [0.5, 0.8, 1.0]
    assert out["resolve"] == {"scale": {"y": "independent"}}


def test_a_control_chart_marks_points_outside_its_limits():
    _, out = spec("spc", "1 | 0\n2 | 0\n3 | 0\n4 | 10", ucl="5", lcl="-5")
    values = next(layer for layer in out["layer"] if layer["mark"]["type"] == "line")
    assert values  # the line of values is there
    assert [d["out"] for d in out["data"]["values"]] == ["inside", "inside", "inside", "outside"]


def test_scatter_axes_can_be_log_and_inverted_and_points_labelled():
    _, out = spec("scatter", xlog="yes", yinvert="yes", labels="yes")
    enc = out["layer"][0]["encoding"]
    assert enc["x"]["scale"] == {"type": "log"} and enc["y"]["scale"]["reverse"] is True
    assert out["layer"][1]["mark"]["type"] == "text" and "size" in enc and "color" in enc


def test_a_function_samples_its_expression_over_its_range():
    _, out = spec("function", "curve: Square | x * x\nrule: 2 | Two", **{"from": "-1", "to": "3"})
    assert out["data"]["sequence"]["start"] == -1 and out["transform"] == [
        {"calculate": "datum.x * datum.x", "as": "c0"}
    ]
    assert any(layer["mark"]["type"] == "rule" for layer in out["layer"])
    _, normal = spec("function", "", preset="normal")
    assert sum(layer["mark"]["type"] == "area" for layer in normal["layer"]) == 3


def test_a_risk_matrix_is_five_by_five_with_its_labels():
    _, out = spec("heatmap", "4 | 5 | R1", preset="risk")
    assert len(out["data"]["values"]) == 25
    assert next(d for d in out["data"]["values"] if d["row"] == "4" and d["col"] == "5")["label"] == "R1"


def test_hierarchies_become_stratified_trees():
    _, out = spec("sunburst", "A / B | 1\nA / C | 2\nD | 3")
    data = out["data"][0]
    assert {d["id"]: d["parent"] for d in data["values"]} == {
        "root": None,
        "A": "root",
        "A/B": "A",
        "A/C": "A",
        "D": "root",
    }
    assert [t["type"] for t in data["transform"]] == ["stratify", "partition"]
    assert out["scales"][0]["range"] == "category"  # the theme's colours, through its Vega config


@pytest.mark.parametrize(
    "kind, code, message",
    [
        ("pareto", "A", "needs 'cause \\| count' lines"),
        ("spc", "1 | 2", "at least two"),
        ("scatter", "P | 1", "'label \\| x \\| y'"),
        ("function", "curve: A", "'curve: label \\| expression in x'"),
        ("function", "line: x", "starts curve:, area: or rule:"),
        ("heatmap", "X | 1", "starts with a header"),
        ("fan", "history: 1 | 2", "needs history: and forecast: lines"),
        ("boxplot", "A | many", "is not a number"),
    ],
)
def test_plot_mistakes(kind, code, message):
    with pytest.raises(PlotError, match=message):
        expand(code, {"type": kind})


def test_an_unknown_plot_type_is_an_error():
    with pytest.raises(PlotError, match="plot type must be one of"):
        expand("A | 1", {"type": "pie"})


# --- in a poster and in a document ---


def test_a_poster_plot_is_drawn_as_vega_lite_in_the_poster_theme(monkeypatch, tmp_path):
    drawn = []

    def draw(runtime, renderer, text, kind, landscape, source_dir, info=None):
        drawn.append((renderer.name, json.loads(text)))
        picture = tmp_path / "plot.svg"
        picture.write_text("<svg/>", encoding="utf-8")
        return picture

    monkeypatch.setattr(poster_blocks, "draw_cached", draw)
    ctx = Ctx(tmp_path, lambda: None, Theme(), render=lambda text, c: text, where="poster.md")
    html = block_html("plot", parse_opts("type=pareto"), EXAMPLES["pareto"], ctx)
    assert html.startswith("<img") and drawn[0][0] == "vega-lite"
    assert drawn[0][1]["config"]["font"] == Theme().fonts["body"]
    with pytest.raises(PosterError, match="poster.md: plot type must be one of"):
        block_html("plot", parse_opts("type=pie"), "A | 1", ctx)


def test_a_document_plot_is_drawn_as_vega_in_the_blocks_theme(monkeypatch, tmp_path):
    drawn = []

    def draw(runtime, renderer, text, kind, landscape, source_dir, info=None):
        drawn.append((renderer.name, kind, json.loads(text)))
        picture = tmp_path / f"plot.{kind}"
        picture.write_bytes(b"\x89PNG\r\n\x1a\n")
        return picture

    monkeypatch.setattr(render, "draw_cached", draw)
    text = "```plot type=sunburst\nA / B | 1\nC | 2\n```\n"
    rendered = render.render_parts([(tmp_path / "doc.md", text)], "docx", lambda: None)
    assert drawn[0][:2] == ("vega", "png") and "config" in drawn[0][2]
    assert "![plot diagram](diagrams/plot.png)" in rendered.markdown
    with pytest.raises(render.DiagramError, match=r"doc\.md:1: plot: plot type"):
        render.render_parts([(Path(tmp_path / "doc.md"), "```plot type=pie\nA | 1\n```\n")], "docx", lambda: None)
