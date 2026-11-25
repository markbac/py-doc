"""arch-text's check of ```archt fences, through the container runtime, merged into the lint report."""

from __future__ import annotations

import logging
import shutil

import pytest
from fake_engine import install
from test_diagrams import stub

from py_doc.errors import EnvironmentProblem, ToolFailed
from py_doc.lint import DocLinter
from py_doc.lint.archt import parse
from py_doc.lint.config import LintConfig
from py_doc.runtime import Runtime

needs_arch_text = pytest.mark.skipif(shutil.which("arch-text") is None, reason="arch-text is not installed")

DOC = "# Metering\n\nHow readings flow.\n\n```archt\nsystem Shop\nShop -> Nowher\nShop -> Shop\n```\n"

# What `arch-text build 0.archt` prints for the fence above: each finding, its source line, a caret, and a hint
OUTPUT = """0.archt:2:9: error AT008: Nothing is called "Nowher".
  |
2 | Shop -> Nowher
  |         ^^^^^^
  = Declare it first, for example with `system`.
0.archt:3:1: warning AT010: Edges from an element to itself are not supported yet, so this one is left out.
  |
3 | Shop -> Shop
  | ^^^^^^^^^^^^
"""

# A stand-in for arch-text: prints OUTPUT once for every fence it is given, under that fence's name
REPORT = f"""
names = [a for a in sys.argv[2:] if a.endswith(".archt")]
for n in names:
    sys.stderr.write({OUTPUT!r}.replace("0.archt", n))
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


def archt_issues(report):
    return [(i.line, i.column, i.rule, i.severity) for i in report.issues if i.category == "Architecture"]


def test_the_output_is_read_with_each_hint_joined_to_its_finding():
    assert parse(OUTPUT) == [
        (0, 2, 9, "AT008", "error", 'Nothing is called "Nowher". Declare it first, for example with `system`.'),
        (0, 3, 1, "AT010", "warning",
         "Edges from an element to itself are not supported yet, so this one is left out."),
    ]  # fmt: skip


def test_findings_are_at_their_line_of_the_markdown_file(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "arch-text", REPORT)
    report = DocLinter(diagram_runtime=runtime).lint_paths([doc])
    assert archt_issues(report) == [(7, 9, "AT008", "error"), (8, 1, "AT010", "warning")]
    assert 'Nothing is called "Nowher".' in str(report.issues)


def test_severities_and_disabled_rules_apply_to_arch_text_codes(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "arch-text", REPORT)
    config = LintConfig(disabled_rules=frozenset({"AT010"}))
    config.severities["AT008"] = "info"
    found = archt_issues(DocLinter(config=config, diagram_runtime=runtime).lint_paths([doc]))
    assert found == [(7, 9, "AT008", "info")]


def test_every_fence_of_every_file_is_checked_in_one_run(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "arch-text", REPORT)
    (tmp_path / "b.md").write_text("Text.\n\n```archt\nA\n```\n\n```archt\nB\n```\n", encoding="utf-8")
    report = DocLinter(diagram_runtime=runtime).lint_paths([tmp_path])
    assert sorted({(i.file.name, i.line) for i in report.issues if i.rule == "AT008"}) == [
        ("a.md", 7), ("b.md", 5), ("b.md", 9),
    ]  # fmt: skip


def test_bpmnt_and_archt_fences_share_one_container(tmp_path, monkeypatch, doc):
    stub(tmp_path, monkeypatch, "arch-text", "sys.exit(0)")
    stub(tmp_path, monkeypatch, "bpmn-text", "print('[]')")
    doc.write_text(DOC + "\n```bpmnt\npool Shop\n```\n", encoding="utf-8")
    engine = install(tmp_path, monkeypatch, mode="host")
    asked = []

    def runtime():
        asked.append(1)
        return Runtime("tools:test", docker=engine.docker, platform_name="linux")

    DocLinter(diagram_runtime=runtime).lint_paths([doc])
    assert asked == [1]


def test_a_file_without_fences_does_not_start_the_container(doc):
    doc.write_text("# Metering\n\nText.\n", encoding="utf-8")

    def runtime():
        raise AssertionError("the container was asked for")

    DocLinter(diagram_runtime=runtime).lint_paths([doc])


def test_without_the_tool_image_the_fences_are_skipped_with_a_warning(doc, caplog):
    def runtime():
        raise EnvironmentProblem("The tool image 'py-doc-tools:x' is not built here. Run `py-doc tools build`")

    with caplog.at_level(logging.WARNING):
        report = DocLinter(diagram_runtime=runtime).lint_paths([doc])
    assert archt_issues(report) == [] and "archt fences were not checked" in caplog.text


def test_a_failure_with_no_finding_is_arch_text_itself_failing(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "arch-text", "print('TypeError: boom', file=sys.stderr)\nsys.exit(1)")
    with pytest.raises(ToolFailed, match="boom"):
        DocLinter(diagram_runtime=runtime).lint_paths([doc])


def test_a_usage_error_is_an_error(tmp_path, monkeypatch, runtime, doc):
    stub(tmp_path, monkeypatch, "arch-text", "print('error: Unknown command', file=sys.stderr)\nsys.exit(2)")
    with pytest.raises(ToolFailed, match="Unknown command"):
        DocLinter(diagram_runtime=runtime).lint_paths([doc])


@needs_arch_text
def test_arch_text_itself(runtime, doc):
    found = archt_issues(DocLinter(diagram_runtime=runtime).lint_paths([doc]))
    assert (7, 9, "AT008", "error") in found and (8, 1, "AT010", "warning") in found
