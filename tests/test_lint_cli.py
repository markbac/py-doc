"""File errors, directory walking and the py-doclint command line."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from py_doc.lint import DocLinter, LintConfig, LintTargetError
from py_doc.lint.cli import run


@pytest.fixture
def tree(tmp_path):
    """A docs tree with a typo in one file and clean files elsewhere, plus directories to skip."""
    (tmp_path / "docs" / "guide").mkdir(parents=True)
    (tmp_path / "docs" / "index.md").write_text("# Index\n\nA clean page.\n", encoding="utf-8")
    (tmp_path / "docs" / "guide" / "setup.md").write_text("# Setup\n\nUse dtls here.\n", encoding="utf-8")
    (tmp_path / "docs" / "notes.txt").write_text("dtls but not Markdown", encoding="utf-8")
    for skipped in (".venv", "node_modules", ".git", "vendor", "build"):
        (tmp_path / "docs" / skipped).mkdir()
        (tmp_path / "docs" / skipped / "README.md").write_text("json dtls\n", encoding="utf-8")
    return tmp_path / "docs"


class TestFileErrors:
    def test_a_missing_file_is_an_error_result_not_a_clean_one(self, tmp_path):
        result = DocLinter().lint_file(tmp_path / "missing.md")
        assert result.error == "File not found"
        assert result.issues == []

    def test_a_file_that_is_not_utf8_is_an_error_result(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_bytes(b"caf\xe9\n")
        assert "Not valid UTF-8" in DocLinter().lint_file(path).error

    def test_a_directory_given_as_a_file_is_an_error_result(self, tmp_path):
        assert DocLinter().lint_file(tmp_path).error.startswith("Cannot read file")

    def test_one_bad_file_does_not_stop_the_others(self, tree):
        (tree / "bad.md").write_bytes(b"\xff\xfe\x00")
        report = DocLinter().lint_path(tree)
        assert [r.file.name for r in report.errors] == ["bad.md"]
        assert report.files_scanned == 3
        assert len(report.issues) == 1

    def test_unsupported_markdown_is_an_error_result(self, tmp_path, monkeypatch):
        from py_doc.lint import linter
        from py_doc.markdown import ParseError

        def fail(_text):
            raise ParseError("Unsupported Markdown block 'x' at line 2")

        monkeypatch.setattr(linter, "parse", fail)
        path = tmp_path / "a.md"
        path.write_text("x\n", encoding="utf-8")
        assert DocLinter().lint_file(path).error == "Unsupported Markdown block 'x' at line 2"


class TestTargets:
    def test_missing_target_raises(self, tmp_path):
        with pytest.raises(LintTargetError, match="Path not found"):
            DocLinter().lint_path(tmp_path / "nope")

    def test_a_file_that_is_not_markdown_raises(self, tree):
        with pytest.raises(LintTargetError, match="Not a Markdown file"):
            DocLinter().lint_path(tree / "notes.txt")

    def test_a_single_markdown_file_is_linted(self, tree):
        report = DocLinter().lint_path(tree / "guide" / "setup.md")
        assert report.files_scanned == 1
        assert [i.line for i in report.issues] == [3]


class TestDirectoryWalk:
    def test_hidden_and_vendor_directories_are_skipped(self, tree):
        report = DocLinter().lint_path(tree)
        assert [r.file.relative_to(tree).as_posix() for r in report.results] == ["guide/setup.md", "index.md"]

    def test_clean_files_are_counted_as_scanned(self, tree):
        report = DocLinter().lint_path(tree)
        assert report.files_scanned == 2
        assert [len(r.issues) for r in report.results] == [1, 0]

    def test_extra_directories_can_be_excluded(self, tree):
        config = LintConfig(exclude_dirs=LintConfig().exclude_dirs | {"guide"})
        report = DocLinter(config=config).lint_path(tree)
        assert report.files_scanned == 1
        assert report.issues == []

    def test_uppercase_and_markdown_suffixes_are_found(self, tmp_path):
        (tmp_path / "README.MD").write_text("A dtls typo.\n", encoding="utf-8")
        (tmp_path / "b.markdown").write_text("Clean.\n", encoding="utf-8")
        (tmp_path / "c.mdx").write_text("dtls\n", encoding="utf-8")
        report = DocLinter().lint_path(tmp_path)
        assert [r.file.name for r in report.results] == ["README.MD", "b.markdown"]
        assert len(report.issues) == 1

    def test_the_order_is_stable(self, tmp_path):
        for name in ("b.md", "a.md", "c.md"):
            (tmp_path / name).write_text("ok\n", encoding="utf-8")
        assert [r.file.name for r in DocLinter().lint_path(tmp_path).results] == ["a.md", "b.md", "c.md"]


class TestCommandLine:
    def test_issues_are_printed_with_paths_relative_to_the_working_directory(self, tree, monkeypatch, capsys):
        monkeypatch.chdir(tree.parent)
        assert run(["docs"]) == 0
        out = capsys.readouterr().out
        assert "docs/guide/setup.md:3: warning DOC001 [Glossary]".replace("/", os.sep) in out

    def test_files_with_the_same_name_can_be_told_apart(self, tmp_path, monkeypatch, capsys):
        for folder in ("one", "two"):
            (tmp_path / folder).mkdir()
            (tmp_path / folder / "README.md").write_text("A dtls typo.\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        run(["."])
        out = capsys.readouterr().out
        assert "one/README.md:1:".replace("/", os.sep) in out
        assert "two/README.md:1:".replace("/", os.sep) in out

    def test_the_summary_counts_scanned_files_and_issues(self, tree, capsys):
        run([str(tree)])
        assert "Scanned 2 file(s): 1 issue(s) reported (1 warning or error), 0 file(s) could not be linted." in (
            capsys.readouterr().out
        )

    def test_without_strict_issues_do_not_fail(self, tree):
        assert run([str(tree)]) == 0

    def test_strict_fails_when_a_warning_is_reported(self, tree):
        assert run([str(tree), "--strict"]) == 1

    def test_strict_passes_a_clean_tree(self, tree):
        assert run([str(tree / "index.md"), "--strict"]) == 0

    def test_strict_does_not_fail_on_info_only(self, tmp_path, capsys):
        (tmp_path / "a.md").write_text("The PSK is used.\n", encoding="utf-8")
        assert run([str(tmp_path), "--strict"]) == 0
        assert "DOC003" in capsys.readouterr().out

    def test_missing_target_exits_2_with_a_message_on_stderr(self, tmp_path, capsys):
        assert run([str(tmp_path / "nope")]) == 2
        captured = capsys.readouterr()
        assert "Error: Path not found" in captured.err
        assert captured.out == ""

    def test_unsupported_file_exits_2(self, tree, capsys):
        assert run([str(tree / "notes.txt")]) == 2
        assert "Not a Markdown file" in capsys.readouterr().err

    def test_an_unreadable_file_exits_2_even_without_strict(self, tmp_path, capsys):
        (tmp_path / "bad.md").write_bytes(b"\xff\xfe\x00")
        assert run([str(tmp_path)]) == 2
        captured = capsys.readouterr()
        assert "bad.md: Not valid UTF-8" in captured.err
        assert "1 file(s) could not be linted" in captured.out

    def test_exclude_adds_directories_to_skip(self, tree):
        assert run([str(tree), "--strict", "--exclude", "guide"]) == 0

    def test_default_target_is_the_working_directory(self, tree, monkeypatch, capsys):
        monkeypatch.chdir(tree)
        run([])
        assert "guide/setup.md:3:".replace("/", os.sep) in capsys.readouterr().out

    def test_installed_module_runs_as_a_script(self, tree):
        result = subprocess.run(
            [sys.executable, "-m", "py_doc.lint.cli", str(tree), "--strict"], capture_output=True, text=True, check=False
        )
        assert result.returncode == 1
        assert "setup.md:3: warning DOC001" in result.stdout


class TestConfigFile:
    @pytest.fixture
    def docs(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "a.md").write_text("A dtls typo, in order to test.\n", encoding="utf-8")
        return tmp_path

    def write(self, root, text):
        (root / "py-doc.yml").write_text(text, encoding="utf-8")

    def test_without_a_config_the_built_in_policy_applies(self, docs, capsys):
        assert run([str(docs / "docs")]) == 0
        assert "DOC001" in capsys.readouterr().out

    def test_error_severity_fails_even_without_strict(self, docs, capsys):
        self.write(docs, "lint:\n  rules:\n    DOC001: error\n")
        assert run([str(docs / "docs")]) == 1
        assert "error DOC001" in capsys.readouterr().out

    def test_disabled_rule_is_not_reported(self, docs, capsys):
        self.write(docs, "lint:\n  rules:\n    DOC001: off\n")
        assert run([str(docs / "docs"), "--strict"]) == 1  # DOC002 still warns
        out = capsys.readouterr().out
        assert "DOC001" not in out and "DOC002" in out

    def test_all_rules_off_is_clean_under_strict(self, docs, capsys):
        self.write(docs, "lint:\n  rules: {DOC001: off, DOC002: off}\n")
        assert run([str(docs / "docs"), "--strict"]) == 0

    def test_config_is_found_above_a_file_target(self, docs, capsys):
        self.write(docs, "lint:\n  rules: {DOC001: error}\n")
        assert run([str(docs / "docs" / "a.md")]) == 1

    def test_explicit_config_beats_discovery(self, docs, tmp_path, capsys):
        self.write(docs, "lint:\n  rules: {DOC001: error}\n")
        other = tmp_path / "other.yml"
        other.write_text("lint:\n  rules: {DOC001: info}\n", encoding="utf-8")
        assert run([str(docs / "docs"), "--config", str(other)]) == 0

    def test_project_glossary_terms_are_checked(self, docs, capsys):
        (docs / "docs" / "b.md").write_text("We run k8s.\n", encoding="utf-8")
        self.write(docs, "lint:\n  glossary:\n    Kubernetes: [k8s]\n")
        run([str(docs / "docs" / "b.md")])
        assert "k8s" in capsys.readouterr().out

    def test_bad_config_exits_2_with_the_place(self, docs, capsys):
        self.write(docs, "lint:\n  rules: {DOC999: error}\n")
        assert run([str(docs / "docs")]) == 2
        assert "unknown rule 'DOC999'" in capsys.readouterr().err

    def test_exclude_flag_adds_to_the_config(self, docs, capsys):
        self.write(docs, "lint:\n  exclude: [skipme]\n")
        for name in ("skipme", "alsoskip"):
            (docs / "docs" / name).mkdir()
            (docs / "docs" / name / "x.md").write_text("A dtls typo.\n", encoding="utf-8")
        run([str(docs / "docs"), "--exclude", "alsoskip"])
        out = capsys.readouterr().out
        assert "skipme" not in out and "alsoskip" not in out
