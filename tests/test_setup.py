"""py-doc setup: what it runs, in what order, and what it refuses to do."""

from __future__ import annotations

import subprocess

import pytest
from fake_engine import install

from py_doc.app import main
from py_doc.errors import EnvironmentProblem
from py_doc.runtime import Runtime
from py_doc.runtime import setup as docker_setup
from py_doc.tools_cli import run_setup


class Recorder:
    """Stands in for subprocess.run: records each call and answers from a table."""

    def __init__(self, user: str = "ann", code: int = 0):
        self.calls: list[tuple[list[str], bytes | None]] = []
        self.user, self.code = user, code

    def __call__(self, argv, input=None, **kwargs):
        self.calls.append((list(argv), input))
        if argv[-2:] == ["id", "-un"]:
            return subprocess.CompletedProcess(argv, 0, stdout=(self.user + "\n").encode(), stderr=b"")
        if input is not None:
            return subprocess.CompletedProcess(argv, self.code, stdout=b"", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    def scripts(self) -> list[str]:
        return [data.decode() for _, data in self.calls if data]


@pytest.fixture
def windows(tmp_path, monkeypatch):
    engine = install(tmp_path, monkeypatch)
    runtime = Runtime("tools:test", docker=["definitely-not-docker-xyz"], wsl_exe=engine.wsl, wsl_distro="Ubuntu", platform_name="windows")
    return engine, runtime


def settle(monkeypatch, runtime):
    monkeypatch.setattr("py_doc.tools_cli.make_runtime", lambda settings: runtime)
    monkeypatch.setattr("py_doc.tools_cli.settings_from_config", lambda path: __import__("py_doc.runtime", fromlist=["RuntimeSettings"]).RuntimeSettings())


def test_the_script_adds_the_user_and_turns_on_systemd_only_in_wsl():
    wsl, linux = docker_setup.script("ann", True), docker_setup.script("ann", False)
    assert "usermod -aG docker ann" in wsl and "systemd=true" in wsl
    assert "usermod -aG docker ann" in linux and "systemd=true" not in linux
    assert "download.docker.com/linux/$ID" in wsl


def test_a_user_name_is_quoted_in_the_script():
    assert "usermod -aG docker 'a b; rm'" in docker_setup.script("a b; rm", False)


def test_a_working_docker_is_left_alone(tmp_path, monkeypatch, capsys):
    engine = install(tmp_path, monkeypatch)
    runtime = Runtime("tools:test", docker=engine.docker, platform_name="linux")
    settle(monkeypatch, runtime)
    recorder = Recorder()
    assert run_setup([], run=recorder) == 0
    assert "already works" in capsys.readouterr().out and recorder.calls == []


def test_dry_run_prints_the_script_and_runs_nothing(windows, monkeypatch, capsys):
    _, runtime = windows
    settle(monkeypatch, runtime)
    recorder = Recorder()
    assert run_setup(["--dry-run"], run=recorder) == 0
    out = capsys.readouterr().out
    assert "apt-get install -y docker-ce" in out and "'ann'" in out
    assert recorder.scripts() == []


def test_declining_changes_nothing(windows, monkeypatch, capsys):
    _, runtime = windows
    settle(monkeypatch, runtime)
    recorder = Recorder()
    assert run_setup([], run=recorder, ask=lambda prompt: "n") == 1
    assert "Nothing was changed" in capsys.readouterr().out and recorder.scripts() == []


def test_a_windows_setup_runs_as_root_in_the_distro_then_restarts_it(windows, monkeypatch, capsys):
    engine, runtime = windows
    settle(monkeypatch, runtime)
    recorder = Recorder()
    assert run_setup(["--yes"], run=recorder) in (0, 2)  # the fake docker stays missing, so the check at the end may fail
    commands = [call[0] for call in recorder.calls]
    root = next(c for c in commands if "--user" in c and c[-2:] == ["bash", "-s"])
    assert root[root.index("-d") + 1] == "Ubuntu" and root[root.index("--user") + 1] == "root"
    (script,) = recorder.scripts()
    assert "usermod -aG docker ann" in script and script.startswith("export DEBIAN_FRONTEND=noninteractive")
    assert any(c[-2:] == ["--terminate", "Ubuntu"] for c in commands)
    assert any(c[-3:] == ["service", "docker", "start"] for c in commands)


def test_an_unsupported_distribution_is_an_environment_problem(windows):
    _, runtime = windows
    with pytest.raises(EnvironmentProblem, match="Ubuntu and Debian"):
        docker_setup.install(runtime, "ann", Recorder(code=docker_setup.UNSUPPORTED))


def test_a_failing_script_reports_its_status(windows):
    _, runtime = windows
    with pytest.raises(EnvironmentProblem, match="exit status 100"):
        docker_setup.install(runtime, "ann", Recorder(code=100))


def test_root_as_the_default_wsl_user_is_refused(windows):
    _, runtime = windows
    with pytest.raises(EnvironmentProblem, match="default user is root"):
        docker_setup.target_user(runtime, Recorder(user="root"))


def test_linux_uses_sudo_unless_already_root(monkeypatch):
    runtime = Runtime("tools:test", platform_name="linux")
    monkeypatch.setattr("os.geteuid", lambda: 1000, raising=False)
    assert docker_setup.command(runtime) == ["sudo", "bash", "-s"]
    monkeypatch.setattr("os.geteuid", lambda: 0, raising=False)
    assert docker_setup.command(runtime) == ["bash", "-s"]


def test_the_command_is_listed(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "setup" in capsys.readouterr().out


def test_the_script_waits_for_apt_locks_held_by_unattended_upgrades():
    text = docker_setup.script("ann", True)
    assert "DPkg::Lock::Timeout" in text and "apt install -y docker-ce" in text
    assert "\napt-get install" not in text and "\napt-get update" not in text  # only the wrapper calls apt-get
