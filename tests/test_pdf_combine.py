"""py-doc build --combine: the PDFs of a project's documents joined into one, with a bookmark each."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from py_doc.app import main
from py_doc.pdf_combine import combine


def pdf(path: Path, pages: int, title: str | None = None, headings: tuple[str, ...] = ()) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    for number, heading in enumerate(headings):
        writer.add_outline_item(title=heading, page_number=number)
    if title:
        writer.add_metadata({"/Title": title})
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def test_documents_are_joined_in_order_with_a_bookmark_each(tmp_path):
    guide = pdf(tmp_path / "guide.pdf", 3, "User guide", ("Install", "Use"))
    spec = pdf(tmp_path / "spec.pdf", 2)  # no title of its own: the name given, else the file name
    pages = combine([(None, guide), ("Requirements", spec)], tmp_path / "out" / "all.pdf", title="Pump")
    assert pages == 5
    reader = PdfReader(tmp_path / "out" / "all.pdf")
    top = [item for item in reader.outline if not isinstance(item, list)]
    assert [item.title for item in top] == ["User guide", "Requirements"]
    assert [reader.get_destination_page_number(item) for item in top] == [0, 3]
    assert [h.title for h in reader.outline[1]] == ["Install", "Use"]  # the guide's own headings, below it
    assert reader.metadata["/Title"] == "Pump" and reader.page_mode == "/UseOutlines"
    assert not list((tmp_path / "out").glob("*.part"))


def test_nothing_to_join_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="no document"):
        combine([], tmp_path / "all.pdf")


def test_combine_takes_only_pdf(tmp_path, monkeypatch, capsys):
    (tmp_path / "py-doc.yml").write_text("documents:\n  a:\n    sources: [a.md]\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("# A\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["build", "--combine", "all.pdf", "-f", "docx", "--no-lint"]) == 1
    assert "--combine joins PDFs" in capsys.readouterr().err
