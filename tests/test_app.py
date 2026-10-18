"""The unified py-doc command: build and the delegated commands."""

from __future__ import annotations

import pytest
from docx_helpers import texts
from py_doc.app import main


pytestmark = pytest.mark.usefixtures("pandoc_runtime")


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

    def test_legacy_build_file_builds_without_a_config(self, project, capsys):
        (project / "deck.yaml").write_text(
            "meta: {title: Deck, version: 2.0.0}\n"
            "cli: {output: out/Deck.pptx, verbose: false, keep-temps: false}\n"
            "entries: [{file: a.md}, {file: b.md, section: Second, heading_offset: 1}]\n",
            encoding="utf-8",
        )
        (project / "paper.yaml").write_text(
            "meta: {title: Paper, version: 0.1.0}\n"
            "cli: {emit-docx: true, output: Paper.docx, plantuml-jar-path: x.jar}\n"
            "entries: [{file: a.md, heading_offset: 0, page_break: false}]\n",
            encoding="utf-8",
        )
        assert main(["build", "--legacy", "deck.yaml"]) == 0
        assert (project / "out" / "Deck-2_0_0.pptx").exists()
        assert main(["build", "--legacy", "paper.yaml"]) == 0
        assert "Alpha" in texts(project / "Paper-0_1_0.docx")
        assert "cli.plantuml-jar-path was left out" in capsys.readouterr().err

    def test_legacy_option_refuses_other_yaml(self, project, capsys):
        assert main(["build", "--legacy", "py-doc.yml"]) == 1
        assert "is not a createdocs build file" in capsys.readouterr().err

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


@pytest.mark.parametrize(
    ("command", "usage", "shown"),
    [
        (["docx"], "usage: py-doc docx", "py-doc docx guide.md -t Template.docx"),
        (["slides"], "usage: py-doc slides", "--split-level 1"),
        (["lint"], "usage: py-doc lint", "py-doc lint docs README.md"),
        (["build"], "usage: py-doc build", "one legacy createdocs build file"),
        (["migrate"], "usage: py-doc migrate", "py-doc migrate docs --check"),
        (["new"], "usage: py-doc new", "py-doc new --scan --start 100"),
        ([], "usage: py-doc ", "`py-doc COMMAND --help`"),
    ],
)
def test_the_help_names_the_command_and_shows_what_it_does(command, usage, shown, capsys):
    with pytest.raises(SystemExit):
        main([*command, "--help"])
    out = capsys.readouterr().out
    assert out.startswith(usage) and shown in out


def test_the_old_commands_keep_their_own_name_in_the_help(capsys):
    from py_doc.cli import run_docx
    from py_doc.slides_cli import run_slides

    for run, name in ((run_docx, "py-doc2docx"), (run_slides, "py-doc2slides")):
        with pytest.raises(SystemExit):
            run(["--help"], legacy=True)
        assert capsys.readouterr().out.startswith(f"usage: {name}")


class TestPipeline:
    def test_lint_errors_stop_the_build_and_strict_stops_on_warnings(self, project, capsys):
        (project / "a.md").write_text("# Alpha\n\n```\nnever closed\n", encoding="utf-8")
        assert main(["build", "alpha", "--lint"]) == 1
        assert "nothing was built" in capsys.readouterr().err and not (project / "build").exists()
        (project / "a.md").write_text("# Alpha\n\nWe run in order to test.\n", encoding="utf-8")
        assert main(["build", "alpha", "--lint"]) == 0
        assert main(["build", "alpha", "--strict"]) == 1

    def test_the_lint_report_and_the_steps_in_the_build_report(self, project):
        import json

        assert main(["build", "alpha", "--lint", "--lint-report", "out/lint.sarif", "--report", "out/report.json"]) == 0
        sarif = json.loads((project / "out" / "lint.sarif").read_text(encoding="utf-8"))
        assert sarif["version"] == "2.1.0" and sarif["runs"][0]["results"][0]["ruleId"] == "DOC002"
        steps = json.loads((project / "out" / "report.json").read_text(encoding="utf-8"))["steps"]
        assert [(s["step"], s["status"]) for s in steps] == [("lint", "ok"), ("documents", "ok"), ("verify", "ok")]

    def test_build_settings_in_py_doc_yml(self, project, capsys):
        with open(project / "py-doc.yml", "a", encoding="utf-8") as file:
            file.write("build: {lint: strict, site: true}\n")
        assert main(["build", "alpha"]) == 1  # strict: the wordy phrase is a warning
        assert main(["build", "alpha", "--no-lint"]) == 1  # then the site: there is no site section
        assert "has no site section" in capsys.readouterr().err
        assert main(["build", "alpha", "--no-lint", "--no-site"]) == 0
