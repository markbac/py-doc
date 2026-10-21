"""What a poster qr block encodes: the standard forms for contacts, events, Wi-Fi and the rest, read back by a
QR decoder where one is installed."""

from __future__ import annotations

import io

import pytest
import segno
from py_doc.poster import build
from py_doc.poster_blocks import PosterError
from py_doc.poster_qr import QrError, kind_of, payload


def write(tmp_path, body: str):
    path = tmp_path / "poster.md"
    path.write_text(f"---\ntitle: QR\n---\n\n## A\n\n{body}\n", encoding="utf-8")
    return path


class TestPayloads:
    def test_text_and_urls_are_as_written(self):
        assert payload("url", "https://example.com/a\n") == "https://example.com/a"
        assert payload("text", "Two\nlines") == "Two\nlines"

    def test_a_contact_card(self):
        card = payload("vcard", "name: Jane van der Berg\norg: Example; Instruments\ntel: +44 1234 567890\ntel: +44 1234 567891\n"
                                "mobile: +44 7700 900123\nemail: jane@example.com\nurl: https://example.com\n"
                                "address: 1 High Street, Leeds, LS1 1AA, UK\nnote: Ask for Jane, or the desk")
        assert card.split("\r\n") == [
            "BEGIN:VCARD", "VERSION:3.0", "N:Berg;Jane van der;;;", "FN:Jane van der Berg", "ORG:Example\\; Instruments",
            "TEL;TYPE=WORK,VOICE:+44 1234 567890", "TEL;TYPE=WORK,VOICE:+44 1234 567891", "TEL;TYPE=CELL:+44 7700 900123",
            "EMAIL;TYPE=INTERNET:jane@example.com", "URL:https://example.com", "ADR;TYPE=WORK:;;1 High Street;Leeds;;LS1 1AA;UK",
            "NOTE:Ask for Jane\\, or the desk", "END:VCARD",
        ]  # fmt: skip

    def test_an_event_with_times_and_an_all_day_one(self):
        event = payload("event", "title: Commissioning, day 1\nstart: 2026-11-03 09:00\nend: 2026-11-03 17:30\nlocation: Site B")
        lines = event.split("\r\n")
        assert lines[:3] == ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//py-doc//poster//EN"] and lines[-2:] == ["END:VEVENT", "END:VCALENDAR"]
        assert "DTSTART:20261103T090000" in lines and "DTEND:20261103T173000" in lines
        assert "SUMMARY:Commissioning\\, day 1" in lines and "LOCATION:Site B" in lines
        all_day = payload("event", "title: Open day\nstart: 2026-11-03\nend: 2026-11-04").split("\r\n")
        assert "DTSTART;VALUE=DATE:20261103" in all_day and "DTEND;VALUE=DATE:20261105" in all_day  # the day after the last
        one_hour = payload("event", "title: Call\nstart: 2026-11-03 09:00Z").split("\r\n")
        assert "DTSTART:20261103T090000Z" in one_hour and "DTEND:20261103T100000Z" in one_hour

    def test_the_same_event_is_the_same_code(self):
        text = "title: Call\nstart: 2026-11-03 09:00"
        assert payload("event", text) == payload("event", text)

    def test_wifi_email_phone_sms_and_geo(self):
        assert payload("wifi", "ssid: Site;Guest\npassword: p:a\"ss") == 'WIFI:T:WPA;S:Site\\;Guest;P:p\\:a\\"ss;;'
        assert payload("wifi", "ssid: Open\nhidden: yes") == "WIFI:T:nopass;S:Open;H:true;;"
        assert payload("email", "to: help@example.com\nsubject: Unit 7 & 8\nbody: Hello there") == (
            "mailto:help@example.com?subject=Unit%207%20%26%208&body=Hello%20there"
        )
        assert payload("phone", "number: +44 (0)1234 567-890") == "tel:+4401234567890"
        assert payload("sms", "number: +44 7700 900123\nbody: JOIN") == "SMSTO:+447700900123:JOIN"
        assert payload("geo", "lat: 53.7997\nlon: -1.5492") == "geo:53.7997,-1.5492"

    def test_text_already_in_the_standard_form_is_kept(self):
        card = "BEGIN:VCARD\nVERSION:3.0\nFN:A\nEND:VCARD"
        assert payload("vcard", card) == card

    @pytest.mark.parametrize(
        "kind, text, message",
        [
            ("vcard", "phone: 123", "type=vcard has no 'phone'. Keys: name"),
            ("vcard", "email: a@b.c", "needs a 'name:' line"),
            ("vcard", "just a name", "line 1 of a type=vcard block is not 'key: value'"),
            ("event", "title: T", "needs a 'start:' line"),
            ("event", "title: T\nstart: 3 November", "start must be YYYY-MM-DD"),
            ("event", "title: T\nstart: 2026-11-03 10:00\nend: 2026-11-03 09:00", "end is before start"),
            ("event", "title: T\nstart: 2026-11-03\nend: 2026-11-03 09:00", "must both be dates, or both dates and times"),
            ("wifi", "ssid: S\nsecurity: WPA", "needs a 'password:' line"),
            ("wifi", "ssid: S\nsecurity: magic\npassword: x", "security must be WPA, WEP or none"),
            ("phone", "number: call me", "is not a phone number"),
            ("geo", "lat: 95\nlon: 0", "lat must be between -90 and 90"),
            ("email", "to: a@b.c\nto: d@e.f", "takes one 'to', not 2"),
            ("url", "  \n", "needs the text or address"),
        ],
    )
    def test_mistakes_say_what_is_wrong(self, kind, text, message):
        with pytest.raises(QrError, match=message):
            payload(kind, text)

    def test_types_and_their_other_names(self):
        assert [kind_of(k) for k in (None, "contact", "vcf", "ical", "calendar", "tel", "mailto")] == ["url", "vcard", "vcard", "event", "event", "phone", "email"]
        with pytest.raises(QrError, match="type must be one of url, text, vcard"):
            kind_of("barcode")


class TestBlock:
    def test_a_typed_block_and_a_file(self, tmp_path):
        (tmp_path / "jane.vcf").write_text("BEGIN:VCARD\nVERSION:3.0\nFN:Jane\nEND:VCARD\n", encoding="utf-8")
        body = '```qr type=vcard label="Call Jane"\nname: Jane Smith\ntel: +44 1234 567890\n```\n\n```qr file=jane.vcf ecc=h size=120\n```'
        page, _ = build(write(tmp_path, body), lambda: object())
        assert page.count('<div class="qr"><svg') == 2 and '<div class="cap">Call Jane</div>' in page

    @pytest.mark.parametrize(
        "body, message",
        [
            ("```qr type=vcard\nphone: 1\n```", "poster.md: type=vcard has no 'phone'"),
            ("```qr file=missing.vcf\n```", "the qr file missing.vcf is not there"),
            ("```qr ecc=x\nhttps://example.com\n```", "ecc must be L, M, Q or H"),
            ("```qr type=barcode\nx\n```", "type must be one of"),
            ("```qr size=big\nhttps://example.com\n```", "size must be a whole number"),
        ],
    )
    def test_block_mistakes_name_the_poster(self, tmp_path, body, message):
        with pytest.raises(PosterError, match=message):
            build(write(tmp_path, body), lambda: object())


zxingcpp = pytest.importorskip("zxingcpp", reason="zxing-cpp is not installed, so the codes are not read back")


@pytest.mark.parametrize(
    "kind, text",
    [
        ("vcard", "name: Jane Smith\norg: Example Instruments\ntel: +44 1234 567890\nemail: jane@example.com"),
        ("event", "title: Commissioning day\nstart: 2026-11-03 09:00\nend: 2026-11-03 17:00\nlocation: Site B"),
        ("wifi", "ssid: Site-Guest\npassword: s3cret;pass"),
        ("email", "to: help@example.com\nsubject: Unit 7"),
        ("geo", "lat: 53.7997\nlon: -1.5492"),
    ],
)
def test_a_reader_gets_back_what_was_encoded(kind, text):
    from PIL import Image

    data = payload(kind, text)
    png = io.BytesIO()
    segno.make(data, error="m", micro=False).save(png, kind="png", scale=8, border=4)
    (found,) = zxingcpp.read_barcodes(Image.open(io.BytesIO(png.getvalue())))
    assert found.text == data
