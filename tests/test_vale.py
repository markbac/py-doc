"""Vale as a second engine of py-doc lint (#92 to #95). A fake vale program prints canned JSON."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from fake_vale import alert, install

from py_doc.app import main
from py_doc.lint.config import LintConfig
from py_doc.lint.linter import DocLinter
from py_doc.lint.vale import build_workspace, drop_duplicates, parse_output
from py_doc.lint.vale_config import ValeConfigError, parse_vale
from py_doc.lint.model import LintIssue


@pytest.fixture(autouse=True)
def in_a_temporary_folder(tmp_path, monkeypatch):
    """The .py-doc folder goes under the working folder, so keep it out of the repository."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# A\n\nThis is very good.\n", encoding="utf-8")
    return tmp_path


def lint(project, *extra, capsys=None):
    return main(["lint", str(project / "docs"), *extra])


def test_without_vale_auto_runs_the_builtin_rules_and_says_so(project, monkeypatch, capsys, caplog):
    monkeypatch.setenv("PATH", "/nonexistent")
    assert lint(project) == 0
    assert "Vale is not installed" in caplog.text or "Vale is not installed" in capsys.readouterr().err


def test_a_required_vale_that_is_missing_exits_2(project, monkeypatch, capsys):
    monkeypatch.setenv("PATH", "/nonexistent")
    linter = DocLinter(engine="vale")  # no runtime offered
    with pytest.raises(Exception, match="Vale is not installed"):
        linter.lint_path(project / "docs")


def test_both_engines_give_one_sorted_list(project, tmp_path, monkeypatch, capsys):
    install(tmp_path / "bin", monkeypatch, canned={"a.md": [alert(line=3)]})
    (project / "docs" / "a.md").write_text("# A\n\nWe use lwm2m. This is very good.\n", encoding="utf-8")
    assert lint(project) == 0
    out = capsys.readouterr().out
    lines = [x for x in out.splitlines() if "a.md" in x]
    assert "DOC001" in lines[0] and "PyDoc.WeaselWords" in lines[1]
    assert ":3:3:" in lines[1]  # Vale gives the column


def test_builtin_engine_does_not_call_vale(project, tmp_path, monkeypatch):
    log = install(tmp_path / "bin", monkeypatch)
    assert lint(project, "--engine", "builtin") == 0
    assert not log.exists()


def test_vale_errors_fail_and_strict_fails_on_warnings(project, tmp_path, monkeypatch):
    install(tmp_path / "bin", monkeypatch, canned={"a.md": [alert(severity="warning", line=3)]})
    assert lint(project) == 0
    assert lint(project, "--strict") == 1
    install(tmp_path / "bin2", monkeypatch, canned={"a.md": [alert(severity="error", line=3)]})
    assert lint(project) == 1


def test_a_vale_crash_is_a_file_error_not_a_clean_result(project, tmp_path, monkeypatch, capsys):
    install(tmp_path / "bin", monkeypatch, crash="E100 broken config")
    assert lint(project) == 2
    assert "broken config" in capsys.readouterr().err


def test_old_vale_is_refused(project, tmp_path, monkeypatch, capsys):
    install(tmp_path / "bin", monkeypatch, version="2.30.0")
    assert lint(project) == 2
    assert "too old" in capsys.readouterr().err


def test_duplicates_of_the_builtin_rules_are_dropped():
    a = Path("a.md")
    builtin = [LintIssue(a, 3, "DOC001", "Glossary", "x")]
    vale = [LintIssue(a, 3, "PyDoc.Terms", "PyDoc", "y"), LintIssue(a, 4, "PyDoc.Terms", "PyDoc", "z")]
    assert [i.line for i in drop_duplicates(vale, builtin)] == [4]


def test_alerts_are_mapped(tmp_path):
    f = tmp_path / "a.md"
    text = json.dumps({str(f): [alert(check="Style.Rule", severity="suggestion", action={"Name": "replace", "Params": ["to"]})]})
    (issue,) = parse_output(text, [f])
    assert (issue.rule, issue.category, issue.severity, issue.suggestion, issue.column) == ("Style.Rule", "Style", "info", "to", 3)
    with pytest.raises(Exception, match="not JSON"):
        parse_output("oops", [f])


def test_generated_files_follow_the_definition(tmp_path):
    settings = parse_vale(
        {
            "packages": ["write-good"], "spelling": "en-GB", "min_alert_level": "warning",
            "rules": {"PyDoc.SentenceLength": {"level": "error", "max": 20}, "PyDoc.PassiveVoice": "off", "write-good.Weasel": "error"},
            "terms": {"Kubernetes": ["k8s"]},
            "avoid": [{"pattern": r"\bsimply\b", "message": "No.", "level": "error"}],
        },
        tmp_path,
    )
    workspace = build_workspace(settings, LintConfig(), tmp_path / "vale")
    ini = workspace.ini.read_text()
    assert "MinAlertLevel = warning" in ini and "Packages = write-good" in ini
    assert "PyDoc.PassiveVoice = NO" in ini and "write-good.Weasel = error" in ini
    sentence = yaml.safe_load((tmp_path / "vale/styles/PyDoc/SentenceLength.yml").read_text())
    assert sentence["max"] == 20
    assert sentence["message"] == "Sentence is %d words long. Try to keep it under 20."  # Vale gives the count as a number
    assert yaml.safe_load((tmp_path / "vale/styles/PyDoc/Terms.yml").read_text())["swap"]["k8s"] == "Kubernetes"
    assert yaml.safe_load((tmp_path / "vale/styles/PyDoc/Terms.yml").read_text())["swap"]["lwm2m"] == "LwM2M"
    assert yaml.safe_load((tmp_path / "vale/styles/PyDoc/Avoid1.yml").read_text())["level"] == "error"
    assert "colour" in yaml.safe_load((tmp_path / "vale/styles/PyDoc/Spelling.yml").read_text())["swap"].values()
    assert "Kubernetes" in (tmp_path / "vale/styles/config/vocabularies/PyDoc/accept.txt").read_text()
    assert (tmp_path / "vale/.gitignore").read_text() == "*\n"


def test_every_bundled_rule_file_is_valid_yaml_with_an_extends():
    from py_doc.lint.vale import _bundled

    rules = {n: yaml.safe_load(t) for n, t in _bundled() if n.endswith(".yml")}
    assert len(rules) >= 9 and all("extends" in r and "message" in r for r in rules.values())


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"rules": {"PyDoc.Typo": "off"}}, "lint.vale.rules.PyDoc.Typo"),
        ({"rules": {"PyDoc.PassiveVoice": "loud"}}, "must be one of"),
        ({"rules": {"PyDoc.SentenceLength": {"max": 0}}}, "whole number"),
        ({"avoid": [{"pattern": "("}], "}": 1}, "unknown key"),
        ({"avoid": [{"pattern": "("}]}, "regular expression"),
        ({"enabled": "maybe"}, "lint.vale.enabled"),
        ({"bogus": 1}, "unknown key 'bogus'"),
        ({"rules": {"write-good.Weasel": {"max": 3}}}, "only a level"),
    ],
)
def test_a_bad_definition_names_its_place(data, message, tmp_path):
    with pytest.raises(ValeConfigError, match=message):
        parse_vale(data, tmp_path)


def test_a_broken_definition_fails_with_status_2_before_vale_runs(project, tmp_path, monkeypatch, capsys):
    log = install(tmp_path / "bin", monkeypatch)
    (project / "py-doc.yml").write_text("lint:\n  vale:\n    rules:\n      PyDoc.Nope: off\n", encoding="utf-8")
    assert lint(project) == 2
    assert "lint.vale.rules.PyDoc.Nope" in capsys.readouterr().err
    assert not log.exists()


def test_rules_files_merge_in_order_and_inline_wins(project, tmp_path):
    (project / "base.yml").write_text("rules:\n  PyDoc.PassiveVoice: error\n  PyDoc.WeaselWords: error\n", encoding="utf-8")
    (project / "team.yml").write_text("rules:\n  PyDoc.WeaselWords: off\n", encoding="utf-8")
    settings = parse_vale({"rules_file": ["base.yml", "team.yml"], "rules": {"PyDoc.PassiveVoice": "warning"}}, project)
    assert settings.rules["PyDoc.PassiveVoice"].level == "warning"
    assert settings.rules["PyDoc.WeaselWords"].off


def test_ignore_and_own_config(project, tmp_path, monkeypatch):
    log = install(tmp_path / "bin", monkeypatch)
    (project / "py-doc.yml").write_text("lint:\n  vale:\n    ignore: ['a.md']\n", encoding="utf-8")
    assert lint(project) == 0
    assert not log.exists() or "a.md" not in log.read_text()
    (project / "own.ini").write_text("StylesPath = s\n", encoding="utf-8")
    (project / "py-doc.yml").write_text("lint:\n  vale:\n    config: own.ini\n", encoding="utf-8")
    assert lint(project) == 0
    assert "own.ini" in log.read_text()


def test_show_config_check_engines_and_sync(project, tmp_path, monkeypatch, capsys):
    log = install(tmp_path / "bin", monkeypatch)
    (project / "py-doc.yml").write_text("lint:\n  vale:\n    packages: [write-good]\n", encoding="utf-8")
    assert lint(project, "--show-vale-config") == 0
    assert "BasedOnStyles = PyDoc, write-good" in capsys.readouterr().out
    assert lint(project, "--check-engines") == 0
    assert "vale: 3.9.1" in capsys.readouterr().out
    assert lint(project) == 2  # packages not downloaded
    assert "py-doc lint --sync" in capsys.readouterr().err
    assert lint(project, "--sync") == 0
    assert "sync" in log.read_text()


def test_the_schema_accepts_a_full_definition():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((Path(__file__).parent.parent / "src/py_doc/lint/vale.schema.json").read_text())
    sample = yaml.safe_load(
        "enabled: auto\nbinary: vale\nmin_alert_level: suggestion\npackages: [write-good]\nspelling: en-GB\n"
        "rules: {PyDoc.SentenceLength: {level: warning, max: 30}, PyDoc.PassiveVoice: false, write-good.Weasel: error}\n"
        "terms: {Kubernetes: [k8s]}\navoid: [{pattern: x, level: warning}]\nignore: [a.md]\n"
    )
    jsonschema.validate(sample, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"enabled": "perhaps"}, schema)


@pytest.mark.skipif(shutil.which("vale") is None, reason="Vale is not installed")
def test_end_to_end_with_the_real_vale(project, capsys):
    (project / "docs" / "a.md").write_text("# A\n\nThis is very good. TODO: finish.\n\n```\nvery TODO\n```\n", encoding="utf-8")
    assert lint(project, "--engine", "vale") == 0
    out = capsys.readouterr().out
    assert "PyDoc.WeaselWords" in out and "PyDoc.Placeholders" in out
    assert out.count("PyDoc.Placeholders") == 1  # the code block is not prose


def test_the_placeholder_words_are_not_in_the_accepted_vocabulary(project, tmp_path):
    from py_doc.lint.config import LintConfig
    from py_doc.lint.vale import build_workspace

    folder = tmp_path / "vale"
    config = LintConfig()
    build_workspace(config.vale, config, folder)
    accepted = (folder / "styles" / "config" / "vocabularies" / "PyDoc" / "accept.txt").read_text(encoding="utf-8").split()
    assert "API" in accepted and not {"TODO", "FIXME", "TBD"} & set(accepted)


def test_rules_turned_off_in_the_config_are_not_written_for_vale(tmp_path):
    from dataclasses import replace

    from py_doc.lint.config import RULE_ACRONYM, RULE_GLOSSARY, RULE_REDUNDANT, LintConfig
    from py_doc.lint.vale import build_workspace

    config = replace(LintConfig(), disabled_rules=frozenset({RULE_GLOSSARY, RULE_REDUNDANT, RULE_ACRONYM}))
    build_workspace(config.vale, config, tmp_path)
    written = {path.stem for path in (tmp_path / "styles" / "PyDoc").glob("*.yml")}
    assert not written & {"Terms", "Wordy", "Redundant", "Acronyms"}
    assert "WeaselWords" in written
