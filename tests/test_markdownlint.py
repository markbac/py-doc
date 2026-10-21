"""markdownlint through the container runtime, merged into the lint report."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fake_engine import install

from py_doc.app import main
from py_doc.errors import ConversionError
from py_doc.lint import DocLinter
from py_doc.lint.config import LintConfig, MarkdownlintSettings
from py_doc.lint.mdlint import parse_findings, run_markdownlint
from py_doc.runtime import Runtime

needs_tool = pytest.mark.skipif(shutil.which("markdownlint-cli2") is None, reason="markdownlint-cli2 is not installed")

BAD = "# Title\nText right after\n\n* star item\n* another\n"


def test_findings_are_parsed_from_the_tool_output():
    output = (
        "markdownlint-cli2 v0.23.2\nFinding: a.md\n"
        'sub/a.md:1 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1] [Context: "# T"]\n'
        "a.md:4:1 error MD004/ul-style Unordered list style\n"
        "Summary: 2 issues\n"
    )
    found = parse_findings(output, Path("/base"))
    assert found[0] == (
        Path("/base/sub/a.md"),
        1,
        "MD022",
        'Headings should be surrounded by blank lines [Expected: 1] [Context: "# T"] (blanks-around-headings)',
    )
    assert found[1][:3] == (Path("/base/a.md"), 4, "MD004")


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    engine = install(tmp_path, monkeypatch, mode="host")
    box = Runtime("tools:test", docker=engine.docker, platform_name="linux")
    monkeypatch.setattr("py_doc.lint.cli.connect", lambda settings: box)
    return lambda: box


@pytest.fixture
def docs(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text(BAD, encoding="utf-8")
    return tmp_path / "docs"


@needs_tool
def test_inline_config_and_severity(docs, runtime):
    settings = MarkdownlintSettings(
        inline={"default": True, "MD004": {"style": "dash"}, "MD022": False}, severity="error"
    )
    issues = run_markdownlint([docs / "a.md"], settings, runtime)
    assert {(i.rule, i.line, i.severity, i.category) for i in issues} == {
        ("MD004", 4, "error", "Markdown"),
        ("MD004", 5, "error", "Markdown"),
    }
    assert not any(i.rule == "MD022" for i in issues)
    assert issues and all(i.file == docs / "a.md" for i in issues)


@needs_tool
def test_config_file(docs, runtime, tmp_path):
    config = tmp_path / "mdl.yaml"
    config.write_text("default: false\nMD004:\n  style: dash\n", encoding="utf-8")
    issues = run_markdownlint([docs / "a.md"], MarkdownlintSettings(config=config), runtime)
    assert {i.rule for i in issues} == {"MD004"} and {i.line for i in issues} == {4, 5}


@needs_tool
def test_files_in_different_folders(docs, runtime, tmp_path):
    (docs / "sub").mkdir()
    (docs / "sub" / "b.md").write_text(BAD, encoding="utf-8")
    settings = MarkdownlintSettings(inline={"default": False, "MD004": {"style": "dash"}})
    issues = run_markdownlint([docs / "a.md", docs / "sub" / "b.md"], settings, runtime)
    assert {i.file for i in issues} == {docs / "a.md", docs / "sub" / "b.md"}


@needs_tool
def test_a_broken_config_is_a_tool_failure(docs, runtime, tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("MD004: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConversionError, match="markdownlint-cli2"):
        run_markdownlint([docs / "a.md"], MarkdownlintSettings(config=config), runtime)


def test_the_tool_is_not_needed_when_markdownlint_is_not_configured(docs):
    report = DocLinter(config=LintConfig()).lint_path(docs)  # no runtime given, and none needed
    assert report.files_scanned == 1


def test_configured_without_a_runtime_is_an_error(docs):
    config = LintConfig(markdownlint=MarkdownlintSettings(inline={"default": True}))
    with pytest.raises(ConversionError, match="needs the tool container"):
        DocLinter(config=config).lint_path(docs)


@needs_tool
class TestCommand:
    def setup(self, docs, tmp_path, extra):
        (tmp_path / "py-doc.yml").write_text(
            "lint:\n  rules: {DOC001: off, DOC002: off, DOC003: off}\n  markdownlint:\n    config: {default: false, MD004: {style: dash}}\n"
            + extra
            + "documents:\n  d: {sources: [docs/a.md]}\n",
            encoding="utf-8",
        )

    def test_one_list_one_summary_and_warnings_do_not_fail(self, docs, tmp_path, runtime, monkeypatch, capsys):
        self.setup(docs, tmp_path, "")
        monkeypatch.chdir(tmp_path)
        assert main(["lint", "docs"]) == 0
        out = capsys.readouterr().out
        assert "MD004" in out and out.count("[SUMMARY]") == 1 and "2 issue(s) reported" in out

    def test_strict_and_error_severity_change_the_status(self, docs, tmp_path, runtime, monkeypatch, capsys):
        self.setup(docs, tmp_path, "")
        monkeypatch.chdir(tmp_path)
        assert main(["lint", "docs", "--strict"]) == 1
        self.setup(docs, tmp_path, "")
        text = (
            (tmp_path / "py-doc.yml")
            .read_text()
            .replace("MD004: {style: dash}}", "MD004: {style: dash}}\n    severity: error")
        )
        (tmp_path / "py-doc.yml").write_text(text, encoding="utf-8")
        assert main(["lint", "docs"]) == 1

    def test_structure_and_markdownlint_findings_share_the_exit_status(
        self, docs, tmp_path, runtime, monkeypatch, capsys
    ):
        self.setup(
            docs,
            tmp_path,
            "  structure:\n    - {id: s/star, type: regex-line, severity: error, pattern: '^\\* ', message: no stars}\n",
        )
        monkeypatch.chdir(tmp_path)
        assert main(["lint", "docs"]) == 1
        out = capsys.readouterr().out
        assert "s/star" in out and "MD004" in out and out.count("[SUMMARY]") == 1

    def test_the_container_being_unavailable_is_status_2(self, docs, tmp_path, monkeypatch, capsys):
        from py_doc.errors import EnvironmentProblem

        def down(settings):
            raise EnvironmentProblem("Docker is not running")

        monkeypatch.setattr("py_doc.lint.cli.connect", down)
        self.setup(docs, tmp_path, "")
        monkeypatch.chdir(tmp_path)
        assert main(["lint", "docs"]) == 2
        assert "Docker is not running" in capsys.readouterr().err


def test_example_rules_can_be_printed(capsys):
    assert main(["lint", "--print-example-rules"]) == 0
    assert "structure/horizontal-rule" in capsys.readouterr().out
