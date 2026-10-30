"""The space, optics, atomic, nuclear and particle blocks of posters."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from py_doc.poster_blocks import BLOCKS, Ctx, PosterError, block_fragment, parse_opts
from py_doc.poster_elements import BY_NUMBER, CATEGORIES, ELEMENTS
from py_doc.poster_space import TOPOLOGIES
from py_doc.poster_themes import Theme

SPACE = (
    "orbits", "optics", "interferometer", "spacetime", "energy-levels", "feynman", "standard-model", "elements",
    "nuclide-chart",
)  # fmt: skip


def ctx():
    return Ctx(Path("."), lambda: None, Theme(), render=lambda text, c: text, where="test.md")


def draw(lang, code, info=""):
    return block_fragment(lang, parse_opts(info), code, ctx())


@pytest.mark.parametrize("name", SPACE)
def test_every_space_block_draws_its_example_as_svg(name):
    assert draw(name, BLOCKS[name].example, BLOCKS[name].info).svg.startswith('<svg class="chart"')


# --- orbits ---


def test_orbits_are_to_scale_with_a_transfer_and_lagrange_points():
    svg = draw("orbits", "orbit: A | 1\norbit: B | 2\ntransfer: 1 | 2 | Go\nlagrange: A").svg
    rx = [float(r) for r in re.findall(r'<ellipse [^>]*rx="([\d.]+)"', svg)]
    assert rx[1] == pytest.approx(2 * rx[0])
    assert ">Δv₁<" in svg and ">Δv₂<" in svg and all(f">L{n}<" in svg for n in range(1, 6))


def test_an_eccentric_orbit_is_an_ellipse_with_the_star_at_a_focus():
    svg = draw("orbits", "orbit: Comet | 1 | | e=0.6").svg
    cx, rx, ry = (
        float(v) for v in re.search(r'<ellipse cx="([\d.]+)" cy="[\d.]+" rx="([\d.]+)" ry="([\d.]+)"', svg).groups()
    )
    assert ry == pytest.approx(rx * 0.8, rel=0.01) and cx < 230  # centred away from the star at 230


def test_orbit_mistakes():
    with pytest.raises(PosterError, match="names no orbit"):
        draw("orbits", "orbit: A | 1\nlagrange: B")
    with pytest.raises(PosterError, match="needs at least one orbit"):
        draw("orbits", "")


# --- optics, interferometer, spacetime ---


@pytest.mark.parametrize("kind", ["refractor", "newtonian", "cassegrain", "tma"])
def test_each_telescope_has_its_rays(kind):
    assert draw("optics", "", f"type={kind}").svg.count("<polyline") == 3


@pytest.mark.parametrize("kind", ["michelson", "fabry-perot"])
def test_each_interferometer_draws(kind):
    assert ">Laser<" in draw("interferometer", "", f"type={kind}").svg


def test_a_worldline_must_be_slower_than_light():
    assert ">Slow<" in draw("spacetime", "worldline: Slow | 0.3").svg
    with pytest.raises(PosterError, match="between -1 and 1"):
        draw("spacetime", "worldline: Fast | 1.2")


def test_wells_and_a_penrose_diagram():
    assert ">Sun<" in draw("spacetime", "Sun | 1\nStar | 100", "mode=well scale=log").svg
    assert ">Singularity, r = 0<" in draw("spacetime", "", "mode=penrose blackhole=yes").svg
    with pytest.raises(PosterError, match="mode must be"):
        draw("spacetime", "", "mode=wormhole")


# --- energy levels ---


def test_a_jump_is_coloured_by_the_wavelength_of_its_light():
    svg = draw("energy-levels", "level: a | -3.4\nlevel: b | -1.51\njump: b | a | H-alpha").svg
    assert ">H-alpha 656 nm<" in svg  # 1239.84 / 1.89 eV
    assert re.search(r'stroke="#ff0000"', svg)  # red light


def test_close_levels_get_their_labels_spread_apart():
    svg = draw("energy-levels", "level: a | -1.0\nlevel: b | -0.99\nlevel: c | -13").svg
    ya = float(re.search(r'<text x="[\d.]+" y="([\d.]+)"[^>]*>a</text>', svg)[1])
    yb = float(re.search(r'<text x="[\d.]+" y="([\d.]+)"[^>]*>b</text>', svg)[1])
    assert abs(ya - yb) >= 16


def test_a_jump_must_name_its_levels():
    with pytest.raises(PosterError, match="names the level 'z'"):
        draw("energy-levels", "level: a | 1\nlevel: b | 2\njump: a | z")


# --- Feynman ---


@pytest.mark.parametrize("topology", sorted(TOPOLOGIES))
def test_every_topology_draws(topology):
    svg = draw("feynman", "", f"topology={topology}").svg
    assert svg.count('r="5" fill') >= 1  # its vertices


def test_feynman_lines_take_labels_and_kinds_by_slot():
    svg = draw("feynman", "in1: e⁻\nmid: g | gluon", "topology=s-channel").svg
    assert ">e⁻<" in svg and ">g<" in svg and Theme().colours["good"] in svg  # the gluon's coil
    with pytest.raises(PosterError, match="has the slots"):
        draw("feynman", "top: x", "topology=s-channel")
    with pytest.raises(PosterError, match="topology must be one of"):
        draw("feynman", "", "topology=pentagon")


# --- the standard model, elements, nuclides ---


def test_the_standard_model_has_its_17_particles_and_highlights():
    svg = draw("standard-model", "", "highlight=H").svg
    assert svg.count('rx="8"') == 17 and ">125.2 GeV<" in svg
    assert 'fill-opacity="1" stroke="#a3322b"' in svg  # the Higgs stands out


def test_the_periodic_table_is_complete_and_right_where_it_is_checked():
    assert len(ELEMENTS) == 118 and sorted(BY_NUMBER) == list(range(1, 119))
    assert BY_NUMBER[26][1:4] == ("Fe", "Iron", "55.85") and BY_NUMBER[79][1] == "Au" and BY_NUMBER[92][3] == "238.03"
    assert {e[4] for e in ELEMENTS.values()} <= set(CATEGORIES)


def test_elements_are_found_by_symbol_or_number():
    svg = draw("elements", "fe 79\nO").svg
    assert ">Iron<" in svg and ">Gold<" in svg and ">Oxygen<" in svg and ">transition metal<" in svg
    with pytest.raises(PosterError, match="'Xx' is not an element"):
        draw("elements", "Xx")


def test_a_nuclide_chart_colours_each_nuclide_by_its_decay():
    svg = draw("nuclide-chart", "1 | 0 | ¹H | stable\n6 | 8 | ¹⁴C | beta-", "magic=yes valley=yes").svg
    assert "#1d1f27" in svg and "#3f74b8" in svg and ">Protons, Z<" in svg
    with pytest.raises(PosterError, match="a decay is one of"):
        draw("nuclide-chart", "1 | 0 | H | spontaneous")


def test_energy_levels_have_a_key_of_what_they_drew():
    svg = draw("energy-levels", "level: a | -3\nlevel: b | -1\njump: b | a | down").svg
    assert ">Emitted: down, wavy<" in svg and "Absorbed" not in svg  # only the kinds of arrow drawn
    assert 'fill="url(#energy-spectrum)"' in svg and "Ultraviolet" not in svg  # 2 eV is 620 nm: visible...
    svg = draw("energy-levels", "level: a | -3\nlevel: b | -2.5\njump: b | a | down").svg
    assert "Ultraviolet or infrared" in svg  # ...0.5 eV is infrared


def test_the_u_channel_keeps_its_arrows_and_labels_off_the_crossing():
    svg = draw("feynman", "out1: c\nout2: d", "topology=u-channel").svg
    # the outgoing lines cross at (440, 160); their arrows sit three quarters along, clear of it
    heads = re.findall(r'<line x1="[\d.]+" y1="[\d.]+" x2="([\d.]+)" y2="([\d.]+)"[^>]*marker-end', svg)
    assert heads and all(abs(float(x) - 440) > 40 for x, _ in heads[-2:])


def test_a_periodic_table_puts_every_element_in_its_place():
    svg = draw("elements", "Fe Au", "layout=table").svg
    assert svg.count("<rect") >= 118 + len(CATEGORIES)
    assert svg.count('fill-opacity=".14"') == 116  # the rest in a pale tint of their category
    assert ">57-71<" in svg and ">89-103<" in svg
    assert draw("elements", "", "layout=table").svg.count('fill-opacity=".14"') == 0  # none named: all solid


def test_a_nuclide_path_is_arrows_named_in_the_key():
    svg = draw("nuclide-chart", "6 | 6 | C | stable\n7 | 6 | N | beta+\npath: 6,6 7,6 | Capture | amber").svg
    assert 'marker-end="url(#nuc-path0)"' in svg and ">Capture<" in svg
