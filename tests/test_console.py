"""Output that the console's encoding cannot show is replaced, not fatal."""

from __future__ import annotations

import io
import sys

from py_doc._cli import safe_console


def test_a_character_the_output_cannot_encode_becomes_a_question_mark(monkeypatch):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", newline="\n")  # what a pipe or a file gets on Windows
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
    safe_console()
    print("waiting \u23f3 done")
    stream.flush()
    assert raw.getvalue() == b"waiting ? done" + b"\n"


def test_utf8_output_is_left_alone(monkeypatch):
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", stream)
    safe_console()
    assert stream.errors == "strict"
