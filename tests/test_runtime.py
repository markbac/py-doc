"""The tool runner, tested against fake docker and wsl.exe programs."""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path, PureWindowsPath

import pytest
from fake_engine import install

from py_doc.errors import EnvironmentProblem, ToolFailed, ToolTimeout, exit_status
from py_doc.runtime import Mount, Runtime
from py_doc.runtime.engine import decode_wsl

IMAGE = "tools:test"


@pytest.fixture
def engine(tmp_path, monkeypatch):
    return install(tmp_path, monkeypatch)


def linux(engine, **kwargs) -> Runtime:
    return Runtime(IMAGE, docker=engine.docker, platform_name="linux", **kwargs)


def windows(engine, **kwargs) -> Runtime:
    return Runtime(IMAGE, docker="docker", wsl_exe=engine.wsl, platform_name="windows", **kwargs)


def options(run: list[str], flag: str) -> list[str]:
    return [run[i + 1] for i, word in enumerate(run) if word == flag]


# --- the command that is built -----------------------------------------------------------------


def test_a_run_is_locked_down_and_runs_as_the_calling_user(engine, tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    src.mkdir()
    out.mkdir()
    linux(engine).run(["pandoc", "--version"], mounts=[Mount(src), Mount(out, writable=True)])
    (run,) = engine.runs()
    assert run[1:3] == ["--rm", "--pull"] and options(run, "--pull") == ["never"]
    assert options(run, "--network") == ["none"]
    assert options(run, "--cap-drop") == ["ALL"]
    assert options(run, "--security-opt") == ["no-new-privileges"]
    if hasattr(os, "getuid"):
        assert options(run, "--user") == [f"{os.getuid()}:{os.getgid()}"]
    mounts = options(run, "--mount")
    assert f"type=bind,source={src.resolve().as_posix()},target={src.resolve().as_posix()},readonly" in mounts
    assert f"type=bind,source={out.resolve().as_posix()},target={out.resolve().as_posix()}" in mounts
    assert "type=volume,source=py-doc-cache,target=/cache" in mounts
    assert "HOME=/cache/home" in options(run, "-e")
    assert run[-3:] == [IMAGE, "pandoc", "--version"]


def test_network_is_off_unless_a_step_asks_for_it(engine):
    linux(engine).run(["tool"], network=True)
    assert "--network" not in engine.runs()[0]


def test_environment_and_working_folder_are_passed(engine, tmp_path):
    linux(engine).run(["tool"], mounts=[Mount(tmp_path)], workdir=tmp_path, env={"A": "1"}, shm_size="1g")
    run = engine.runs()[0]
    assert "A=1" in options(run, "-e")
    assert options(run, "-w") == [tmp_path.resolve().as_posix()]
    assert options(run, "--shm-size") == ["1g"]


def test_path_arguments_must_lie_under_a_mount(engine, tmp_path):
    (tmp_path / "in").mkdir()
    with pytest.raises(EnvironmentProblem, match="not under any folder"):
        linux(engine).run(["pandoc", tmp_path / "secret.md"], mounts=[Mount(tmp_path / "in")])
    assert engine.runs() == []


def test_a_working_folder_outside_the_mounts_is_refused(engine, tmp_path):
    with pytest.raises(EnvironmentProblem, match="working folder"):
        linux(engine).run(["tool"], mounts=[], workdir=tmp_path)


def test_a_path_argument_is_translated_to_the_engine_path(engine, tmp_path):
    linux(engine).run(["pandoc", tmp_path / "a.md"], mounts=[Mount(tmp_path)])
    assert engine.runs()[0][-1] == (tmp_path / "a.md").resolve().as_posix()


def test_a_folder_name_with_a_comma_is_quoted_for_mount(engine, tmp_path):
    odd = tmp_path / "a,b"
    odd.mkdir()
    linux(engine).run(["tool"], mounts=[Mount(odd)])
    mount = options(engine.runs()[0], "--mount")[0]
    assert f'"source={odd.resolve().as_posix()}"' in mount


def test_no_shell_is_used_anywhere():
    source = Path(__file__).parent.parent / "src"
    offenders = [p for p in source.rglob("*.py") if re.search(r"shell\s*=\s*True", p.read_text(encoding="utf-8"))]
    assert offenders == []


# --- failures ----------------------------------------------------------------------------------


def test_a_failing_tool_raises_with_its_whole_output(engine):
    engine.configure(exit=3, stderr="line one\nline two\n", stdout="partial\n")
    with pytest.raises(ToolFailed) as caught:
        linux(engine).run(["mytool", "x"])
    error = caught.value
    assert error.tool == "mytool" and error.returncode == 3
    assert "line one" in str(error) and "line two" in str(error) and "partial" in str(error)
    assert exit_status(error) == 1


def test_check_false_returns_the_result_of_a_failing_tool(engine):
    engine.configure(exit=2, stdout="data")
    result = linux(engine).run(["mytool"], check=False)
    assert (result.returncode, result.stdout) == (2, "data")


def test_a_stopped_engine_is_an_environment_problem_with_a_hint(engine):
    engine.configure(daemon=False)
    with pytest.raises(EnvironmentProblem, match="systemctl start docker") as caught:
        linux(engine).run(["tool"])
    assert exit_status(caught.value) == 2


def test_a_stopped_engine_in_wsl_says_to_start_it_inside_the_distro(engine):
    engine.configure(daemon=False)
    with pytest.raises(EnvironmentProblem, match="inside the WSL distro"):
        windows(engine, wsl_distro="Ubuntu").run(["tool"])


def test_a_missing_image_names_the_build_command(engine):
    engine.configure(images=[])
    with pytest.raises(EnvironmentProblem, match="py-doc tools build"):
        linux(engine).run(["tool"])


def test_a_missing_docker_program_is_an_environment_problem():
    runtime = Runtime(IMAGE, docker="definitely-not-docker-xyz", platform_name="linux")
    with pytest.raises(EnvironmentProblem, match="was not found"):
        runtime.run(["tool"])


def test_a_missing_wsl_is_an_environment_problem():
    runtime = Runtime(IMAGE, wsl_exe="definitely-not-wsl-xyz", platform_name="windows")
    with pytest.raises(EnvironmentProblem, match="wsl.exe was not found"):
        runtime.run(["tool"])


def test_a_tool_that_overruns_is_stopped_and_its_container_killed(engine):
    engine.configure(sleep=5)
    with pytest.raises(ToolTimeout, match="did not finish within 0.5 seconds"):
        linux(engine).run(["slow"], timeout=0.5)
    assert any(call[:1] == ["kill"] and call[1].startswith("py-doc-") for call in engine.docker_calls())


def test_output_that_is_not_utf8_is_replaced_with_a_warning(engine, caplog):
    engine.configure(stdout_hex="636166e9")  # "caf" and a Latin-1 e-acute
    with caplog.at_level(logging.WARNING, logger="py_doc"):
        result = linux(engine).run(["tool"])
    assert result.stdout == "caf\ufffd"
    assert [r for r in caplog.records if "UTF-8" in r.getMessage()]


# --- Windows and WSL ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("windows_path", "expected"),
    [
        (r"C:\Users\me\my docs\a.md", "/mnt/c/Users/me/my docs/a.md"),
        (r"D:\proj\b.md", "/mnt/d/proj/b.md"),
        ("C:\\Users\\zo\u00eb\\caf\u00e9.md", "/mnt/c/Users/zo\u00eb/caf\u00e9.md"),
        (r"\\wsl$\Ubuntu\home\me\x.md", "/home/me/x.md"),
    ],
)
def test_windows_paths_are_translated_by_wslpath(engine, windows_path, expected):
    assert windows(engine).container_path(PureWindowsPath(windows_path)) == expected


def test_a_path_wsl_cannot_see_is_an_error_naming_it(engine):
    with pytest.raises(EnvironmentProblem, match=r"WSL cannot see .*server"):
        windows(engine).container_path(r"\\server\share\x.md")


def test_a_windows_run_goes_through_wsl_with_the_distro_and_translated_mounts(engine):
    runtime = windows(engine, wsl_distro="Ubuntu")
    runtime.run(["pandoc", PureWindowsPath(r"D:\my docs\a.md")], mounts=[Mount(PureWindowsPath(r"D:\my docs"))])
    first = engine.wsl_calls()
    assert ["-d", "Ubuntu", "--exec", "wslpath", "-a", "-u", r"D:\my docs"] in [c for c in first]
    (run,) = engine.runs()
    assert "type=bind,source=/mnt/d/my docs,target=/mnt/d/my docs,readonly" in options(run, "--mount")
    assert options(run, "--user") == ["1000:1000"]
    assert run[-2:] == ["pandoc", "/mnt/d/my docs/a.md"]
    assert all(call[:3] == ["-d", "Ubuntu", "--exec"] for call in first if call[0] != "-l")


def test_translated_paths_are_cached(engine):
    runtime = windows(engine)
    for _ in range(3):
        runtime.container_path(r"C:\x")
    assert len([c for c in engine.wsl_calls() if "wslpath" in c]) == 1


def test_wsl_listings_are_utf16():
    assert decode_wsl(b"\xff\xfe" + "Ubuntu\r\n".encode("utf-16-le")) == "Ubuntu\r\n"
    assert decode_wsl(b"plain") == "plain"


def test_the_runner_refuses_to_start_on_an_unsupported_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    with pytest.raises(EnvironmentProblem, match="Linux and Windows"):
        Runtime(IMAGE)
