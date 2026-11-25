"""Wave Terminal: the preview in a Wave pane (W-01 to W-06), the widget (W-11 to W-14) and doctor (W-21 to W-24)."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from py_doc import tools_cli, wave
from py_doc.app import main
from py_doc.preview_cli import STOP, preview

WAVE = {"TERM_PROGRAM": "waveterm", "WAVETERM": "C:/Wave/Wave.exe", "WAVETERM_VERSION": "0.12.1", "WAVETERM_TABID": "tab-1"}  # fmt: skip
ADDRESS = "http://127.0.0.1:5123/"


class FakeWsh:
    """Records each wsh command; answers ``created block block:N`` unless told to fail."""

    def __init__(self, fail: bool = False, fail_replace: bool = False, missing: bool = False):
        self.calls: list[list[str]] = []
        self.fail, self.fail_replace, self.missing = fail, fail_replace, missing

    def which(self, name: str) -> str | None:
        return None if self.missing else f"/wave/bin/{name}"

    def run(self, command, **kwargs):
        self.calls.append(list(command))
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 1 if self.fail else 0, "wsh v0.12.1\n", "")
        if self.fail or (self.fail_replace and "-r" in command):
            return subprocess.CompletedProcess(command, 1, "", "error: block not found\n")
        return subprocess.CompletedProcess(command, 0, f"created block block:{len(self.calls)}\n", "")


def show(fake, env, tmp_path, browser=None, **kw):
    opened = []
    result = wave.show(ADDRESS, env=env, run=fake.run, which=fake.which, browser=browser or opened.append,
                       state_dir=tmp_path, **kw)  # fmt: skip
    return result, opened


# --- W-01, W-02, W-06: when the pane opens -----------------------------------------------------


def test_the_wave_option_opens_a_pane_with_wsh_web_open(tmp_path):
    fake = FakeWsh()
    result, browser = show(fake, {}, tmp_path, wave=True)
    assert result.where == "wave" and fake.calls == [["/wave/bin/wsh", "web", "open", ADDRESS]]
    assert browser == []


def test_outside_wave_nothing_changes(tmp_path):
    fake = FakeWsh()
    result, browser = show(fake, {"TERM_PROGRAM": "vscode"}, tmp_path)
    assert result.where == "browser" and browser == [ADDRESS] and fake.calls == []


def test_inside_wave_a_plain_watch_opens_the_pane(tmp_path):
    fake = FakeWsh()
    result, browser = show(fake, WAVE, tmp_path)
    assert result.where == "wave" and fake.calls[0][:3] == ["/wave/bin/wsh", "web", "open"] and browser == []


@pytest.mark.parametrize("env, wanted", [({**WAVE, "PY_DOC_NO_WAVE": "1"}, None), (WAVE, False)])
def test_the_opt_out_keeps_the_browser(tmp_path, env, wanted):
    fake = FakeWsh()
    result, browser = show(fake, env, tmp_path, wave=wanted)
    assert result.where == "browser" and browser == [ADDRESS] and fake.calls == []


def test_no_open_shows_it_nowhere(tmp_path):
    fake = FakeWsh()
    result, browser = show(fake, WAVE, tmp_path, open_browser=False)
    assert result.where == "nowhere" and browser == [] and fake.calls == []


def test_wave_is_found_by_either_variable():
    assert wave.inside_wave({"TERM_PROGRAM": "waveterm"}) and wave.inside_wave({"WAVETERM": "x"})
    assert not wave.inside_wave({"TERM_PROGRAM": "WezTerm"})


# --- W-03: one pane, replaced ------------------------------------------------------------------


def test_the_next_preview_in_the_tab_replaces_the_pane(tmp_path):
    fake = FakeWsh()
    show(fake, WAVE, tmp_path)
    show(fake, WAVE, tmp_path)
    assert fake.calls[1] == ["/wave/bin/wsh", "web", "open", "-r", "block:1", ADDRESS]


def test_a_pane_that_was_closed_is_opened_again(tmp_path):
    fake = FakeWsh()
    show(fake, WAVE, tmp_path)
    fake.fail_replace = True
    result, _ = show(fake, WAVE, tmp_path)
    assert result.where == "wave" and fake.calls[-1] == ["/wave/bin/wsh", "web", "open", ADDRESS]


def test_another_tab_gets_a_pane_of_its_own(tmp_path):
    fake = FakeWsh()
    show(fake, WAVE, tmp_path)
    show(fake, {**WAVE, "WAVETERM_TABID": "tab-2"}, tmp_path)
    assert "-r" not in fake.calls[1]


def test_moving_the_preview_to_another_file_does_not_open_a_second_pane(tmp_path, monkeypatch):
    fake = FakeWsh()
    monkeypatch.setattr(wave, "inside_wave", lambda env=None: True)
    monkeypatch.setattr(wave.shutil, "which", fake.which)
    monkeypatch.setattr(wave.subprocess, "run", fake.run)
    monkeypatch.setattr(wave.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(wave.webbrowser, "open", lambda address: pytest.fail("the browser opened"))
    first, second = tmp_path / "a.md", tmp_path / "b.md"
    first.write_text("# A\n", encoding="utf-8")
    second.write_text("# B\n", encoding="utf-8")
    requests: queue.Queue = queue.Queue()
    built = []

    def build(kind, source, output):
        built.append(source.name)
        output.write_text("<html><body>ok</body></html>", encoding="utf-8")
        if source == first:
            requests.put((second, "document"))
        else:
            requests.put(STOP)

    done = threading.Event()
    assert preview(first, "document", requests, build=build, stop=done, interval=0.05) == 0
    assert built == ["a.md", "b.md"]
    assert [c for c in fake.calls if c[1] == "web"] == [["/wave/bin/wsh", "web", "open", fake.calls[0][-1]]]


# --- W-04, W-05: when the pane cannot open -------------------------------------------------------


def test_a_missing_wsh_falls_back_to_the_browser_with_the_reason(tmp_path, capsys):
    fake = FakeWsh(missing=True)
    result, browser = show(fake, WAVE, tmp_path)
    assert result.where == "browser" and browser == [ADDRESS]
    assert "not opened in a Wave pane: wsh was not found" in capsys.readouterr().out


def test_a_failing_wsh_falls_back_with_its_message(tmp_path, capsys):
    fake = FakeWsh(fail=True)
    result, browser = show(fake, WAVE, tmp_path)
    assert result.where == "browser" and browser == [ADDRESS]
    assert "wsh web open failed: error: block not found" in capsys.readouterr().out


def test_a_wsh_that_cannot_start_never_stops_the_preview(tmp_path, capsys):
    def broken(command, **kwargs):
        raise OSError("Access is denied")

    result = wave.show(ADDRESS, env=WAVE, run=broken, which=lambda n: "wsh", browser=lambda a: None, state_dir=tmp_path)
    assert result.where == "browser" and "wsh did not run: Access is denied" in capsys.readouterr().out


def test_over_ssh_the_address_and_the_port_forward_are_printed(tmp_path, capsys):
    fake = FakeWsh()
    result, browser = show(fake, {**WAVE, "SSH_CONNECTION": "10.0.0.2 5000 10.0.0.3 22"}, tmp_path)
    out = capsys.readouterr().out
    assert result.where == "nowhere" and browser == [] and fake.calls == []
    assert "runs over SSH" in out and "ssh -L 5123:127.0.0.1:5123" in out and f"wsh web open {ADDRESS}" in out


def test_from_wsl_the_pane_opens_with_a_hint(tmp_path, capsys):
    fake = FakeWsh()
    result, _ = show(fake, {**WAVE, "WSL_DISTRO_NAME": "Ubuntu"}, tmp_path)
    assert result.where == "wave" and "localhostForwarding" in capsys.readouterr().out


def test_wsh_is_found_in_waves_own_bin_folder(tmp_path):
    (tmp_path / "wsh.exe").write_text("", encoding="utf-8")
    assert wave.find_wsh({"WAVETERM_WSHBINDIR": str(tmp_path)}, which=lambda n: None) == str(tmp_path / "wsh.exe")


# --- The commands take the options ---------------------------------------------------------------


@pytest.mark.parametrize("argv", [["docx", "x.md", "--watch", "--wave"], ["slides", "x.md", "--watch", "--no-wave"]])
def test_the_converters_pass_the_option_to_the_watch(tmp_path, monkeypatch, argv):
    from py_doc import watch as watcher

    source = tmp_path / "x.md"
    source.write_text("# X\n", encoding="utf-8")
    seen = []
    monkeypatch.setattr(watcher, "watch", lambda build, errors, **kw: seen.append(kw["wave"]) or 0)
    monkeypatch.chdir(tmp_path)
    assert main(argv) == 0
    assert seen == [argv[-1] == "--wave"]


@pytest.mark.parametrize("command", ["poster", "diagram", "preview"])
def test_the_other_preview_commands_take_the_option(command, capsys):
    with pytest.raises(SystemExit):
        main([command, "x.md", "--wave", "--no-wave"])
    assert "not allowed with argument" in capsys.readouterr().err


# --- W-21 to W-24: doctor ------------------------------------------------------------------------


def test_doctor_reports_the_version_when_wsh_answers():
    fake = FakeWsh()
    [check] = wave.doctor_checks(WAVE, run=fake.run, which=fake.which)
    assert check.status == "ok" and "Wave Terminal 0.12.1" in check.detail and "wsh v0.12.1" in check.detail


def test_doctor_warns_with_the_fix_when_wsh_is_missing():
    [check] = wave.doctor_checks(WAVE, run=FakeWsh().run, which=lambda n: None)
    assert check.status == "WARN" and "not on the PATH" in check.detail and "wsh" in check.hint


def test_doctor_warns_when_wsh_does_not_answer():
    fake = FakeWsh(fail=True)
    [check] = wave.doctor_checks(WAVE, run=fake.run, which=fake.which)
    assert check.status == "WARN" and "does not answer" in check.detail


def test_doctor_says_nothing_about_wave_outside_it():
    assert wave.doctor_checks({}, run=FakeWsh().run) == []


def test_a_wave_warning_leaves_the_exit_status_alone(monkeypatch, capsys):
    from py_doc.runtime.doctor import Check

    monkeypatch.setattr(tools_cli, "make_runtime", lambda settings: object())
    monkeypatch.setattr(tools_cli, "diagnose", lambda runtime: [Check("docker", "ok", "fine")])
    monkeypatch.setattr(wave, "doctor_checks", lambda: [Check("wave", "WARN", "no wsh", "fix it")])
    assert main(["doctor"]) == 0
    assert "WARN  wave" in capsys.readouterr().out


# --- W-11 to W-14: the widget --------------------------------------------------------------------


def test_the_widget_is_in_waves_format():
    definition = wave.widget("C:/docs")
    assert definition["icon"] and definition["label"]
    meta = definition["blockdef"]["meta"]
    assert meta["view"] == "term" and meta["controller"] == "cmd" and meta["cmd"] == "py-doc wave pick"
    assert meta["cmd:cwd"] == "C:/docs"
    assert "cmd:cwd" not in wave.widget()["blockdef"]["meta"]


def test_the_printed_widget_is_valid_json(capsys):
    assert main(["wave", "widget"]) == 0
    assert json.loads(capsys.readouterr().out)[wave.WIDGET_NAME] == wave.widget()


def test_installing_keeps_the_other_widgets_and_never_duplicates(tmp_path):
    others = {"dua": {"icon": "brands@linux", "label": "dua", "blockdef": {"meta": {"view": "term"}}},
              "defwidget@ai": None}  # fmt: skip
    (tmp_path / "widgets.json").write_text(json.dumps(others), encoding="utf-8")
    assert wave.install_widget(tmp_path, wave.widget())[0] == "added"
    assert wave.install_widget(tmp_path, wave.widget())[0] == "up to date"
    saved = json.loads((tmp_path / "widgets.json").read_text(encoding="utf-8"))
    assert saved == {**others, wave.WIDGET_NAME: wave.widget()}


def test_a_changed_definition_is_updated(tmp_path):
    wave.install_widget(tmp_path, wave.widget())
    assert wave.install_widget(tmp_path, wave.widget("D:/work"))[0] == "updated"
    saved = json.loads((tmp_path / "widgets.json").read_text(encoding="utf-8"))
    assert saved[wave.WIDGET_NAME]["blockdef"]["meta"]["cmd:cwd"] == "D:/work" and len(saved) == 1


def test_a_widgets_file_that_is_not_json_is_left_alone(tmp_path):
    (tmp_path / "widgets.json").write_text("{ not json", encoding="utf-8")
    outcome, detail = wave.install_widget(tmp_path, wave.widget())
    assert outcome == "skipped" and "cannot be read" in detail
    assert (tmp_path / "widgets.json").read_text(encoding="utf-8") == "{ not json"


def test_the_install_command_asks_first(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    from py_doc.wave import run_wave

    assert run_wave(["widget", "--install", "--config-dir", str(tmp_path)], ask=lambda q: "n") == 1
    assert not (tmp_path / "widgets.json").exists()
    assert run_wave(["widget", "--install", "--config-dir", str(tmp_path), "-y"]) == 0
    assert "added" in capsys.readouterr().out


# --- W-12, W-13: the picker ---------------------------------------------------------------------


def test_the_picker_lists_the_markdown_files_and_starts_the_chosen_one(tmp_path):
    (tmp_path / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "talk").mkdir()
    (tmp_path / "talk" / "deck.md").write_text("---\nmarp: true\n---\n# Talk\n", encoding="utf-8")
    (tmp_path / ".py-doc").mkdir()
    (tmp_path / ".py-doc" / "hidden.md").write_text("x", encoding="utf-8")
    shown, answers = [], iter(["2", ""])
    chosen = wave.pick(tmp_path, ask=lambda q: next(answers), out=shown.append)
    assert chosen == ((tmp_path / "talk" / "deck.md").resolve(), "slides")
    assert "   1  guide.md" in shown and "   2  talk/deck.md" in shown and not any("hidden" in s for s in shown)


def test_a_file_given_skips_the_question(tmp_path):
    (tmp_path / "poster.md").write_text("---\nposter:\n  size: A1\n---\n", encoding="utf-8")
    chosen = wave.pick(tmp_path, "poster.md", ask=lambda q: pytest.fail("asked"))
    assert chosen == ((tmp_path / "poster.md").resolve(), "poster")


def test_the_picker_moves_into_a_folder(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# A\n", encoding="utf-8")
    answers = iter(["docs", "1", "d"])
    assert wave.pick(tmp_path, ask=lambda q: next(answers), out=lambda s: None) == (
        (tmp_path / "docs" / "a.md").resolve(),
        "document",
    )


def test_wave_pick_runs_the_preview(tmp_path, monkeypatch):
    import py_doc.preview_cli as preview_cli

    (tmp_path / "a.md").write_text("# A\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    seen = []
    monkeypatch.setattr(preview_cli, "run_preview", lambda argv: seen.append(argv) or 0)
    assert wave.run_wave(["pick", "a.md", "--no-wave"]) == 0
    assert seen == [[str((tmp_path / "a.md").resolve()), "--kind", "document", "--port", "0", "--no-wave"]]


@pytest.mark.skipif(sys.platform != "win32" and not os.environ.get("CI"), reason="fake wsh as a script")
def test_a_real_fake_wsh_process_records_its_arguments(tmp_path):
    """W-01 end to end through a process: a fake wsh on the PATH that logs what it was given."""
    log = tmp_path / "log.txt"
    script = tmp_path / "fake_wsh.py"
    script.write_text(
        "import sys; open(sys.argv[1], 'a').write(' '.join(sys.argv[2:]) + '\\n'); print('created block block:abc')\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        wsh = tmp_path / "wsh.cmd"
        wsh.write_text(f'@"{sys.executable}" "{script}" "{log}" %*\n', encoding="utf-8")
    else:
        wsh = tmp_path / "wsh"
        wsh.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "{log}" "$@"\n', encoding="utf-8")
        wsh.chmod(0o755)
    result = wave.open_pane(ADDRESS, env=WAVE, which=lambda n: str(wsh), state_dir=tmp_path)
    assert result.where == "wave" and result.block == "block:abc"
    assert log.read_text(encoding="utf-8").split() == ["web", "open", ADDRESS]
    assert Path(tmp_path, "py-doc-wave-tab-1.txt").read_text(encoding="utf-8") == "block:abc"
