"""The protocol, embedded and explanation blocks of posters, and inline sparklines."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from py_doc.poster_blocks import MD, Ctx, PosterError, block_fragment, inline, parse_opts
from py_doc.poster_embedded import FUNCTIONS
from py_doc.poster_svg import sparkline, sparklines
from py_doc.poster_themes import Theme

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><rect width="100" height="50"/></svg>'


def ctx(base=Path(".")):
    return Ctx(base, lambda: None, Theme(), render=lambda text, c: text, where="test.md")


def draw(lang, code, info="", base=Path(".")):
    return block_fragment(lang, parse_opts(info), code, ctx(base))


# --- hex-dissect ---

COAP = "bytes: 54 45 7a 31\n0 | Header | NON | navy\n1 | Code | 2.05 | blue\n2-3 | Message ID | 0x7a31 | green"


def test_a_hex_dump_shows_each_byte_its_field_and_ascii():
    svg = draw("hex-dissect", COAP).svg
    assert [m for m in re.findall(r">([0-9a-f]{2})<", svg)] == ["54", "45", "7a", "31"]
    assert ">Message ID<" in svg and ">0x7a31<" in svg and ">2-3<" in svg
    assert ">T<" in svg and ">E<" in svg  # the bytes as text
    assert svg.count('fill-opacity=".2"') == 4  # every byte belongs to a field


def test_hex_bytes_can_be_written_without_spaces_and_ranges_with_a_length():
    svg = draw("hex-dissect", "bytes: 5445\n0+2 | Both | | red", "ascii=no").svg
    assert ">54<" in svg and ">45<" in svg and ">0-1<" in svg and ">T<" not in svg


@pytest.mark.parametrize(
    "code, message",
    [
        ("0 | Header", "needs a 'bytes:' line"),
        ("bytes: 54 zz", "'zz' is not a byte"),
        ("bytes: 54\n0-3 | Header", "ends at byte 3, but there are 1 bytes"),
        ("bytes: 54 45\n1-0 | Back", "ends before it starts"),
    ],
)
def test_hex_dissect_mistakes(code, message):
    with pytest.raises(PosterError, match=message):
        draw("hex-dissect", code)


# --- syntax-anatomy ---


def test_a_string_is_taken_apart_token_by_token_in_order():
    svg = draw("syntax-anatomy", "coap://host:5683/3/0\ncoap | Scheme | navy\n3 | Object | green\n0 | Instance").svg
    assert ">coap://host:5683/3/0<" in svg and ">Scheme<" in svg and ">Instance<" in svg
    assert svg.count('height="5" rx="2"') == 3


def test_every_label_stays_inside_the_drawing():
    tokens = "\n".join(f"{n} | Label {n}" for n in range(8))
    svg = draw("syntax-anatomy", "0/1/2/3/4/5/6/7\n" + tokens).svg
    width = float(re.search(r'viewBox="0 0 ([\d.]+)', svg)[1])
    xs = [float(x) for x in re.findall(r'<text x="([\d.]+)"[^>]*text-anchor="middle"', svg)]
    assert xs and all(60 <= x <= width - 60 for x in xs)


def test_a_token_that_is_not_in_the_string_is_an_error():
    with pytest.raises(PosterError, match="'b' is not in 'a/a' after the tokens before it"):
        draw("syntax-anatomy", "a/a\na | First\nb | Second")


# --- code-compare ---


def test_code_compare_has_marked_panels_badges_and_notes():
    html = draw("code-compare", "@bad Unsafe\nstrcpy(a, b);  <1>\n@good Safe\nstrncpy(a, b, n);\n-- 1 | Unbounded").html
    assert '<div class="cc bad"><div class="cc-h">&#10007; Unsafe</div>' in html
    assert '<div class="cc good"><div class="cc-h">&#10003; Safe</div>' in html
    assert '<div>strcpy(a, b);<b class="cb">1</b></div>' in html
    assert '<ol class="cc-notes"><li><b class="cb">1</b>Unbounded</li></ol>' in html
    assert "repeat(2," in html


def test_code_compare_escapes_code_and_needs_a_panel():
    assert "&lt;stdio.h&gt;" in draw("code-compare", "@plain C\n#include <stdio.h>").html
    with pytest.raises(PosterError, match="starts with a panel"):
        draw("code-compare", "int x;")


# --- pinout ---

PINS = "1 | VDD | pwr\n2 | PA0 | adc\n3 | GND | gnd\n4 | SDA | i2c"


@pytest.mark.parametrize("package", ["dip", "qfn", "header"])
def test_a_pinout_shows_each_pin_in_its_function_colour(package):
    svg = draw("pinout", PINS, f"package={package}").svg
    for name in ("VDD", "PA0", "GND", "SDA"):
        assert f">{name}<" in svg
    assert FUNCTIONS["i2c"] in svg and ">I2C<" in svg  # the legend names the functions used


def test_a_pin_function_may_be_a_colour_and_a_package_must_be_known():
    assert "#123456" in draw("pinout", "1 | X | #123456").svg
    with pytest.raises(PosterError, match="package must be one of"):
        draw("pinout", PINS, "package=bga")


# --- instrument ---


def test_a_scope_draws_each_channel_and_its_cursor_readout():
    svg = draw("instrument", "Ch1 | | 0 1 2 1 0\nCh2 | red | 1 1 1 1 1", 'type=scope tdiv="5 ms" cursors=2,4').svg
    assert svg.count("<polyline") == 2 and ">Δt = 10 ms<" in svg and ">Ch1 1 V/div<" in svg


def test_a_logic_analyser_draws_square_waves_from_bits():
    svg = draw("instrument", "CLK | 0101\nCS# | 1001", "type=logic").svg
    assert svg.count("<polyline") == 2 and ">CS#<" in svg
    with pytest.raises(PosterError, match="logic line is"):
        draw("instrument", "CLK | 012", "type=logic")


def test_a_meter_shows_its_value_in_seven_segment_digits():
    svg = draw("instrument", "", 'type=meter value="2.41 µA" label="Asleep" min=2.38').svg
    assert svg.count('rx="') >= 3 * 7 and ">µA<" in svg and ">MIN 2.38<" in svg
    with pytest.raises(PosterError, match="needs value="):
        draw("instrument", "", "type=meter")


def test_an_unknown_instrument_is_an_error():
    with pytest.raises(PosterError, match="instrument type must be one of"):
        draw("instrument", "", "type=radio")


# --- proscons and glossary ---


def test_pros_and_cons_go_in_their_columns():
    html = draw("proscons", "+ Long battery\n- Slow", 'pros="For" cons="Against"').html
    assert '<div class="pc pro"><div class="pc-h">For</div><ul><li><b>&#10003;</b><span>Long battery</span>' in html
    assert '<div class="pc con"><div class="pc-h">Against</div>' in html
    with pytest.raises(PosterError, match="starts '\\+ ' or '- '"):
        draw("proscons", "Long battery")


def test_a_glossary_lists_terms_and_definitions():
    html = draw("glossary", "PSM | Power saving mode\neDRX | Extended DRX", "cols=1").html
    assert '<div class="gl"><b>PSM</b><span>Power saving mode</span></div>' in html and "repeat(1," in html
    with pytest.raises(PosterError, match="'Term \\| definition'"):
        draw("glossary", "PSM")


# --- annotated and zoom-chain ---


def test_an_annotated_picture_has_numbered_pins_and_a_legend(tmp_path):
    (tmp_path / "board.svg").write_text(SVG, encoding="utf-8")
    html = draw("annotated", "board.svg\n30%, 40% | Sensor | On I2C | blue\n60,50 | Radio", base=tmp_path).html
    assert 'src="data:image/svg+xml;base64,' in html
    assert '<b class="pin" style="left:30.0%;top:40.0%;background:' in html and ">2</b>" in html
    assert "<strong>Sensor</strong><span>On I2C</span>" in html


@pytest.mark.parametrize(
    "code, message",
    [
        ("missing.svg", "is not there"),
        ("board.svg\n130%, 20% | X", "not a percentage"),
        ("board.svg\n20% | X", "starts 'x%, y%'"),
    ],
)
def test_annotated_mistakes(tmp_path, code, message):
    (tmp_path / "board.svg").write_text(SVG, encoding="utf-8")
    with pytest.raises(PosterError, match=message):
        draw("annotated", code, base=tmp_path)


def test_a_zoom_chain_frames_what_the_next_picture_shows(tmp_path):
    for name in ("a.svg", "b.svg"):
        (tmp_path / name).write_text(SVG, encoding="utf-8")
    html = draw("zoom-chain", "a.svg | Room | | 10%, 20%, 30%, 40%\nb.svg | Node | 10×", base=tmp_path).html
    assert html.count('<figure class="zp">') == 2
    assert '<i class="zbox" style="left:10.0%;top:20.0%;width:30.0%;height:40.0%"></i>' in html
    assert '<div class="zarrow"><b>10×</b>' in html
    with pytest.raises(PosterError, match="at least two pictures"):
        draw("zoom-chain", "a.svg | Room", base=tmp_path)


# --- sparklines ---


def test_a_sparkline_ends_with_a_dot_at_its_last_value():
    svg = sparkline([1, 3, 2])
    assert svg.startswith('<svg class="spark"') and svg.count("<circle") == 1
    assert sparkline([5]) == ""


def test_sparklines_are_drawn_in_text_and_cells_but_not_in_code():
    assert '<svg class="spark"' in inline("A week {spark 1,3,2,5} of readings")
    assert '<svg class="spark"' in sparklines(MD.render("| a |\n|---|\n| {spark 1,2,3} |"))
    out = sparklines(MD.render("Write `{spark 1,2,3}` to draw one."))
    assert "{spark 1,2,3}" in out and '<svg class="spark"' not in out
