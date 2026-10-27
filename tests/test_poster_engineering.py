"""The engineering blocks of posters: bowtie, fault-tree, gsn, kmap, plc-ladder, structogram, n2, idef0 and vsm."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from py_doc.diagrams.blocks import SVG_BLOCK, prepare, theme_for
from py_doc.poster_blocks import BLOCKS, Ctx, PosterError, block_fragment, parse_opts
from py_doc.poster_engineering import _runs, expression, minimal_cover
from py_doc.poster_themes import Theme

ENGINEERING = ("bowtie", "fault-tree", "gsn", "kmap", "plc-ladder", "structogram", "n2", "idef0", "vsm")


def ctx():
    return Ctx(Path("."), lambda: None, Theme(), render=lambda text, c: text, where="test.md")


def draw(lang, code, info=""):
    return block_fragment(lang, parse_opts(info), code, ctx()).svg


def texts(svg):
    return re.findall(r">([^<>]+)</text>", svg)


@pytest.mark.parametrize("name", ENGINEERING)
def test_every_engineering_block_draws_its_example_as_svg(name):
    svg = draw(name, BLOCKS[name].example, BLOCKS[name].info)
    assert svg.startswith('<svg class="chart"')
    ET.fromstring(svg)  # well formed


@pytest.mark.parametrize("name", ENGINEERING)
def test_every_engineering_block_is_an_svg_picture_in_a_document(name, tmp_path):
    """Word, PowerPoint, PDF and sites draw them through the SVG path, with no photograph of HTML."""
    renderer, body = prepare(name, BLOCKS[name].info, BLOCKS[name].example, tmp_path, theme_for(None, tmp_path))
    assert renderer is SVG_BLOCK and body.startswith("<?xml")


# --- kmap ------------------------------------------------------------------------------------------


def test_a_kmap_finds_the_minimal_sum_of_products():
    assert expression(minimal_cover({0, 2, 5, 7, 8, 10, 13, 15}, {6}, 4), "ABCD") == "B′D′ + BD"
    assert expression(minimal_cover({1, 3, 5, 7}, set(), 3), "ABC") == "C"
    assert expression(minimal_cover({0, 1, 2, 3}, set(), 2), "AB") == "1"
    assert expression(minimal_cover(set(), set(), 2), "AB") == "0"
    # a don't-care is used when it makes a loop larger, and never needs covering on its own
    assert expression(minimal_cover({4, 5, 6}, {7}, 3), "ABC") == "A"


def test_a_kmap_loop_wraps_round_the_edges():
    assert _runs({0, 3}, 4) == [(3, 2, True)]
    assert _runs({1, 2}, 4) == [(1, 2, False)]
    assert _runs({0, 1, 2, 3}, 4) == [(0, 4, False)]
    svg = draw("kmap", "vars: A B C D\nones: 0 2 8 10")
    loops = re.findall(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="[\d.]+" height="[\d.]+" rx="14"', svg)
    assert len(loops) == 4  # the four corners are one loop, in four pieces
    assert ">F = B′D′<" in svg


def test_a_kmap_says_what_is_wrong():
    with pytest.raises(PosterError, match="2, 3 or 4 vars"):
        draw("kmap", "vars: A B C D E\nones: 1")
    with pytest.raises(PosterError, match="16 is not a minterm of 4 variables"):
        draw("kmap", "vars: A B C D\nones: 16")
    with pytest.raises(PosterError, match="both a one and a don't-care"):
        draw("kmap", "vars: A B\nones: 1\ndont: 1")
    assert 'rx="14"' not in draw("kmap", "vars: A B\nones: 1 3", "loops=no")


# --- fault-tree ------------------------------------------------------------------------------------


def test_a_fault_tree_draws_its_gates_and_leaf_symbols():
    svg = draw("fault-tree", BLOCKS["fault-tree"].example)
    assert svg.count("<circle") == 3  # three basic events
    assert "Gateway down" in texts(svg) and "1e-3" in texts(svg)
    two_of_three = draw("fault-tree", "2/3: Lost\n  basic: A\n  basic: B\n  basic: C")
    assert "2/3" in texts(two_of_three)


@pytest.mark.parametrize(
    "code, message",
    [
        ("or: Top\n  basic: A\n    basic: B", "a basic event has no events under it"),
        ("Top\n  basic: A", "give the gate of 'Top'"),
        ("and: Top", "needs the events under it"),
        ("2/3: Top\n  basic: A\n  basic: B", "a 2/3 gate needs 3 events"),
        ("or: Top\n  basic: A\nor: Second", "one top event"),
        ("nand: Top\n  basic: A", "starts 'nand:'"),
    ],
)
def test_a_fault_tree_says_what_is_wrong(code, message):
    with pytest.raises(PosterError, match=re.escape(message)):
        draw("fault-tree", code)


def test_an_inhibit_gate_shows_its_condition():
    assert "Door open" in texts(draw("fault-tree", "inhibit: Fire spreads | | Door open\n  basic: Fire"))


# --- gsn ----------------------------------------------------------------------------------------------


def test_gsn_puts_a_context_beside_its_goal_and_a_solution_under_it():
    svg = draw("gsn", "goal G1: Safe\n  context C1: Indoors\n  solution Sn1: Test report")
    goal = re.search(r'<rect x="([\d.]+)" y="([\d.]+)"', svg)
    context = re.search(r'<rect x="([\d.]+)" y="([\d.]+)" width="[\d.]+" height="64" rx=', svg)
    assert goal[2] == context[2] and float(context[1]) > float(goal[1])  # same row, to the right
    solution = re.search(r'<circle cx="[\d.]+" cy="([\d.]+)"', svg)
    assert float(solution[1]) > float(goal[2]) + 64
    assert "G1" in texts(svg) and "Sn1" in texts(svg)


def test_gsn_marks_an_undeveloped_goal_and_refuses_an_unknown_kind():
    svg = draw("gsn", "goal G1: Safe\n  goal G2: Later | undeveloped")
    assert re.search(r'fill="#fff" stroke=', svg)  # the hollow diamond
    with pytest.raises(PosterError, match="kind ID: text"):
        draw("gsn", "claim C: It works")
    with pytest.raises(PosterError, match="supports nothing"):
        draw("gsn", "goal G1: Safe\n  solution S: Report\n    goal G2: More")


# --- bowtie ------------------------------------------------------------------------------------------


def test_a_bowtie_draws_threats_barriers_and_consequences():
    words = texts(draw("bowtie", BLOCKS["bowtie"].example))
    assert {"Overcharge", "Crush", "Fire", "Toxic smoke", "Lithium cell"} <= set(words)
    assert "monitor" in words and "Thermal" in words  # barriers and the top event, wrapped
    with pytest.raises(PosterError, match="needs a top: event"):
        draw("bowtie", "threat: A | B")
    with pytest.raises(PosterError, match="starts hazard:"):
        draw("bowtie", "top: X\nrisk: Y")


def test_a_bowtie_s_threats_can_be_read_in_the_print_theme():
    # the print theme's secondary is a light box colour, which white text cannot be read on
    print_theme = theme_for("print", Path("."))
    ctx = Ctx(Path("."), lambda: None, print_theme, render=lambda text, c: text, where="test.md")
    svg = block_fragment("bowtie", {}, BLOCKS["bowtie"].example, ctx).svg
    assert print_theme.colours["secondary"] not in svg


# --- plc-ladder -----------------------------------------------------------------------------------


def test_a_ladder_draws_its_rungs_branches_and_elements():
    svg = draw("plc-ladder", BLOCKS["plc-ladder"].example)
    assert {"Start", "Stop", "Pump", "T1", "PT=30s", "TON", "R"} <= set(texts(svg))
    assert re.search(r'<path d="M[\d.]+,\d+ L[\d.]+,\d+ L[\d.]+,\d+ L[\d.]+,\d+" fill="none"', svg)  # the branch


def test_a_ladder_says_what_is_wrong():
    with pytest.raises(PosterError, match="starts NO, NC"):
        draw("plc-ladder", "XIC Start | OTE Motor")
    with pytest.raises(PosterError, match="more elements than fit"):
        draw("plc-ladder", " | ".join(["NO A"] * 8) + " | COIL B")
    with pytest.raises(PosterError, match="more elements than its rung has inputs"):
        draw("plc-ladder", "NO A | COIL B\nbranch: NO C | NO D")
    with pytest.raises(PosterError, match="one line of elements"):
        draw("plc-ladder", "NO A | COIL B\nNO C | COIL D")


# --- structogram ---------------------------------------------------------------------------------


def test_a_structogram_draws_decisions_loops_and_cases():
    svg = draw("structogram", BLOCKS["structogram"].example)
    assert {"yes", "no", "Send it", "Count the skip"} <= set(texts(svg))
    case = draw("structogram", "case Mode\n  when Normal\n    Send\n  when Test\n    Log\n  else\n    Stop")
    assert {"Normal", "Test", "else"} <= set(texts(case))
    repeat = draw("structogram", "repeat\n  Try to join\nuntil Joined")
    assert "until Joined" in texts(repeat)


def test_a_structogram_says_what_is_wrong():
    with pytest.raises(PosterError, match="an else follows an if"):
        draw("structogram", "Send\nelse\n  Log")
    with pytest.raises(PosterError, match="needs an until"):
        draw("structogram", "repeat\n  Try")
    with pytest.raises(PosterError, match="only if, else"):
        draw("structogram", "Send\n  Log")


# --- n2 -----------------------------------------------------------------------------------------------


def test_an_n2_chart_puts_items_on_the_diagonal_and_shades_feedback():
    svg = draw("n2", BLOCKS["n2"].example)
    callout = Theme().colours["callout"]
    assert svg.count(f'fill="{callout}"') == 1  # Cloud -> Controller is the one feedback
    assert "Sensor" in texts(svg) and "MQTT publish" in texts(svg)
    with pytest.raises(PosterError, match="'Gateway' is not one of the items"):
        draw("n2", "items: A, B\nA -> Gateway | x")
    assert {"A", "B"} <= set(texts(draw("n2", "A -> B | data")))  # the items from the lines


# --- idef0 -------------------------------------------------------------------------------------------


def test_idef0_joins_an_output_to_a_later_box_once():
    svg = draw("idef0", BLOCKS["idef0"].example)
    assert texts(svg).count("Reading") == 1  # one arrow from A1 to A2, not an output and an input
    assert {"Air", "Sample interval", "Sensor", "Message", "A1", "A2"} <= set(texts(svg))
    with pytest.raises(PosterError, match="at most 5 boxes"):
        draw("idef0", "\n".join(f"box: A{n} Step" for n in range(1, 7)))
    with pytest.raises(PosterError, match="under a box"):
        draw("idef0", "in: Air")


# --- vsm ---------------------------------------------------------------------------------------------


def test_a_value_stream_map_adds_up_its_lead_and_processing_times():
    svg = draw("vsm", BLOCKS["vsm"].example)
    assert "Lead time 8 days  ·  Processing time 90 s" in texts(svg)
    mixed = draw("vsm", "inventory: 2 days\nprocess: A | C/T 4 h")
    assert "Lead time 2 days  ·  Processing time 4 h" in texts(mixed)
    with pytest.raises(PosterError, match="at least one process"):
        draw("vsm", "inventory: 2 days")
