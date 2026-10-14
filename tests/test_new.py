"""py-doc new: a legacy build file and its Markdown, numbered from the register at the repository root."""

from __future__ import annotations

import datetime

import pytest
import yaml
from py_doc import new
from py_doc.app import main
from py_doc.config import parse_config
from py_doc.migrate import migrate

TODAY = datetime.date(2026, 10, 14)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    old = tmp_path / "docs" / "notes"
    old.mkdir(parents=True)
    (old / "G460-TN-012-pipelines.yaml").write_text(
        'meta:\n  title: "Pipelines"\n  document_number: "G460-TN-012"\ncli:\n  emit-docx: true\nentries:\n  - file: a.md\n', encoding="utf-8"
    )
    (old / "G460-OV-001-overview.yaml").write_text(
        'meta:\n  title: "Overview"\n  document_number: "G460-OV-001"\ncli:\n  output: o.pptx\nentries:\n  - file: b.md\n', encoding="utf-8"
    )
    monkeypatch.chdir(old)
    monkeypatch.setattr(new, "_git_name", lambda: "Ann Author")
    return tmp_path


def make(args: list[str], answers: list[str] | None = None):
    parsed = new.build_parser().parse_args(args)
    replies = iter(answers or [])
    ask = (lambda question: next(replies)) if answers is not None else None
    from pathlib import Path

    return new.make(Path.cwd(), parsed, ask, TODAY)


def register(root) -> dict:
    return yaml.safe_load((root / "doc-numbers.yml").read_text(encoding="utf-8"))


def test_the_first_run_makes_the_register_from_the_existing_build_files(repo):
    written, _, created = make(["--title", "Build and Release", "--type", "tn", "--prefix", "G460"])
    assert created
    data = register(repo)
    assert data["prefix"] == "G460"
    assert data["documents"] == [
        {"number": "G460-OV-001", "title": "Overview", "file": "docs/notes/G460-OV-001-overview.yaml"},
        {"number": "G460-TN-012", "title": "Pipelines", "file": "docs/notes/G460-TN-012-pipelines.yaml"},
        {"number": "G460-TN-013", "title": "Build and Release", "file": "docs/notes/G460-TN-013-Build-and-Release.yaml"},
    ]
    assert [p.name for p in written] == ["G460-TN-013-Build-and-Release.yaml", "G460-TN-013-Build-and-Release.md"]


def test_one_counter_for_every_type_and_prefix_and_type_are_optional(repo):
    make(["--title", "One", "--type", "SP", "--prefix", "G460"])
    _, reg, _ = make(["--title", "Two", "--type", ""])
    assert [e.number for e in reg.entries][-2:] == ["G460-SP-013", "G460-014"]
    (repo / "doc-numbers.yml").write_text("documents: []\n", encoding="utf-8")
    _, reg, _ = make(["--title", "Three", "--type", ""])
    assert reg.entries[-1].number == "001"


def test_the_build_file_is_the_legacy_format_and_builds(repo):
    written, _, _ = make(["--title", "Deck", "--type", "OV", "--prefix", "G460", "--format", "pptx", "--classification", "Confidential",
                          "--description", 'Says "hello"'])  # fmt: skip
    data = yaml.safe_load(written[0].read_text(encoding="utf-8"))
    assert data["meta"] == {
        "title": "Deck", "author": "Ann Author", "version": "0.1.0", "date": "14 October 2026",
        "description": 'Says "hello"', "document_number": "G460-OV-013", "classification": "Confidential",
    }  # fmt: skip
    assert data["cli"] == {"output": "G460-OV-013-Deck.pptx"}
    assert data["entries"] == [{"file": "G460-OV-013-Deck.md", "heading_offset": 0}]
    assert written[1].read_text(encoding="utf-8").startswith("# Deck\n")
    result = migrate([written[0]], written[0].parent)
    assert not [f for f in result.findings if f.level == "warning"]
    parse_config(result.config, written[0].parent)


def test_the_wizard_asks_what_is_not_given(repo):
    answers = ["G460", "Asked title", "tn", "", "", "Internal", "About it"]
    written, reg, _ = make([], answers)
    assert reg.entries[-1].number == "G460-TN-013"
    meta = yaml.safe_load(written[0].read_text(encoding="utf-8"))["meta"]
    assert (meta["author"], meta["classification"], meta["description"]) == ("Ann Author", "Internal", "About it")


def test_the_register_is_found_from_a_subfolder_and_numbers_never_repeat(repo, monkeypatch):
    make(["--title", "A", "--type", "TN", "--prefix", "G460"])
    deeper = repo / "docs" / "other"
    deeper.mkdir()
    monkeypatch.chdir(deeper)
    _, reg, created = make(["--title", "B", "--type", "TN"])
    assert not created and reg.entries[-1] == new.Entry("G460-TN-014", "B", "docs/other/G460-TN-014-B.yaml")


@pytest.mark.parametrize(
    ("args", "message"),
    [(["--type", "TN"], "A title is needed"), (["--title", "x", "--type", "T-N"], "letters and digits"), (["--title", "x", "--format", "pdf"], "invalid choice")],
)
def test_mistakes_are_refused_and_nothing_is_written(repo, args, message, capsys):
    with pytest.raises((new.NewError, SystemExit)):
        make(args)
    assert not (repo / "doc-numbers.yml").exists()


def test_an_existing_file_is_not_replaced(repo):
    (repo / "docs" / "notes" / "G460-TN-013-Same.md").write_text("mine\n", encoding="utf-8")
    with pytest.raises(new.NewError, match="already exists"):
        make(["--title", "Same", "--type", "TN", "--prefix", "G460"])
    assert (repo / "docs" / "notes" / "G460-TN-013-Same.md").read_text(encoding="utf-8") == "mine\n"


def test_the_command_reports_what_it_did(repo, capsys):
    assert main(["new", "-y", "--title", "Cmd", "--type", "TN", "--prefix", "G460"]) == 0
    out = capsys.readouterr().out
    assert "with 2 existing number(s)" in out and "number    G460-TN-013" in out and "py-doc build --legacy G460-TN-013-Cmd.yaml" in out
    assert main(["new", "-y"]) == 1
    assert "A title is needed" in capsys.readouterr().err
