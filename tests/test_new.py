"""py-doc new: a legacy build file and its Markdown, numbered from the register at the repository root."""

from __future__ import annotations

import datetime
import re

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
        'meta:\n  title: "Pipelines"\n  document_number: "G460-TN-012"\ncli:\n  emit-docx: true\nentries:\n  - file: a.md\n',
        encoding="utf-8",
    )
    (old / "G460-OV-001-overview.yaml").write_text(
        'meta:\n  title: "Overview"\n  document_number: "G460-OV-001"\ncli:\n  output: o.pptx\nentries:\n  - file: b.md\n',
        encoding="utf-8",
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
        {
            "number": "G460-TN-013",
            "title": "Build and Release",
            "file": "docs/notes/G460-TN-013-Build-and-Release.yaml",
        },
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
    [
        (["--type", "TN"], "A title is needed"),
        (["--title", "x", "--type", "T-N"], "letters and digits"),
        (["--title", "x", "--format", "pdf"], "invalid choice"),
    ],
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
    assert (
        "with 2 existing number(s)" in out
        and "number    G460-TN-013" in out
        and "py-doc build --legacy G460-TN-013-Cmd.yaml" in out
    )
    assert main(["new", "-y"]) == 1
    assert "A title is needed" in capsys.readouterr().err


def test_scan_adds_new_build_files_and_keeps_clashing_numbers(repo, capsys):
    make(["--title", "First", "--type", "TN", "--prefix", "G460"])
    other = repo / "docs" / "other"
    other.mkdir()
    (other / "copy.yaml").write_text(
        'meta:\n  title: "Copy"\n  document_number: "G460-TN-012"\nentries:\n  - file: c.md\n', encoding="utf-8"
    )
    assert main(["new", "--scan"]) == 0
    out = capsys.readouterr().out
    assert "added     G460-TN-012  docs/other/copy.yaml" in out
    assert "clash     G460-TN-012 is used by docs/notes/G460-TN-012-pipelines.yaml, docs/other/copy.yaml" in out
    assert [d["file"] for d in register(repo)["documents"]].count("docs/other/copy.yaml") == 1
    assert main(["new", "--scan"]) == 0  # a second scan adds nothing
    assert "added" not in capsys.readouterr().out


def test_start_sets_where_numbers_begin_and_skips_taken_ones(repo, capsys):
    assert main(["new", "--scan", "--start", "12", "--prefix", "G460"]) == 0
    assert "the next ends in 013" in capsys.readouterr().out
    assert register(repo)["start"] == 12
    _, reg, _ = make(["--title", "A", "--type", "SP"])
    assert reg.entries[-1].number == "G460-SP-013"
    assert main(["new", "--start", "100"]) == 0
    _, reg, _ = make(["--title", "B", "--type", "TN"])
    assert reg.entries[-1].number == "G460-TN-100"
    _, reg, _ = make(["--title", "C", "--type", "TN"])
    assert reg.entries[-1].number == "G460-TN-101"


def test_a_bad_start_is_refused(repo, capsys):
    assert main(["new", "--start", "0"]) == 1
    (repo / "doc-numbers.yml").write_text("start: soon\ndocuments: []\n", encoding="utf-8")
    with pytest.raises(new.NewError, match="start must be a whole number"):
        make(["--title", "x"])


LISTED = (
    "prefix: G460\nprefixes: [G460, G470]\ntypes: [TN, OV]\nclassifications: [Confidential, Internal]\ndocuments: []\n"
)


def test_listed_values_are_the_only_ones_allowed_and_keep_the_registers_spelling(repo):
    (repo / "doc-numbers.yml").write_text(LISTED, encoding="utf-8")
    _, reg, _ = make(["--title", "A", "--type", "tn", "--prefix", "g470", "--classification", "internal"])
    assert reg.entries[-1].number == "G470-TN-001"
    meta = yaml.safe_load((repo / "docs" / "notes" / "G470-TN-001-A.yaml").read_text(encoding="utf-8"))["meta"]
    assert meta["classification"] == "Internal"
    assert register(repo)["types"] == ["TN", "OV"]  # the lists are kept when the register is saved


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--type", "SP"], "--type 'SP' is not in the register's list: TN, OV"),
        (["--type", "TN", "--prefix", "G999"], "--prefix 'G999' is not in the register's list: G460, G470"),
        (["--type", "TN", "--classification", "Secret"], "--classification 'Secret' is not in the register's list"),
        ([], "--type is needed: one of TN, OV"),
    ],
)
def test_a_value_outside_a_list_is_refused(repo, args, message):
    (repo / "doc-numbers.yml").write_text(LISTED, encoding="utf-8")
    with pytest.raises(new.NewError, match=re.escape(message)):
        make(["--title", "A", *args])
    assert register(repo)["documents"] == []


def test_the_wizard_offers_the_list_and_asks_again(repo, capsys):
    (repo / "doc-numbers.yml").write_text(LISTED, encoding="utf-8")
    questions = []
    replies = iter(["", "Title", "XX", "", "ov", "", "", "nope", "confidential", "About"])

    def ask(question):
        questions.append(question)
        return next(replies)

    parsed = new.build_parser().parse_args([])
    from pathlib import Path

    _, reg, _ = new.make(Path.cwd(), parsed, ask, TODAY)
    assert reg.entries[-1].number == "G460-OV-001"
    assert questions[0] == "Number prefix (G460, G470) [G460]: "
    assert questions[2] == "Type code (TN, OV): " and questions.count("Type code (TN, OV): ") == 3
    assert "Classification (Confidential, Internal): " in questions
    out = capsys.readouterr().out
    assert "'XX' is not one of TN, OV" in out and "Choose one of TN, OV" in out and "'nope' is not one of" in out


def test_without_lists_anything_goes_and_prefix_can_change_per_document(repo):
    make(["--title", "A", "--type", "TN", "--prefix", "G460"])
    _, reg, _ = make(["--title", "B", "--type", "ZZ9", "--prefix", "X1", "--classification", "Whatever"])
    assert reg.entries[-1].number == "X1-ZZ9-014"
    assert register(repo)["prefix"] == "G460"  # the default stays


def test_an_existing_markdown_file_gets_a_number_and_a_build_file_beside_it(repo, monkeypatch):
    notes = repo / "docs" / "pump"
    notes.mkdir()
    page = notes / "control.md"
    text = "---\nauthor: Bea\ndescription: How the pump is controlled.\nclassification: Internal\n---\n# Pump Control\n\nText.\n"
    page.write_text(text, encoding="utf-8")
    written, reg, _ = make([str(page), "--type", "TN", "--prefix", "G460"])
    assert written == [notes / "G460-TN-013-Pump-Control.yaml"]
    assert page.read_text(encoding="utf-8") == text  # the Markdown is not changed
    data = yaml.safe_load(written[0].read_text(encoding="utf-8"))
    assert data["entries"] == [{"file": "control.md", "heading_offset": 0}]
    assert {k: data["meta"][k] for k in ("title", "author", "description", "classification", "version")} == {
        "title": "Pump Control", "author": "Bea", "description": "How the pump is controlled.",
        "classification": "Internal", "version": "0.1.0",
    }  # fmt: skip
    assert reg.entries[-1] == new.Entry("G460-TN-013", "Pump Control", "docs/pump/G460-TN-013-Pump-Control.yaml")
    result = migrate([written[0]], notes)
    assert not [f for f in result.findings if f.level == "warning"]


def test_an_existing_file_takes_its_front_matter_title_and_options_still_win(repo):
    page = repo / "docs" / "notes" / "x.md"
    page.write_text("---\ntitle: From Front Matter\nversion: 1.2.0\n---\n# Heading\n", encoding="utf-8")
    written, _, _ = make([str(page), "--type", "", "--title", "Given Title"])
    meta = yaml.safe_load(written[0].read_text(encoding="utf-8"))["meta"]
    assert (meta["title"], meta["version"]) == ("Given Title", "1.2.0")
    page2 = repo / "docs" / "notes" / "y.md"
    page2.write_text("---\ntitle: From Front Matter\n---\n# Heading\n", encoding="utf-8")
    written, _, _ = make([str(page2), "--type", ""])
    assert yaml.safe_load(written[0].read_text(encoding="utf-8"))["meta"]["title"] == "From Front Matter"


@pytest.mark.parametrize(
    ("name", "text", "message"),
    [
        ("numbered.md", "---\ndocument_number: X-001\n---\n# A\n", "already has the document number X-001"),
        (
            "a.md",
            "# Already used\n",
            "a.md is already a source of docs/notes/G460-TN-012-pipelines.yaml, number G460-TN-012",
        ),
        ("notes.txt", "text\n", "is not a Markdown file"),
    ],
)
def test_a_file_that_has_a_number_or_is_not_markdown_is_refused(repo, name, text, message):
    page = repo / "docs" / "notes" / name
    page.write_text(text, encoding="utf-8")
    make(["--title", "Seed", "--type", "TN", "--prefix", "G460"])  # makes the register, with pipelines.yaml in it
    with pytest.raises(new.NewError, match=re.escape(message)):
        make([str(page), "--type", "TN"])


def test_the_command_numbers_an_existing_file(repo, capsys):
    page = repo / "docs" / "notes" / "c.md"
    page.write_text("# Cmd Page\n", encoding="utf-8")
    assert main(["new", "-y", str(page), "--type", "TN", "--prefix", "G460"]) == 0
    out = capsys.readouterr().out
    assert "written   G460-TN-013-Cmd-Page.yaml" in out and "c.md" not in out.split("written")[1].split("\n")[0]


def test_the_paths_shown_work_from_where_the_command_was_run(repo, capsys, monkeypatch):
    from pathlib import Path

    monkeypatch.chdir(repo)
    page = repo / "docs" / "notes" / "d.md"
    page.write_text("# From Root\n", encoding="utf-8")
    assert main(["new", "-y", "docs/notes/d.md", "--type", "TN", "--prefix", "G460"]) == 0
    shown = str(Path("docs/notes/G460-TN-013-From-Root.yaml"))
    out = capsys.readouterr().out
    assert f"written   {shown}" in out and f"py-doc build --legacy {shown}" in out
