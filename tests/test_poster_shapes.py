"""The shape blocks of posters: pyramid, cone, funnel, stack, target, cutaway, sizes, vessels, memory, tape, ring,
cycle, balance and iceberg."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from py_doc.poster_blocks import BLOCKS, Ctx, PosterError, block_fragment, parse_opts
from py_doc.poster_themes import Theme

SHAPES = (
    "pyramid", "cone", "funnel", "stack", "target", "onion", "cutaway", "sizes", "vessels",
    "memory", "tape", "ring", "cycle", "balance", "iceberg",
)  # fmt: skip


def ctx():
    return Ctx(Path("."), lambda: None, Theme(), render=lambda text, c: text, where="test.md")


def draw(lang, code, info=""):
    return block_fragment(lang, parse_opts(info), code, ctx())


@pytest.mark.parametrize("name", SHAPES)
def test_every_shape_draws_its_example_as_svg(name):
    assert draw(name, BLOCKS[name].example, BLOCKS[name].info).svg.startswith('<svg class="chart"')


def test_a_pyramid_points_up_and_a_cone_down():
    up = draw("pyramid", "Top | 5 %\nBase | 95 %").svg
    down = draw("cone", "Top | 95 %\nTip | 5 %").svg
    first_up = re.search(r'<path d="M([\d.]+),\d+ L([\d.]+),', up)
    first_down = re.search(r'<path d="M([\d.]+),\d+ L([\d.]+),', down)
    assert float(first_up[2]) - float(first_up[1]) == 0  # the point, at the top
    assert float(first_down[2]) - float(first_down[1]) > 300  # the wide end, at the top


def test_a_narrow_tier_puts_its_name_beside_it():
    svg = draw("pyramid", "Apex | 1 %\nB | 4 %\nC | 10 %\nD | 25 %\nBase | 60 %").svg
    assert ">Apex 1 %<" in svg  # the top tier is too narrow for its name


def test_a_name_too_long_for_its_tier_goes_beside_it():
    # the top tier of four is 42 pixels wide half way down, too narrow for this name though wider than a short one
    svg = draw("pyramid", "End-to-end | 5 %\nB | 15 %\nC | 25 %\nD | 55 %").svg
    assert ">End-to-end 5 %<" in svg


def test_a_funnel_shows_what_each_stage_keeps():
    svg = draw("funnel", "All | 1000\nHalf | 500\nTenth | 50").svg
    assert ">50 % kept<" in svg
    assert ">Tenth 50, 10 % kept<" in svg  # a stage too narrow for its name has it beside, with the share
    assert "kept" not in draw("funnel", "All | 1000\nHalf | 500", "percent=no").svg


def test_a_stack_side_must_name_its_layers():
    assert ">Secured<" in draw("stack", "A | 1\nB | 2\nside: Secured | 1-2 | red").svg
    with pytest.raises(PosterError, match="names layers 2-5 of 2"):
        draw("stack", "A\nB\nside: Wide | 2-5")


def test_cutaway_shells_grow_outwards_and_a_column_has_its_edges():
    with pytest.raises(PosterError, match="from the core outwards"):
        draw("cutaway", "Outer | 1\nInner | 0.5")
    svg = draw("cutaway", "0 | 12 | Troposphere\n12 | 50 | Stratosphere", 'type=column unit=" km"').svg
    assert ">50 km<" in svg and ">Troposphere<" in svg
    with pytest.raises(PosterError, match="sphere or column"):
        draw("cutaway", "x", "type=cube")


def test_sizes_are_drawn_to_one_scale():
    svg = draw("sizes", "Big | 10\nSmall | 5").svg
    radii = [float(r) for r in re.findall(r'<circle cx="[\d.]+" cy="[\d.]+" r="([\d.]+)"', svg)]
    assert radii[0] == pytest.approx(2 * radii[1])
    nested = draw("sizes", "Big | 10\nSmall | 5", "nested=yes").svg
    assert len(re.findall(r'<circle[^>]*fill="none" stroke="[^"]+" stroke-width="3"', nested)) == 2


def test_vessels_fill_in_proportion_and_name_their_layers():
    svg = draw("vessels", "A | 30 ml Espresso (amber) + 30 ml Milk (#f3e3c3)\nB | 60 ml Espresso (amber)").svg
    assert ">30 ml Espresso<" in svg and ">60 ml<" in svg
    with pytest.raises(PosterError, match="amount unit label"):
        draw("vessels", "A | some espresso")


def test_a_memory_map_puts_the_highest_address_at_the_top_and_shows_gaps():
    svg = draw("memory", "0x0800_0000 | 32 KB | Boot\n0x2000_0000 | 8 KB | Stack | amber | down").svg
    assert svg.index(">Stack<") < svg.index(">Boot<")
    assert ">0x0800_7FFF<" in svg and "unused" in svg and ">grows down<" in svg
    with pytest.raises(PosterError, match="not a size"):
        draw("memory", "0x0 | lots | X")


def test_a_tape_brackets_its_groups():
    svg = draw("tape", "cells: A U G\n1-3 | Met").svg
    assert svg.count(">A<") == 1 and ">Met<" in svg
    with pytest.raises(PosterError, match="cells 2-9 of 3"):
        draw("tape", "cells: A U G\n2-9 | Long")


def test_a_ring_fill_may_wrap_round():
    svg = draw("ring", "fill: 14-1 | Wrapped | red", "cells=16").svg
    assert svg.count('fill="#a3322b"') >= 4  # cells 14, 15, 0 and 1
    with pytest.raises(PosterError, match="starts fill: or pointer:"):
        draw("ring", "head: 1")


def test_a_cycle_has_three_to_eight_stages_joined_by_arrows():
    svg = draw("cycle", "A\nB\nC").svg
    assert svg.count('marker-end="url(#cyc-arrow)"') == 3
    with pytest.raises(PosterError, match="at least 3 lines"):
        draw("cycle", "A\nB")


def test_a_balance_tips_to_the_heavier_side():
    svg = draw("balance", "left: Light | 1\nright: Heavy | 9").svg
    x1, y1, x2, y2 = (
        float(v)
        for v in re.search(
            r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke="currentColor" stroke-width="6"', svg
        ).groups()
    )
    assert y2 > y1  # the right end is lower
    with pytest.raises(PosterError, match="starts left: or right:"):
        draw("balance", "middle: X | 1")


def test_an_iceberg_puts_items_above_and_below_its_waterline():
    svg = draw("iceberg", "above: App\nbelow: Security", 'waterline="Seen"').svg
    assert ">App<" in svg and ">Security<" in svg and ">Seen<" in svg
