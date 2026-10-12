"""py-doc init: a new project that loads, lints and builds, and never a replaced file."""

from __future__ import annotations

import argparse

import pytest

from py_doc.app import main
from py_doc.config import load_config
from py_doc.errors import ConversionError, EnvironmentProblem
from py_doc.init import IGNORED, Choices, build_parser, choose, make_project


def _no_container():
    raise EnvironmentProblem("Docker is not running")


def test_a_plain_project_loads_and_builds_one_document(tmp_path):
    written = make_project(tmp_path, Choices("Pump"), runtime=_no_container)
    assert {p.relative_to(tmp_path).as_posix() for p in written} == {"py-doc.yml", "docs/overview.md", ".gitignore"}
    config = load_config(tmp_path / "py-doc.yml")
    assert config.name == "Pump" and list(config.documents) == ["overview"] and config.site is None
    assert (tmp_path / "docs" / "overview.md").read_text(encoding="utf-8").startswith("---\ntitle: Pump overview\n")


def test_every_option_adds_its_part(tmp_path):
    make_project(tmp_path, Choices("Pump", site="mkdocs", c4=True), runtime=_no_container)
    config = load_config(tmp_path / "py-doc.yml")
    assert list(config.documents) == ["overview", "architecture"]
    assert config.documents["architecture"].sources[1].structurizr is not None
    assert (tmp_path / "architecture" / "workspace.dsl").read_text(encoding="utf-8").startswith('workspace "Pump"')
    assert config.site.engine == "mkdocs" and (tmp_path / "site" / "mkdocs.yml").is_file()


def test_templates_need_the_container_and_are_skipped_without_it(tmp_path, caplog):
    make_project(tmp_path, Choices("Pump", templates=True), runtime=_no_container)
    config = load_config(tmp_path / "py-doc.yml")
    assert config.outputs["docx"].template == (tmp_path / "templates" / "reference.docx").resolve()
    assert not (tmp_path / "templates").exists() and "templates were not written" in caplog.text


def test_a_project_folder_is_refused_and_left_as_it_is(tmp_path):
    (tmp_path / "py-doc.yml").write_text("project: {name: Old}\n", encoding="utf-8")
    with pytest.raises(ConversionError, match="already a py-doc project|already there"):
        make_project(tmp_path, Choices("New"), runtime=_no_container)
    assert (tmp_path / "py-doc.yml").read_text(encoding="utf-8") == "project: {name: Old}\n"
    assert not (tmp_path / "docs").exists()


def test_files_that_are_there_are_kept(tmp_path, caplog):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "overview.md").write_text("mine\n", encoding="utf-8")
    written = make_project(tmp_path, Choices("Pump"), runtime=_no_container)
    assert (tmp_path / "docs" / "overview.md").read_text(encoding="utf-8") == "mine\n"
    assert tmp_path / "docs" / "overview.md" not in written and "Kept" in caplog.text


def test_gitignore_gets_only_the_missing_lines(tmp_path):
    (tmp_path / ".gitignore").write_text("*.pyc\nbuild/\n", encoding="utf-8")
    make_project(tmp_path, Choices("Pump"), runtime=_no_container)
    lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines[:2] == ["*.pyc", "build/"] and lines.count("build/") == 1
    assert set(IGNORED) <= set(lines)


def _args(*argv):
    return build_parser().parse_args(list(argv))


def test_choices_come_from_options_then_answers_then_defaults(tmp_path):
    answers = iter(["", "STARLIGHT", "y", ""])
    chosen = choose(_args(str(tmp_path)), tmp_path, lambda prompt: next(answers))
    assert chosen == Choices(tmp_path.resolve().name, "starlight", True, False)
    assert choose(_args(str(tmp_path), "--name", "X", "--c4"), tmp_path, None) == Choices("X", None, True, False)


def test_a_wrong_site_answer_is_asked_again(tmp_path):
    answers = iter(["Name", "hugo", "mkdocs", "n", "n"])
    assert choose(_args(str(tmp_path)), tmp_path, lambda prompt: next(answers)).site == "mkdocs"


def test_the_command_writes_the_project_and_the_next_steps(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("py_doc.init.connect", _no_container)
    assert main(["init", str(tmp_path / "new"), "--name", "Pump", "--site", "none", "-y"]) == 0
    out = capsys.readouterr().out
    assert "written" in out and "py-doc build" in out and "py-doc site build" not in out
    assert main(["init", str(tmp_path / "new"), "-y"]) == 1
    assert "already there" in capsys.readouterr().err


def test_the_new_project_lints_clean(tmp_path, monkeypatch, capsys):
    make_project(tmp_path, Choices("Pump", c4=True), runtime=_no_container)
    monkeypatch.chdir(tmp_path)
    assert main(["lint", "docs", "--strict"]) == 0
    assert "0 issue(s)" in capsys.readouterr().out


def test_parser_defaults(tmp_path):
    assert isinstance(_args(), argparse.Namespace) and _args().c4 is None and _args().templates is None
