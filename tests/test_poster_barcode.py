"""Linear barcodes on posters: the data checks, the check digits, the drawing, and a reader getting the data back."""

from __future__ import annotations

import pytest
from py_doc.poster import build
from py_doc.poster_barcode import BarcodeError, barcode_svg, checked, gs1_check_digit, human_text, kind_of, pattern
from py_doc.poster_blocks import PosterError


def write(tmp_path, body: str):
    path = tmp_path / "poster.md"
    path.write_text(f"---\ntitle: Barcodes\n---\n\n## A\n\n{body}\n", encoding="utf-8")
    return path


class TestData:
    @pytest.mark.parametrize(
        "kind, given, encoded",
        [
            ("ean13", "501234567890", "5012345678900"),  # the check digit is worked out
            ("ean13", "4006381333931", "4006381333931"),  # or checked
            ("ean8", "9638507", "96385074"),
            ("upca", "03600029145", "036000291452"),
            ("upca", "0360 0029 1452", "036000291452"),  # spaces are only for reading
            ("itf14", "1540014128876", "15400141288763"),
            ("code39", "sn-100", "SN-100"),
            ("code128", "SN-100 A7/b", "SN-100 A7/b"),
        ],
    )
    def test_check_digits_and_letters(self, kind, given, encoded):
        assert checked(kind, given) == encoded

    @pytest.mark.parametrize(
        "kind, data, message",
        [
            ("ean13", "5012345678901", "the check digit of 5012345678901 should be 0, not 1: is a digit mistyped"),
            ("ean13", "50123", "ean13 takes 12 digits"),
            ("upca", "ABCDEFGHIJK", "upca takes 11 digits"),
            ("itf14", "15400141288760", "should be 3, not 0"),
            ("code39", "sn_100", "code39 has only A to Z"),
            ("code128", "café", "printable ASCII only"),
            ("code128", "  ", "needs the data to encode"),
        ],
    )
    def test_mistakes_say_what_is_wrong(self, kind, data, message):
        with pytest.raises(BarcodeError, match=message):
            checked(kind, data)

    def test_types_and_their_other_names(self):
        assert [kind_of(k) for k in (None, "EAN-13", "upc", "itf", "39", "128")] == ["code128", "ean13", "upca", "itf14", "code39", "code128"]
        with pytest.raises(BarcodeError, match="type must be one of code128, code39"):
            kind_of("pdf417")

    def test_the_gs1_check_digit(self):
        assert [gs1_check_digit(d) for d in ("400638133393", "1540014128876", "9638507")] == ["1", "3", "4"]

    def test_the_text_under_the_bars(self):
        assert human_text("ean13", "5012345678900") == "5 012345 678900"
        assert human_text("upca", "036000291452") == "0 36000 29145 2"
        assert human_text("itf14", "15400141288763") == "1 54 00141 28876 3"
        assert human_text("code39", "SN-100", check=True).startswith("*SN-100") and human_text("code39", "SN-100") == "*SN-100*"


class TestDrawing:
    def test_guard_bars_are_longer_on_ean_and_upc(self):
        assert pattern("ean13", "5012345678900").count("G") == 6 and len(pattern("ean13", "5012345678900")) == 95
        assert len(pattern("upca", "036000291452")) == 95 and len(pattern("ean8", "96385074")) == 67
        svg = barcode_svg("ean13", "5012345678900", "#123456", width=300, height=80)
        heights = {float(h) for h in __import__("re").findall(r'<rect [^>]*height="([\d.]+)"', svg)}
        assert len(heights) == 2 and min(heights) == 80  # bars and the longer guards
        assert 'fill="#123456"' in svg and 'width="300"' in svg
        assert [t for t in __import__("re").findall(r">(\d+)</text>", svg)] == ["5", "012345", "678900"]  # placed as on products

    def test_itf14_has_bearer_bars_and_text_can_be_left_out(self):
        svg = barcode_svg("itf14", "15400141288763", "#000", text=False)
        assert 'fill-rule="evenodd"' in svg and "<text" not in svg

    def test_itf14_keeps_ten_narrow_bars_clear_inside_its_frame(self):
        import re

        modules = pattern("itf14", "15400141288763")
        svg = barcode_svg("itf14", "15400141288763", "#000", width=1000)
        unit = 1000 / (len(modules) + 2 * 20 + 2 * 8)
        first_bar = min(float(x) for x in re.findall(r'<rect x="([\d.]+)"', svg))
        frame = 8 * unit
        assert round((first_bar - frame) / unit) == 20  # 10 narrow bars of 2 modules: the reader needs this space


class TestBlock:
    def test_blocks_on_a_poster(self, tmp_path):
        body = '```barcode type=ean13 label="SN-100 retail box"\n501234567890\n```\n\n```barcode width=320 height=50\nSN-100-0042\n```'
        page, _ = build(write(tmp_path, body), lambda: object())
        assert page.count('<div class="barcode"><svg') == 2 and '<div class="cap">SN-100 retail box</div>' in page
        assert ">012345</text>" in page and ">678900</text>" in page and ">SN-100-0042</text>" in page

    @pytest.mark.parametrize(
        "body, message",
        [
            ("```barcode type=ean13\n5012345678901\n```", "poster.md: the check digit"),
            ("```barcode type=qr\nx\n```", "type must be one of"),
            ("```barcode check=yes\nABC\n```", "check=yes is for code39"),
            ("```barcode text=maybe\nABC\n```", "text must be yes or no"),
            ("```barcode width=wide\nABC\n```", "width must be a whole number"),
        ],
    )
    def test_block_mistakes_name_the_poster(self, tmp_path, body, message):
        with pytest.raises(PosterError, match=message):
            build(write(tmp_path, body), lambda: object())


zxingcpp = pytest.importorskip("zxingcpp", reason="zxing-cpp is not installed, so the barcodes are not read back")

READERS = {"code128": "Code128", "code39": "Code39", "ean13": "EAN13", "ean8": "EAN8", "upca": "UPCA", "itf14": "ITF"}


@pytest.mark.parametrize(
    "kind, data",
    [("code128", "SN-100 A7/b"), ("code39", "SN-100"), ("ean13", "501234567890"), ("ean8", "9638507"), ("upca", "03600029145"), ("itf14", "1540014128876")],
)
def test_a_reader_gets_back_what_was_encoded(kind, data):
    from PIL import Image

    encoded = checked(kind, data)
    modules = pattern(kind, encoded)
    scale, quiet, height = 3, 15, 60
    image = Image.new("L", ((len(modules) + 2 * quiet) * scale, height), 255)
    for i, m in enumerate(modules):
        if m in "1G":
            image.paste(0, ((quiet + i) * scale, 0, (quiet + i + 1) * scale, height))
    formats = getattr(zxingcpp.BarcodeFormat, READERS[kind])
    found = zxingcpp.read_barcodes(image, formats=formats)
    assert found, f"no {kind} found"
    # A UPC-A is the EAN-13 of the same number with a leading 0, and some readers give it in that form
    assert found[0].text in ((encoded, "0" + encoded) if kind == "upca" else (encoded,))
