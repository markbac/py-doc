"""scripts/install-vscode-extension.ps1 installs the VS Code extension once, and again only when it changed.

It runs against a fake VS Code command line, so it needs PowerShell and Node.js (npm), as GitHub's runners
have. It builds the real extension each time it installs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "install-vscode-extension.ps1"
POWERSHELL = shutil.which("pwsh") or (shutil.which("powershell") if os.name == "nt" else None)
VERSION = json.loads((ROOT / "editors" / "vscode" / "package.json").read_text(encoding="utf-8"))["version"]

pytestmark = [
    pytest.mark.skipif(not POWERSHELL or not shutil.which("npm"), reason="needs PowerShell and Node.js (npm)"),
    pytest.mark.timeout(900),  # each install builds the extension (npm ci, vsce): minutes on a Windows runner
]

FAKE = """
import os, sys
state, log = os.environ["FAKE_CODE_STATE"], os.environ["FAKE_CODE_LOG"]
if sys.argv[1] == "--list-extensions":
    if os.path.exists(state):
        print(open(state).read().strip())
elif sys.argv[1] == "--install-extension":
    open(log, "a").write(" ".join(os.path.basename(a) for a in sys.argv[1:]) + "\\n")
    name = os.path.basename(sys.argv[2])[: -len(".vsix")]
    open(state, "w").write("py-doc.vscode-py-doc-preview@" + name.rsplit("-", 1)[1] + "\\n")
"""


@pytest.fixture
def code(tmp_path) -> Path:
    """A fake VS Code command line: it lists what it was given to install, and logs each install."""
    (tmp_path / "fake_code.py").write_text(FAKE, encoding="utf-8")
    if os.name == "nt":
        command = tmp_path / "code.cmd"
        command.write_text(f'@"{sys.executable}" "{tmp_path / "fake_code.py"}" %*\n', encoding="utf-8")
    else:
        command = tmp_path / "code"
        command.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{tmp_path / "fake_code.py"}" "$@"\n', encoding="utf-8")
        command.chmod(0o755)
    return command


def run(tmp_path, *arguments):
    environment = {**os.environ, "FAKE_CODE_STATE": str(tmp_path / "state"), "FAKE_CODE_LOG": str(tmp_path / "log")}
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-StateFile", str(tmp_path / "hash"), *arguments],
        capture_output=True, text=True, env=environment, timeout=600,
    )  # fmt: skip


def installs(tmp_path) -> list[str]:
    log = tmp_path / "log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_it_installs_once_then_only_when_the_extension_changed(tmp_path, code):
    first = run(tmp_path, "-Code", str(code))
    assert first.returncode == 0, first.stdout + first.stderr
    assert "it is not installed" in first.stdout
    assert installs(tmp_path) == [f"--install-extension vscode-py-doc-preview-{VERSION}.vsix --force"]
    assert len((tmp_path / "hash").read_text(encoding="utf-8").strip()) == 64

    again = run(tmp_path, "-Code", str(code))
    assert again.returncode == 0 and "up to date" in again.stdout, again.stdout + again.stderr
    assert len(installs(tmp_path)) == 1, "nothing changed, so nothing is installed"

    (tmp_path / "hash").write_text("0" * 64, encoding="utf-8")  # as if a file of the extension had changed
    changed = run(tmp_path, "-Code", str(code))
    assert changed.returncode == 0 and "its files changed" in changed.stdout, changed.stdout + changed.stderr
    assert len(installs(tmp_path)) == 2


def test_another_version_installed_is_replaced(tmp_path, code):
    (tmp_path / "state").write_text("py-doc.vscode-py-doc-preview@0.0.1\n", encoding="utf-8")
    result = run(tmp_path, "-Code", str(code))
    assert result.returncode == 0 and f"0.0.1 is installed and this checkout has {VERSION}" in result.stdout


def test_a_code_that_is_not_there_is_a_failure_with_the_reason(tmp_path):
    result = run(tmp_path, "-Code", str(tmp_path / "nowhere" / "code.cmd"))
    assert result.returncode == 1 and "which is not there" in result.stdout
