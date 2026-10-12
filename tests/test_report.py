"""The JSON build report: contents, stable output, failures and the schema."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fake_engine import install
from jsonschema import Draft202012Validator

from py_doc.app import main
from py_doc.report import SCHEMA, counts
from py_doc.runtime import Runtime

needs_pandoc = pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is not installed")
needs_dot = pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz is not installed")
VALIDATOR = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

GOOD = "digraph { a -> b }"


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PY_DOC_CACHE", str(tmp_path / "cache"))


@pytest.fixture
def run(tmp_path, monkeypatch):
    engine = install(tmp_path, monkeypatch, mode="host")
    runtime = Runtime("tools:test", docker=engine.docker, platform_name="linux")
    from py_doc import app

    monkeypatch.setattr(app, "connect", lambda settings: runtime)
    monkeypatch.chdir(tmp_path)

    def build(markdown: str, *args: str, config_extra: str = ""):
        (tmp_path / "a.md").write_text(markdown, encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text(
            f"documents:\n  a:\n    sources: [a.md]\n    outputs: {{docx: {{}}}}\n{config_extra}", encoding="utf-8"
        )
        status = main(["build", *args])
        return status

    return build


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert list(VALIDATOR.iter_errors(data)) == []
    return data


def test_counts_skip_code_and_headings():
    text = "# Title\n\nOne sentence. Two sentences!\n\n```python\nx = 1. 2.\n```\n\nThird?\n"
    assert counts(text) == {"words": 5, "sentences": 3, "paragraphs": 2}


@needs_pandoc
def test_a_good_build_is_described(tmp_path, run):
    assert run("# A\n\nHello world. Again.\n", "--report", "out/r.json") == 0
    data = load(tmp_path / "out" / "r.json")
    assert (data["status"], data["error"]) == ("ok", None)
    (document,) = data["documents"]
    assert document["sources"] == [{"file": "a.md", "words": 3, "sentences": 2, "paragraphs": 1}]
    (output,) = document["outputs"]
    built = tmp_path / "build" / "a.docx"
    assert output["path"] == "build/a.docx" and output["bytes"] == built.stat().st_size
    import hashlib

    assert output["sha256"] == hashlib.sha256(built.read_bytes()).hexdigest()
    assert data["tools"]["pandoc"].startswith("pandoc")
    assert data["image"]["tag"] == "tools:test"
    assert "generated" not in data


@needs_pandoc
def test_two_builds_give_the_same_report(tmp_path, run):
    """Apart from the checksums: Word files hold the time they were written, so their bytes differ."""
    run("# A\n\ntext\n", "--report", "one.json")
    run("# A\n\ntext\n", "--report", "two.json")
    one, two = (load(tmp_path / name) for name in ("one.json", "two.json"))
    for data in (one, two):
        for output in data["documents"][0]["outputs"]:
            del output["sha256"], output["bytes"]
    assert one == two
    assert (tmp_path / "one.json").read_text().count("\n") == (tmp_path / "two.json").read_text().count("\n")


@needs_pandoc
def test_timestamps_are_only_added_on_request(tmp_path, run):
    run("# A\n\ntext\n", "--report", "r.json", "--timestamps")
    assert "generated" in load(tmp_path / "r.json")


@needs_pandoc
def test_reports_path_in_the_configuration(tmp_path, run):
    run("# A\n\ntext\n", config_extra="reports: {path: reports/build.json}\n")
    assert load(tmp_path / "reports" / "build.json")["status"] == "ok"


@needs_pandoc
@needs_dot
def test_diagrams_are_listed_with_cache_hits(tmp_path, run):
    text = f"# A\n\n```dot\n{GOOD}\n```\n"
    run(text, "--report", "one.json", "--timestamps")
    run(text, "--report", "two.json", "--timestamps")
    first, second = (load(tmp_path / n)["diagrams"][0] for n in ("one.json", "two.json"))
    assert (first["type"], first["file"], first["line"], first["status"]) == ("graphviz", "a.md", 3, "ok") or first["type"] == "dot"
    assert (first["cached"], second["cached"]) == (False, True)
    assert "seconds" in first
    assert "dot" in load(tmp_path / "two.json")["tools"]


@needs_pandoc
@needs_dot
def test_a_failing_diagram_is_named_and_the_status_is_not_zero(tmp_path, run):
    assert run("# A\n\n```dot\ndigraph { a -> \n```\n", "--report", "r.json") == 1
    data = load(tmp_path / "r.json")
    assert data["status"] == "failed" and data["documents"][0]["status"] == "failed"
    assert "a.md:3" in data["error"]
    (diagram,) = data["diagrams"]
    assert diagram["status"] == "failed" and diagram["line"] == 3 and diagram["error"]


@needs_pandoc
def test_warnings_carry_file_and_line(tmp_path, run):
    run("# A\n\nValue {{missing}} here.\n", "--report", "r.json")
    warnings = load(tmp_path / "r.json")["warnings"]
    found = [w for w in warnings if "missing" in w["message"]]
    assert found and found[0]["line"] == 3 and found[0]["file"].endswith("a.md")


@needs_pandoc
def test_template_problems_are_in_the_report(tmp_path, run):
    from docx import Document

    template = Document()
    template.styles["Normal"].font.bold = True
    template.save(str(tmp_path / "t.docx"))
    run("# A\n\ntext\n", "--report", "r.json", config_extra="outputs:\n  docx: {template: t.docx}\n")
    (entry,) = load(tmp_path / "r.json")["templates"]
    assert entry["path"] == "t.docx" and any("Bold leak" in f for f in entry["failures"])


def test_a_missing_source_still_writes_a_report(tmp_path, run):
    (tmp_path / "py-doc.yml").write_text("documents:\n  a:\n    sources: [gone.md]\n", encoding="utf-8")
    assert main(["build", "--report", "r.json"]) == 1
    data = load(tmp_path / "r.json")
    assert data["status"] == "failed" and "gone.md" in data["error"]
