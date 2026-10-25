"""The shared drawing pieces of the native poster blocks (poster_svg) and the block registry."""

from __future__ import annotations

import json
import math
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from py_doc import poster_blocks, poster_svg
from py_doc.poster_blocks import BLOCKS, Ctx, Fragment, block_fragment, parse_opts
from py_doc.poster_svg import Band, Linear, Log10, Node, arc, extent, nice, number, polar, sector, spread, tidy, wrap
from py_doc.poster_themes import Theme

ROOT = Path(__file__).parent.parent
SNAPSHOTS = Path(__file__).parent / "fixtures" / "poster_blocks" / "snapshots.json"


def ctx(tmp_path=ROOT):
    return Ctx(tmp_path, lambda: None, Theme(), render=lambda text, c: text, where="test.md")


# --- numbers and scales ---


@pytest.mark.parametrize(
    "value, expected", [(0, 0.0), (0.7, 1.0), (1, 1.0), (1.2, 2.0), (2.1, 2.5), (3, 5.0), (7, 10.0), (1440, 2000.0)]
)
def test_nice_rounds_up_to_1_2_25_or_5_times_a_power_of_ten(value, expected):
    assert nice(value) == pytest.approx(expected)


def test_number_separates_thousands_and_drops_trailing_zeros():
    assert (number(12000), number(2.50), number(-3.0), number(0.125)) == ("12,000", "2.5", "-3", "0.125")


def test_extent_starts_at_zero_or_a_round_number_below_a_negative_value():
    assert extent([3, 7]) == (0.0, 10.0)
    assert extent([-3, 4]) == (-5.0, 5.0)
    assert extent([1, 2], low=0.5, high=None) == (0.5, 2.0)
    assert extent([0]) == (0.0, 1.0)  # nothing above zero still has an axis


def test_a_linear_scale_maps_and_can_grow_upwards():
    up = Linear(0, 100, 300, 100)  # a value axis: 0 at the bottom
    assert (up(0), up(50), up(100)) == (300, 200, 100)
    assert up.ticks(25) == [0, 25, 50, 75, 100]


def test_a_log_scale_puts_each_power_of_ten_the_same_distance_apart():
    scale = Log10(1e-9, 1e-1, 0, 800)  # 1 ns to 100 ms
    assert scale(1e-9) == pytest.approx(0)
    assert scale(1e-5) == pytest.approx(400)
    assert scale.ticks() == pytest.approx([10.0**k for k in range(-9, 0)])
    with pytest.raises(ValueError):
        Log10(0, 10, 0, 1)


def test_bands_share_the_width_and_centre_their_marks():
    band = Band(4, 0, 400)
    assert (band.width, band.at(1), band.centre(1)) == (100, 100, 150)
    assert band.mark(1) == pytest.approx(115)


# --- polar paths ---


def test_angles_start_at_the_top_and_go_clockwise():
    assert polar(0, 0, 10, 0) == pytest.approx((0, -10))
    assert polar(0, 0, 10, 90) == pytest.approx((10, 0))
    assert polar(0, 0, 10, 180) == pytest.approx((0, 10))


def test_an_arc_takes_the_long_way_only_past_half_a_turn():
    assert " 0 0 1 " in arc(0, 0, 10, 0, 90)
    assert " 0 1 1 " in arc(0, 0, 10, 0, 270)


def test_sectors_are_closed_slices_rings_and_whole_circles():
    assert sector(50, 50, 0, 40, 0, 90).endswith("L50.00,50.00 Z")
    assert sector(50, 50, 20, 40, 0, 90).count(" A") == 2
    whole = sector(50, 50, 20, 40, 0, 360)
    assert whole.count("M") == 2 and whole.count(" Z") == 2  # outer and inner circle, for evenodd


# --- text ---


def test_wrap_breaks_between_words_and_keeps_a_long_word_whole():
    assert wrap("one two three four", 13 * 0.55 * 9, 13) == ["one two", "three", "four"]
    assert wrap("supercalifragilistic", 10, 13) == ["supercalifragilistic"]
    assert wrap("", 100, 13) == [""]


def test_spread_moves_labels_apart_in_order_and_within_bounds():
    assert spread([10, 11, 12], 10) == [10, 20, 30]
    assert spread([12, 10, 11], 10) == [30, 10, 20]  # the order of the positions is kept
    placed = spread([95, 96, 97], 10, low=0, high=100)
    assert placed == [80, 90, 100]
    assert spread([], 10) == []


def test_label_escapes_its_text():
    assert "&lt;b&gt;" in poster_svg.label(0, 0, "<b>")


# --- tree layout ---


def test_a_tidy_tree_centres_parents_and_keeps_siblings_apart():
    root = Node("root", [Node("a", [Node("a1"), Node("a2"), Node("a3")]), Node("b"), Node("c", [Node("c1")])])
    width, depth = tidy(root)
    nodes = {n.label: n for n in root.walk()}
    assert depth == 2
    assert min(n.x for n in nodes.values()) == 0
    assert nodes["a"].x == pytest.approx((nodes["a1"].x + nodes["a3"].x) / 2)
    assert nodes["root"].x == pytest.approx((nodes["a"].x + nodes["c"].x) / 2)
    for level in range(depth + 1):
        xs = sorted(n.x for n in nodes.values() if n.depth == level)
        assert all(b - a >= 1 - 1e-9 for a, b in zip(xs, xs[1:])), f"depth {level}: {xs}"
    assert width == pytest.approx(max(n.x for n in nodes.values()))


def test_a_single_node_tree():
    assert tidy(Node("only")) == (0.0, 0)


# --- the block registry ---


def test_every_native_block_is_registered_and_in_the_posters_chapter():
    chapter = (ROOT / "docs" / "guide" / "12_posters.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([a-z-]+)` \|", chapter, re.M))
    expected = {"cards", "lcd", "segments", "flow", "lanes", "figure", "timeline", "chart", "qr", "barcode"}
    expected |= {"steps", "gallery", "progress", "checklist", "compare", "people", "highlight"}
    assert expected <= set(BLOCKS)
    missing = set(BLOCKS) - documented
    assert not missing, f"blocks not in the Poster blocks table of 12_posters.md: {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(BLOCKS))
def test_every_block_has_syntax_and_a_working_example(name):
    found = BLOCKS[name]
    assert found.syntax
    if found.example is None:  # gallery: its example needs picture files
        return
    drawn = block_fragment(name, {}, found.example, ctx())
    assert isinstance(drawn, Fragment) and drawn.html


@pytest.mark.parametrize("name, code", [("chart", "A | 1\nB | 2"), ("qr", "https://example.com"), ("barcode", "SN-1")])
def test_an_all_svg_block_can_be_written_as_a_file_of_its_own(name, code):
    drawn = block_fragment(name, {}, code, ctx())
    assert drawn.svg and drawn.svg in drawn.html
    file = poster_svg.standalone(drawn.svg, Theme(), background="#ffffff")
    root = ET.fromstring(file.split("\n", 1)[1])
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("color") == Theme().colours["text"]


def test_an_html_block_has_no_picture_of_its_own():
    assert block_fragment("cards", {}, "A | text", ctx()).svg is None


def test_a_fence_that_is_not_a_block_is_left_alone():
    assert block_fragment("python", {}, "print(1)", ctx()) is None
    assert poster_blocks.block_html("python", {}, "print(1)", ctx()) is None


# --- snapshots: the refactor onto poster_svg did not change what a block draws ---

CASES = {
    "chart-column": ("chart", 'title="Messages a day" unit=" msg"', "series: 2.0, 2.1\nOffice | 1440 | 610\nWarehouse | 1440 | 980"),
    "chart-bar": ("chart", 'type=bar values=last axis="Charge"', "Asleep | 116\nMeasure | 300\nSend | -1200"),
    "chart-line": ("chart", 'type=line min=2.2 max=3.2 step=0.2 values=last area=yes height=240 colours=blue axis="Volts"', "Year 0 | 3.05\nYear 1 | 2.96\nYear 5 | 2.62"),
    "chart-line-series": ("chart", "type=line dashed=Target markers=no", "series: Real, Target\nQ1 | 4 | 5\nQ2 | 6 | 5\nQ3 | -1 | 5"),
    "segments": ("segments", "", "title: One minute (not to scale)\n6 | Asleep, 58 s | 2 µA | navy\n2 | Send, 1 s | 12 mA | amber\nA note."),
    "timeline": ("timeline", "", "Jan 2026 | Pilot | 200 nodes | navy\nApr 2026 | Firmware 2.1"),
    "timeline-vertical": ("timeline", "vertical", "2024 | One\n2025 | Two | detail | green"),
    "progress": ("progress", 'unit=" nodes"', "Joined | 48 | 50\nLabelled | 50 | 50 | teal"),
    "progress-ceiling": ("progress", "better=lower show=percent", "Returns | 3 | 2\nFaults | 1 | 4"),
}  # fmt: skip


def _draw_cases():
    return {
        name: poster_blocks.block_html(lang, parse_opts(info), code, ctx())
        for name, (lang, info, code) in CASES.items()
    }


def test_blocks_draw_what_their_snapshots_hold():
    drawn = _draw_cases()
    if os.environ.get("PY_DOC_UPDATE_SNAPSHOTS"):
        SNAPSHOTS.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOTS.write_text(json.dumps(drawn, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    expected = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))
    assert drawn.keys() == expected.keys()
    for name in drawn:
        assert drawn[name] == expected[name], f"{name} changed; PY_DOC_UPDATE_SNAPSHOTS=1 rewrites the snapshots"


def test_snapshot_charts_have_no_nan():
    assert not any(math.isnan(float(x)) for x in re.findall(r'="(-?[\d.]+)"', "".join(_draw_cases().values())))
