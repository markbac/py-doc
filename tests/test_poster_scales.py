"""The scale blocks of posters: threshold, waterfall, buckets, gauge, dial24, rating, gradient-scale, logscale
and spectrum."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from py_doc.poster_blocks import BLOCKS, Ctx, PosterError, block_fragment, parse_opts
from py_doc.poster_scales import wavelength_to_rgb
from py_doc.poster_svg import standalone
from py_doc.poster_themes import Theme


def ctx():
    return Ctx(Path("."), lambda: None, Theme(), render=lambda text, c: text, where="test.md")


def draw(lang, code, info=""):
    return block_fragment(lang, parse_opts(info), code, ctx())


def numbers(svg, attr):
    return [float(v) for v in re.findall(rf'{attr}="(-?[\d.]+)"', svg)]


# --- every block that draws SVG writes a picture that is valid on its own ---


@pytest.mark.parametrize("name", sorted(name for name, b in BLOCKS.items() if b.example))
def test_every_svg_block_is_valid_xml_on_its_own(name):
    drawn = draw(name, BLOCKS[name].example, BLOCKS[name].info)
    if drawn.svg is None:
        return
    ET.fromstring(standalone(drawn.svg, Theme()).split("\n", 1)[1])  # a duplicate attribute would raise here


SCALES = ("threshold", "buckets", "gauge", "dial24", "rating", "gradient-scale", "logscale", "spectrum")


@pytest.mark.parametrize("name", SCALES)
def test_scale_blocks_are_all_svg(name):
    assert draw(name, BLOCKS[name].example, BLOCKS[name].info).svg


# --- threshold ---

GRID = """span: Low | Emergency | red | 2
pin: 48.8 Hz Load shedding | red
span: Normal | Balanced | green | 4
pin: 50.2 Hz | green
span: High | Curtail | amber | 2"""


def test_threshold_bands_are_in_proportion_and_pins_sit_on_their_edges():
    svg = draw("threshold", GRID).svg
    rects = [
        (float(x), float(w)) for x, w in re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="30"', svg)
    ]
    assert len(rects) == 3
    assert rects[1][1] == pytest.approx(2 * rects[0][1], rel=0.01)  # weight 4 against 2
    circles = [float(x) for x in re.findall(r'<circle cx="([\d.]+)"', svg)]
    assert circles == pytest.approx([rects[1][0], rects[2][0]], abs=0.2)


def test_threshold_words_go_under_their_band_and_a_target_is_marked():
    svg = draw("threshold", GRID, 'target="50 Hz nominal"').svg
    assert ">Balanced<" in svg and ">50 Hz nominal<" in svg and 'stroke-dasharray="4 3"' in svg


def test_threshold_lines_must_say_what_they_are():
    with pytest.raises(PosterError, match="starts span:, pin: or target:"):
        draw("threshold", "band: x")
    with pytest.raises(PosterError, match="at least one span"):
        draw("threshold", "pin: x")


def test_wide_blocks_can_be_drawn_wider():
    assert 'viewBox="0 0 960 ' in draw("threshold", GRID).svg
    assert 'viewBox="0 0 1400 ' in draw("threshold", GRID, "width=1400").svg
    with pytest.raises(PosterError, match="width must be"):
        draw("threshold", GRID, "width=20")


# --- waterfall ---

TOPUP = "Top-up | +25 | blue\nRepay | -10\nCredit | =15 | green"


def test_a_waterfall_is_a_chart_type_and_steps_from_the_running_total():
    svg = draw("chart", TOPUP, 'type=waterfall unit="£"').svg
    assert ">+£25<" in svg and ">-£10<" in svg and ">£15<" in svg
    bars = re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)" fill', svg)
    (top1, h1), (top2, h2), (top3, h3) = [(float(y), float(h)) for y, h in bars]
    assert top2 == pytest.approx(top1)  # the repayment hangs from the top of the top-up
    assert h3 == pytest.approx(h1 - h2, rel=0.01)  # the total is what is left


def test_a_waterfall_value_must_be_a_number():
    with pytest.raises(PosterError, match="is not a number"):
        draw("chart", "Top-up | lots", "type=waterfall")


# --- buckets, gauge, dial24, rating ---


def test_a_bucket_is_filled_to_its_share_and_shows_its_thresholds():
    svg = draw("buckets", "Credit | 5 | 20 | green | 2 Low; 10 Half", 'unit="£"').svg
    assert ">25 %<" in svg and ">£2 Low<" in svg and ">£10 Half<" in svg and ">£5 of £20<" in svg
    with pytest.raises(PosterError, match="capacity of 'X' must be above zero"):
        draw("buckets", "X | 1 | 0")


def test_a_gauge_needle_points_at_its_value():
    svg = draw("gauge", "0 | 50 | green\n50 | 100 | red", "value=100 min=0 max=100").svg
    needle = re.search(
        r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke="[^"]+" stroke-width="5"', svg
    )
    x1, y1, x2, y2 = (float(v) for v in needle.groups())
    assert x2 > x1 and y2 == pytest.approx(y1, abs=0.5)  # the maximum is flat to the right
    with pytest.raises(PosterError, match="needs value=, min= and max="):
        draw("gauge", "", "value=1")


def test_a_dial24_period_runs_past_midnight():
    svg = draw("dial24", "22:00 | 06:00 | Night | navy").svg
    assert ">22:00 to 06:00<" in svg and ">Night<" in svg
    with pytest.raises(PosterError, match="is not a time"):
        draw("dial24", "25:00 | 06:00 | Night")


def test_a_rating_points_at_its_current_and_potential_bands():
    svg = draw("rating", "", "current=D potential=B").svg
    assert svg.count(">D<") == 2 and svg.count(">B<") == 2 and ">Current<" in svg
    with pytest.raises(PosterError, match="rating Z is not one of its bands"):
        draw("rating", "", "current=Z")


# --- gradient-scale, logscale ---


def test_two_gradient_scales_on_a_page_do_not_share_a_gradient():
    a = draw("gradient-scale", "1 | One", "from=0 to=10").svg
    b = draw("gradient-scale", "2 | Two", "from=0 to=10").svg
    assert re.search(r'id="(g\w+)"', a)[1] != re.search(r'id="(g\w+)"', b)[1]


def test_a_logscale_has_a_tick_for_each_power_of_ten():
    svg = draw("logscale", "1e-9 | ns\n1e-3 | ms").svg
    assert svg.count("10⁻") >= 7 and ">ns<" in svg
    with pytest.raises(PosterError, match="must be above zero"):
        draw("logscale", "0 | none")


# --- spectrum ---


@pytest.mark.parametrize(
    "nm, colour", [(380, "#000000"), (440, "#0000ff"), (580, "#ffff00"), (700, "#ff0000"), (800, "#000000")]
)
def test_wavelengths_have_their_colours(nm, colour):
    if 380 < nm < 750:
        assert wavelength_to_rgb(nm) == colour
    else:
        assert wavelength_to_rgb(nm - 0.1 if nm == 380 else nm) == colour


def test_absorption_lines_are_dark_and_emission_lines_bright_on_black():
    absorption = draw("spectrum", "589 | Na D", "mode=absorption").svg
    emission = draw("spectrum", "557.7 | O", "mode=emission").svg
    assert 'fill="#000"' in absorption.split("</defs>", 1)[1].split('fill="url', 1)[1]
    assert '<rect x="20" y="44" width="600" height="46" fill="#000"/>' in emission
    assert wavelength_to_rgb(557.7) in emission


def test_a_redshift_adds_a_shifted_track():
    svg = draw("spectrum", "500 | X", "mode=absorption shift=0.2").svg
    assert ">z = 0.2<" in svg


@pytest.mark.parametrize("mode", ["em", "stellar"])
def test_the_whole_spectrum_and_the_star_classes_need_no_lines(mode):
    assert draw("spectrum", "", f"mode={mode}").svg


def test_channels_are_lobes_on_a_frequency_axis():
    svg = draw("spectrum", "Wi-Fi 1 | 2412 | 20\nBLE 37 | 2402 | 2", "mode=channels").svg
    assert svg.count(" C") == 2 and ">Wi-Fi 1<" in svg
    with pytest.raises(PosterError, match="channel line is"):
        draw("spectrum", "Wi-Fi 1 | 2412", "mode=channels")


def test_an_unknown_spectrum_mode_is_an_error():
    with pytest.raises(PosterError, match="spectrum mode must be one of"):
        draw("spectrum", "", "mode=sound")
