"""All logging goes through ctxlogkit, set up once per command. No copies of old logging code."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from fake_engine import install

from py_doc.app import main
from py_doc.runtime import Runtime

SRC = Path(__file__).parent.parent / "src"

# Modules that are command line front ends: they print results and errors for people and programs.
FRONT_ENDS = {
    "app.py", "_cli.py", "cli.py", "slides_cli.py", "tools_cli.py", "template_cli.py", "import_cli.py", "__main__.py", "lint/cli.py",
}  # fmt: skip


def sources():
    return [p for p in SRC.rglob("*.py")]


def test_there_is_no_copy_of_a_logging_module():
    names = {p.stem for p in sources()}
    assert not {"pylogkit", "logging_setup", "logkit"} & names


def test_nothing_imports_colorama_or_configures_logging_itself():
    offenders = []
    for path in sources():
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(import|from)\s+colorama", text, re.M):
            offenders.append(f"{path.name}: colorama")
        if path.name not in ("_logging.py", "report.py") and re.search(r"logging\.basicConfig|setup_logging\(|addHandler\(", text):
            offenders.append(f"{path.name}: configures logging")
    assert offenders == []


def test_library_modules_do_not_print():
    offenders = []
    for path in sources():
        relative = path.relative_to(SRC / "py_doc").as_posix() if "py_doc" in path.parts else path.name
        if relative in FRONT_ENDS or path.parts[-2] in ("pydoc2docx", "pydoc2slides", "pydoclint"):
            continue
        if re.search(r"^\s*print\(", path.read_text(encoding="utf-8"), re.M):
            offenders.append(relative)
    assert offenders == []


@pytest.mark.parametrize(
    "command",
    [["docx"], ["slides"], ["lint"], ["build"], ["migrate"], ["doctor"], ["import", "x"], ["template", "check", "x"], ["template", "show", "x"]]
    + [["tools", action] for action in ("build", "status", "prune", "lock", "save", "load")],
)
def test_every_command_takes_quiet_and_verbose(command, capsys):
    with pytest.raises(SystemExit):
        main([*command, "--help"])
    out = capsys.readouterr().out
    assert "--quiet" in out and "--verbose" in out


def test_tool_output_is_logged_at_debug_and_kept_for_errors(tmp_path, monkeypatch, caplog):
    engine = install(tmp_path, monkeypatch, stdout="first line\nsecond line\n")
    runtime = Runtime("tools:test", docker=engine.docker, platform_name="linux")
    with caplog.at_level(logging.DEBUG, logger="py_doc"):
        runtime.run(["tool"])
    debug = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
    assert "first line" in debug and "second line" in debug
