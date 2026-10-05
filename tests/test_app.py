"""The unified py-doc command: build and the delegated commands."""

from __future__ import annotations

import pytest
from docx_helpers import texts
from py_doc.app import main


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("# Alpha\n\nrun in order to test\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Beta\n", encoding="utf-8")
    (tmp_path / "py-doc.yml").write_text(
        "documents:\n  alpha: {sources: [a.md]}\n  beta: {sources: [b.md], outputs: {docx: {}, pptx: {}}}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestBuild:
    def test_builds_every_document(self, project, capsys):
        assert main(["build"]) == 0
        assert texts(project / "build" / "alpha.docx")[0] == "Alpha"
        assert (project / "build" / "beta.docx").exists() and (project / "build" / "beta.pptx").exists()
        assert "2 of 2 document(s) built" in capsys.readouterr().err

    def test_builds_only_the_named_documents(self, project):
        assert main(["build", "beta"]) == 0
        assert not (project / "build" / "alpha.docx").exists()

    def test_format_option_limits_the_formats(self, project):
        assert main(["build", "beta", "-f", "pptx"]) == 0
        assert not (project / "build" / "beta.docx").exists() and (project / "build" / "beta.pptx").exists()

    def test_config_is_found_in_a_parent_folder(self, project, monkeypatch):
        (project / "sub").mkdir()
        monkeypatch.chdir(project / "sub")
        assert main(["build", "alpha"]) == 0
        assert (project / "build" / "alpha.docx").exists()

    def test_explicit_config(self, project, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path.parent)
        assert main(["build", "-c", str(project / "py-doc.yml"), "alpha"]) == 0

    def test_no_config_is_a_clear_error(self, tmp_path, monkeypatch, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        monkeypatch.setattr("py_doc.app.find_config", lambda start: None)
        assert main(["build"]) == 1
        assert "No py-doc.yml found" in capsys.readouterr().err

    def test_unknown_document_is_an_error_before_anything_is_built(self, project, capsys):
        assert main(["build", "alpha", "nope"]) == 1
        assert "Unknown document(s): nope. Defined: alpha, beta" in capsys.readouterr().err
        assert not (project / "build").exists()

    def test_bad_config_is_reported_with_its_place(self, project, capsys):
        (project / "py-doc.yml").write_text("documents:\n  a: {}\n", encoding="utf-8")
        assert main(["build"]) == 1
        assert "documents.a.sources must be a list" in capsys.readouterr().err

    def test_config_without_documents_is_an_error(self, project, capsys):
        (project / "py-doc.yml").write_text("project: {name: x}\n", encoding="utf-8")
        assert main(["build"]) == 1
        assert "defines no documents" in capsys.readouterr().err

    def test_one_failing_document_does_not_stop_the_others(self, project, capsys):
        (project / "a.md").write_bytes(b"caf\xe9\n")
        assert main(["build"]) == 1
        err = capsys.readouterr().err
        assert "alpha:" in err and "not valid UTF-8" in err
        assert "1 of 2 document(s) built, 1 failed" in err
        assert (project / "build" / "beta.docx").exists()

    def test_missing_source_names_the_document(self, project, capsys):
        (project / "b.md").unlink()
        assert main(["build", "beta"]) == 1
        assert "beta: Source for document 'beta' not found" in capsys.readouterr().err

    def test_quiet_hides_progress(self, project, capsys):
        assert main(["build", "alpha", "-q"]) == 0
        assert capsys.readouterr().err == ""


class TestDelegation:
    def test_docx(self, project):
        assert main(["docx", "a.md", "-o", "x.docx"]) == 0
        assert texts(project / "x.docx")[0] == "Alpha"

    def test_slides(self, project):
        assert main(["slides", "a.md"]) == 0
        assert (project / "a.pptx").exists()

    def test_lint_uses_the_project_configuration(self, project, capsys):
        assert main(["lint", "a.md"]) == 0
        assert "DOC002" in capsys.readouterr().out
        (project / "py-doc.yml").write_text("lint:\n  rules: {DOC002: error}\n", encoding="utf-8")
        assert main(["lint", "a.md"]) == 1

    def test_failures_keep_their_exit_status(self, project):
        assert main(["docx", "missing.md"]) == 1

    def test_no_command_is_a_usage_error(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2

    def test_version(self, capsys):
        import py_doc

        with pytest.raises(SystemExit):
            main(["--version"])
        assert capsys.readouterr().out.strip() == f"py-doc {py_doc.__version__}"
