"""py-doc stats, check and diff."""

from __future__ import annotations

import json
import subprocess

import pytest
from py_doc.analysis import diff_markdown, sections
from py_doc.analysis.stats import text_stats
from py_doc.app import main


class TestStats:
    def test_counts_prose_and_blocks(self):
        text = "---\ntitle: x y z\n---\n\n# Title\n\nOne two [three](a.md).\n\n```\nnot words here\n```\n\n| A | B |\n|---|---|\n| c | d |\n\n![alt](p.png)\n"
        stats = text_stats(text)
        assert (stats.words, stats.headings, stats.code_blocks, stats.tables, stats.images, stats.links) == (9, 1, 1, 1, 1, 1)  # the alt text counts

    def test_the_command_reports_each_document_and_the_total(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "a.md").write_text("# A\n\nOne two.\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B\n\nThree.\n", encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text("documents:\n  guide: {sources: [a.md, b.md]}\n  notes: {sources: [b.md]}\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["stats", "--format", "json", "--lint"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data["items"]["guide"]["words"] == 5 and data["items"]["notes"]["headings"] == 1
        assert data["total"]["words"] == 7 and "lint_issues" in data["total"]


class TestCheck:
    def test_missing_sources_and_templates_fail_without_building(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "a.md").write_text("# A\n\nFine.\n", encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text(
            "documents:\n  guide: {sources: [a.md, gone.md], outputs: {docx: {template: t.docx}}}\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        assert main(["check", "--engine", "builtin"]) == 1
        err = capsys.readouterr().err
        assert "source gone.md is not there" in err and "the docx template t.docx is not there" in err

    def test_a_clean_project_passes_and_strict_fails_on_warnings(self, tmp_path, monkeypatch):
        (tmp_path / "a.md").write_text("# A\n\nWe do it in order to win.\n", encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text("documents:\n  guide: {sources: [a.md]}\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["check", "--engine", "builtin"]) == 0
        assert main(["check", "--engine", "builtin", "--strict"]) == 1
        assert main(["check", "--no-lint", "--strict"]) == 0


OLD = """# Guide

Intro text.

## Install

Run the installer.

## Use

Open it.

## Old part

Gone soon.
"""

NEW = """# Guide

Intro   text.

## Use

Open it, then close it.

## Setup

Run the installer.

## New part

Brand new.
"""


class TestDiff:
    def test_sections_are_named_by_their_heading_path(self):
        assert [s.title for s in sections("Before.\n\n# A\n\n## B\n\nx\n\n# C\n")] == ["(preamble)", "A", "A > B", "C"]

    def test_section_changes_not_line_changes(self):
        changes = {(c.kind, (c.new or c.old).title) for c in diff_markdown(OLD, NEW)}
        assert changes == {
            ("changed", "Guide > Use"),
            ("renamed", "Guide > Setup"),
            ("added", "Guide > New part"),
            ("removed", "Guide > Old part"),
        }  # rewrapping the intro is no change, and Use moving above Setup comes from the rename

    def test_a_moved_section(self):
        old = "# A\n\none\n\n# B\n\ntwo\n\n# C\n\nthree\n"
        new = "# C\n\nthree\n\n# A\n\none\n\n# B\n\ntwo\n"
        assert [(c.kind, c.new.title) for c in diff_markdown(old, new)] == [("moved", "C")]

    def test_words_added_and_removed(self):
        (change,) = diff_markdown("# A\n\none two three\n", "# A\n\none four three five\n")
        assert (change.kind, change.words_added, change.words_removed) == ("changed", 2, 1)

    def test_two_files(self, tmp_path, capsys):
        (tmp_path / "old.md").write_text(OLD, encoding="utf-8")
        (tmp_path / "new.md").write_text(NEW, encoding="utf-8")
        assert main(["diff", str(tmp_path / "old.md"), str(tmp_path / "new.md"), "--exit-code"]) == 1
        out = capsys.readouterr().out
        assert "~ renamed  Guide > Install -> Guide > Setup" in out and "+ added    Guide > New part" in out

    def test_against_a_git_revision(self, tmp_path, monkeypatch, capsys):
        git = lambda *args: subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: E731
        if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
            pytest.skip("git is not installed")
        git("init", "-q")
        (tmp_path / "a.md").write_text(OLD, encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text("documents:\n  guide: {sources: [a.md]}\n", encoding="utf-8")
        git("add", ".")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "one")
        (tmp_path / "a.md").write_text(NEW, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert main(["diff", "--rev", "HEAD", "--format", "json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert {c["kind"] for c in data["a.md"]} == {"changed", "renamed", "added", "removed"}
