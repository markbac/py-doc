"""Integration tests for the py-doc2docx command line interface."""

from __future__ import annotations

import subprocess
import sys

import pytest
from docx import Document
from docx_helpers import texts
from pydoc2docx.cli import main


def run_cli(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["py-doc2docx", *args])
    main()


@pytest.fixture
def md_tree(tmp_path):
    """docs/ with a root file, a nested file and a non-Markdown file."""
    root = tmp_path / "docs"
    (root / "guide").mkdir(parents=True)
    (root / "index.md").write_text("# Index\n", encoding="utf-8")
    (root / "guide" / "setup.md").write_text("# Setup\n\n- Step\n", encoding="utf-8")
    (root / "notes.txt").write_text("not markdown", encoding="utf-8")
    return root


class TestFileMode:
    def test_default_output_is_next_to_input(self, tmp_path, monkeypatch):
        src = tmp_path / "spec.md"
        src.write_text("# Spec\n", encoding="utf-8")
        run_cli(monkeypatch, str(src))
        assert texts(tmp_path / "spec.docx") == ["Spec"]

    def test_explicit_output_path(self, tmp_path, monkeypatch):
        src = tmp_path / "spec.md"
        src.write_text("# Spec\n", encoding="utf-8")
        run_cli(monkeypatch, str(src), "-o", str(tmp_path / "out" / "custom.docx"))
        assert texts(tmp_path / "out" / "custom.docx") == ["Spec"]
        assert not (tmp_path / "spec.docx").exists()

    def test_template_option_is_applied(self, tmp_path, monkeypatch):
        template = tmp_path / "template.docx"
        doc = Document()
        doc.core_properties.title = "Corporate template"
        doc.save(str(template))
        src = tmp_path / "spec.md"
        src.write_text("# Spec\n", encoding="utf-8")
        run_cli(monkeypatch, str(src), "-t", str(template))
        assert Document(str(tmp_path / "spec.docx")).core_properties.title == "Corporate template"

    def test_template_body_is_removed_unless_keep_template_body_is_given(self, tmp_path, monkeypatch):
        template = tmp_path / "template.docx"
        doc = Document()
        doc.add_paragraph("Template boilerplate")
        doc.save(str(template))
        src = tmp_path / "spec.md"
        src.write_text("# Spec\n", encoding="utf-8")
        run_cli(monkeypatch, str(src), "-t", str(template))
        assert texts(tmp_path / "spec.docx") == ["Spec"]
        run_cli(monkeypatch, str(src), "-t", str(template), "--keep-template-body", "-o", str(tmp_path / "kept.docx"))
        assert texts(tmp_path / "kept.docx") == ["Template boilerplate", "Spec"]

    def test_invalid_utf8_input_exits_with_status_1_and_no_traceback(self, tmp_path, monkeypatch, capsys):
        src = tmp_path / "spec.md"
        src.write_bytes(b"caf\xe9\n")
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, str(src))
        assert exc.value.code == 1
        assert "not valid UTF-8" in capsys.readouterr().out
        assert not (tmp_path / "spec.docx").exists()

    def test_missing_template_exits_with_status_1_and_writes_nothing(self, tmp_path, monkeypatch, capsys):
        src = tmp_path / "spec.md"
        src.write_text("# Spec\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, str(src), "-t", str(tmp_path / "missing.docx"))
        assert exc.value.code == 1
        assert "template not found" in capsys.readouterr().out.lower()
        assert not (tmp_path / "spec.docx").exists()

    def test_allow_missing_template_flag_falls_back(self, tmp_path, monkeypatch):
        src = tmp_path / "spec.md"
        src.write_text("# Spec\n", encoding="utf-8")
        run_cli(monkeypatch, str(src), "-t", str(tmp_path / "missing.docx"), "--allow-missing-template")
        assert texts(tmp_path / "spec.docx") == ["Spec"]

    def test_missing_input_exits_with_status_1(self, tmp_path, monkeypatch, capsys):
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch, str(tmp_path / "nope.md"))
        assert exc.value.code == 1
        assert "not found" in capsys.readouterr().out.lower()

    def test_missing_argument_exits_with_usage_error(self, monkeypatch):
        with pytest.raises(SystemExit) as exc:
            run_cli(monkeypatch)
        assert exc.value.code == 2

    def test_module_entry_point_prints_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "pydoc2docx.cli", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "Markdown" in result.stdout


class TestDirectoryMode:
    def test_converts_markdown_files_in_place_by_default(self, md_tree, monkeypatch):
        run_cli(monkeypatch, str(md_tree))
        assert texts(md_tree / "index.docx") == ["Index"]
        assert texts(md_tree / "guide" / "setup.docx") == ["Setup", "Step"]

    def test_output_directory_mirrors_input_structure(self, md_tree, tmp_path, monkeypatch):
        out = tmp_path / "dist"
        run_cli(monkeypatch, str(md_tree), "-o", str(out))
        assert texts(out / "index.docx") == ["Index"]
        assert texts(out / "guide" / "setup.docx") == ["Setup", "Step"]

    def test_non_markdown_files_are_ignored(self, md_tree, tmp_path, monkeypatch):
        out = tmp_path / "dist"
        run_cli(monkeypatch, str(md_tree), "-o", str(out))
        assert not list(out.rglob("notes*"))
