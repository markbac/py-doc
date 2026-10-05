"""Reading document metadata from front matter."""

from __future__ import annotations

import pytest
from py_doc.markdown import FrontMatterError, Metadata, parse, read_metadata


def meta(text: str) -> Metadata:
    return read_metadata(parse(text))


def test_a_document_without_front_matter_has_no_metadata():
    assert meta("# Title\n") == Metadata()


def test_empty_front_matter_has_no_metadata():
    assert meta("---\n---\n\n# Title\n") == Metadata()


def test_the_standard_keys_are_read_as_text():
    result = meta(
        "---\ntitle: Design Notes\nsubtitle: A draft\nauthor: Mark\ndate: 2026-10-05\nversion: 1.2\n"
        "status: Review\ndocument_id: DN-7\nkeywords: [a, b]\n---\n"
    )
    assert result == Metadata("Design Notes", "A draft", "Mark", "2026-10-05", "1.2", "Review", "DN-7", "a, b")


def test_aliases_map_to_the_standard_keys():
    result = meta("---\nid: X-1\ntags: [a, b]\nTitle: Cased\n---\n")
    assert (result.document_id, result.keywords, result.title) == ("X-1", "a, b", "Cased")


@pytest.mark.parametrize(("value", "expected"), [("2026-10-05", "2026-10-05"), ("2026-10-05 09:30:00", "2026-10-05T09:30:00")])
def test_dates_are_written_in_iso_form(value, expected):
    assert meta(f"---\ndate: {value}\n---\n").date == expected


def test_numbers_and_lists_become_text():
    result = meta("---\nversion: 2\nauthor: [Ann, Bob]\n---\n")
    assert (result.version, result.author) == ("2", "Ann, Bob")


def test_other_keys_are_kept_as_they_are():
    result = meta("---\ntitle: T\nlayout: wide\nweight: 3\n---\n")
    assert result.extra == {"layout": "wide", "weight": 3}


def test_empty_values_are_none():
    assert meta("---\ntitle:\nauthor: ''\n---\n") == Metadata()


def test_invalid_yaml_names_the_line():
    with pytest.raises(FrontMatterError, match=r"Invalid front matter at line 1"):
        meta("---\ntitle: [unclosed\n---\n")


@pytest.mark.parametrize("body", ["- a\n- b", "just text"])
def test_front_matter_that_is_not_a_mapping_is_an_error(body):
    with pytest.raises(FrontMatterError, match="must be a mapping"):
        meta(f"---\n{body}\n---\n")
