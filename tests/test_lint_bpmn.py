"""bpmn-text's check of ```bpmnt fences, through the container runtime, merged into the lint report."""

from __future__ import annotations

import logging
import shutil

import pytest
from fake_engine import install
from test_diagrams import stub

from py_doc.errors import EnvironmentProblem, ToolFailed
from py_doc.lint import DocLinter
from py_doc.lint.config import LintConfig
from py_doc.runtime import Runtime

needs_bpmn_text = pytest.mark.skipif(shutil.which("bpmn-text") is None, reason="bpmn-text is not installed")

DOC = "# Orders\n\nHow an order ships.\n\n```bpmnt\npool Shop\n  task A -> Nowhere\n```\n"

# bpmn-text check --format json: one entry per file, with 1-based lines of the fence body
REPORT = """
names = [a for a in sys.argv[1:] if a.endswith(".bpmnt")]
d = {"code": "BT202", "severity": "error", "message": "Nothing is called `Nowhere`.",
     "range": {"start": {"line": 2, "col": 13, "offset": 22}, "end": {"line": 2, "col": 20, "offset": 29}}}
w = dict(d, code="BT301", severity="warning", message="Nothing flows into this element.")
print(json.dumps([{"file": n, "diagnostics": [d, w]} for n in names]))
sys.exit(1)
"""


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    engine = install(tmp_path, monkeypatch, mode="host")
    box = Runtime("tools:test", docker=engine.docker, platform_name="linux")
    return lambda: box


@pytest.fixture
def doc(tmp_path):
    (tmp_path / "a.md").write_text(DOC, encoding="utf-8")
    return tmp_path / "a.md"


def bpmn_issues(report):
    return [(i.line, i.column, i.rule, i.severity) for i in report.issues if i.category == "BPMN"]


def test_findings_are_at_their_line_of_the_markdown_file(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "bpmn-text", REPORT)
    report = DocLinter(bpmn_runtime=runtime).lint_paths([doc])
    assert bpmn_issues(report) == [(7, 13, "BT202", "error"), (7, 13, "BT301", "warning")]
    assert "Nothing is called `Nowhere`." in str(report.issues)


def test_severities_and_disabled_rules_apply_to_bpmn_text_codes(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "bpmn-text", REPORT)
    config = LintConfig(disabled_rules=frozenset({"BT301"}))
    config.severities["BT202"] = "info"
    assert bpmn_issues(DocLinter(config=config, bpmn_runtime=runtime).lint_paths([doc])) == [(7, 13, "BT202", "info")]


def test_every_fence_of_every_file_is_checked_in_one_run(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "bpmn-text", REPORT)
    (tmp_path / "b.md").write_text("Text.\n\n```bpmnt\nA\n```\n\n```bpmnt\nB\n```\n", encoding="utf-8")
    report = DocLinter(bpmn_runtime=runtime).lint_paths([tmp_path])
    assert sorted({(i.file.name, i.line) for i in report.issues if i.category == "BPMN"}) == [
        ("a.md", 7), ("b.md", 5), ("b.md", 9),
    ]  # fmt: skip


def test_a_file_without_fences_does_not_start_the_container(doc, tmp_path):
    doc.write_text("# Orders\n\nText.\n", encoding="utf-8")

    def runtime():
        raise AssertionError("the container was asked for")

    DocLinter(bpmn_runtime=runtime).lint_paths([doc])


def test_without_the_tool_image_the_fences_are_skipped_with_a_warning(doc, caplog):
    def runtime():
        raise EnvironmentProblem("The tool image 'py-doc-tools:x' is not built here. Run `py-doc tools build`")

    with caplog.at_level(logging.WARNING):
        report = DocLinter(bpmn_runtime=runtime).lint_paths([doc])
    assert bpmn_issues(report) == [] and "bpmnt fences were not checked" in caplog.text


def test_a_tool_that_does_not_finish_is_an_error(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "bpmn-text", "print('Internal error: boom', file=sys.stderr)\nsys.exit(2)")
    with pytest.raises(ToolFailed, match="boom"):
        DocLinter(bpmn_runtime=runtime).lint_paths([doc])


@needs_bpmn_text
def test_bpmn_text_itself(runtime, doc):
    found = bpmn_issues(DocLinter(bpmn_runtime=runtime).lint_paths([doc]))
    assert (7, 13, "BT202", "error") in found
