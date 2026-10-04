"""Corpus tests: run every Markdown fixture through the converter."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from docx_helpers import texts

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_NAMES = sorted(p.name for p in FIXTURE_DIR.glob("*.md"))

# Fixtures whose conversion currently loses content, mapped to the tracking issue.
KNOWN_CONTENT_LOSS: dict[str, str] = {}

WORD = re.compile(r"[^\W\d_]{2,}")


def _words_outside_fence_markers(markdown: str) -> set[str]:
    words: set[str] = set()
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            continue  # the fence line and its info string are not content
        words.update(w.lower() for w in WORD.findall(line))
    return words


def _params():
    for name in FIXTURE_NAMES:
        marks = []
        if name in KNOWN_CONTENT_LOSS:
            marks.append(pytest.mark.xfail(strict=True, reason=KNOWN_CONTENT_LOSS[name]))
        yield pytest.param(name, marks=marks, id=name)


def test_corpus_is_present():
    expected = {
        "headings", "paragraphs", "lists", "nested_lists", "code", "links", "images",
        "tables", "quotes", "thematic_breaks", "inline_formatting", "malformed",
        "unclosed_fence", "mixed",
    }  # fmt: skip
    assert expected <= {Path(n).stem for n in FIXTURE_NAMES}


@pytest.mark.parametrize("name", list(_params()))
def test_conversion_preserves_every_word(name, convert_fixture):
    """No fixture may lose words, whatever its constructs are rendered as."""
    out = convert_fixture(name)
    source_words = _words_outside_fence_markers((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    output_words = {w.lower() for t in texts(out) for w in WORD.findall(t)}
    assert source_words - output_words == set()


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_conversion_succeeds_and_produces_a_valid_docx(name, convert_fixture):
    out = convert_fixture(name)
    assert out.exists() and out.stat().st_size > 0
    texts(out)  # raises if python-docx cannot open the result


@pytest.mark.parametrize("name", ["mixed", "headings", "lists", "code"])
def test_golden_output(name, convert_fixture, check_golden):
    """Change detector for the current renderer output.

    A failure means the rendered structure changed. If that is intended (for
    example when #8 lands), regenerate with UPDATE_GOLDEN=1 and review the diff.
    """
    check_golden(name, convert_fixture(f"{name}.md"))
