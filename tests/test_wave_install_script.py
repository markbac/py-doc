"""scripts/install-wave-widget.ps1, the Wave step of update.ps1 (W-41 to W-46), against a temporary Wave folder."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from py_doc import wave

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "install-wave-widget.ps1"
UPDATE = ROOT / "scripts" / "update.ps1"
POWERSHELL = shutil.which("pwsh") or (shutil.which("powershell") if os.name == "nt" else None)

needs_powershell = pytest.mark.skipif(not POWERSHELL, reason="needs PowerShell")


def run(config: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
         "-Python", sys.executable, "-ConfigDir", str(config)],
        capture_output=True, text=True, timeout=300,
    )  # fmt: skip


def saved(config: Path) -> dict:
    return json.loads((config / "widgets.json").read_text(encoding="utf-8"))


@needs_powershell
def test_the_first_run_adds_the_widget_and_the_second_changes_nothing(tmp_path):
    first = run(tmp_path)
    assert first.returncode == 0 and "widget added" in first.stdout, first.stdout + first.stderr
    assert saved(tmp_path) == {wave.WIDGET_NAME: wave.widget()}
    written = (tmp_path / "widgets.json").stat().st_mtime_ns

    again = run(tmp_path)
    assert again.returncode == 0 and "up to date" in again.stdout, again.stdout + again.stderr
    assert (tmp_path / "widgets.json").stat().st_mtime_ns == written


@needs_powershell
def test_a_changed_definition_is_updated_and_other_widgets_kept(tmp_path):
    old = {**wave.widget(), "label": "an older label"}
    others = {"dua": {"icon": "brands@linux", "label": "dua", "blockdef": {"meta": {"view": "term", "cmd": "dua"}}}}
    (tmp_path / "widgets.json").write_text(json.dumps({**others, wave.WIDGET_NAME: old}), encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 0 and "updated" in result.stdout, result.stdout + result.stderr
    assert saved(tmp_path) == {**others, wave.WIDGET_NAME: wave.widget()}


@needs_powershell
def test_no_wave_is_a_note_and_the_update_carries_on(tmp_path):
    result = run(tmp_path / "no-wave-here")
    assert result.returncode == 0 and "not installed" in result.stdout
    assert not (tmp_path / "no-wave-here").exists()


@needs_powershell
def test_a_widgets_file_that_is_not_json_is_left_untouched(tmp_path):
    (tmp_path / "widgets.json").write_text("{ broken", encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 1 and "cannot be read" in result.stdout, result.stdout + result.stderr
    assert (tmp_path / "widgets.json").read_text(encoding="utf-8") == "{ broken"


def test_update_has_a_skip_option_and_runs_the_step_before_docker():
    text = UPDATE.read_text(encoding="utf-8")
    assert "[switch]$NoWave" in text and ".PARAMETER NoWave" in text and "(-NoWave)" in text
    assert text.index("install-wave-widget.ps1') -Python") < text.index('Write-Step "Docker"')
    assert text.index('Write-Step "Wave Terminal"') > text.index('Write-Step "VS Code extension"')
