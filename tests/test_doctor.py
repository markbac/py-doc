"""``py-doc doctor`` and the runtime section of py-doc.yml."""

from __future__ import annotations

import pytest
from fake_engine import install

from py_doc import tools_cli
from py_doc.app import main
from py_doc.config import ConfigError, parse_config
from py_doc.runtime import Runtime
from py_doc.runtime.doctor import diagnose


@pytest.fixture
def engine(tmp_path, monkeypatch):
    return install(tmp_path, monkeypatch)


def runtime_for(engine, ref: str = "py-doc-tools:test") -> Runtime:
    return Runtime(ref, docker=engine.docker, platform_name="linux")


def test_doctor_passes_when_the_container_works(engine, capsys, monkeypatch):
    engine.configure(stdout="pandoc 3.8.2.1\n")
    monkeypatch.setattr(tools_cli, "make_runtime", lambda settings: runtime_for(engine, "tools:test"))
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "ok    docker" in out and "ok    engine" in out and "a trivial run works: pandoc 3.8.2.1" in out


def test_doctor_reports_an_unbuilt_image_as_information(engine, capsys, monkeypatch):
    engine.configure(images=[])
    monkeypatch.setattr(tools_cli, "make_runtime", lambda settings: runtime_for(engine, "tools:test"))
    assert main(["doctor"]) == 0
    assert "info  image" in capsys.readouterr().out


def test_doctor_fails_with_a_hint_when_the_engine_is_down(engine, capsys, monkeypatch):
    engine.configure(daemon=False)
    monkeypatch.setattr(tools_cli, "make_runtime", lambda settings: runtime_for(engine, "tools:test"))
    assert main(["doctor"]) == 2
    out = capsys.readouterr().out
    assert "FAIL  engine" in out and "systemctl start docker" in out


def test_doctor_on_an_unsupported_platform_exits_2(capsys, monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert main(["doctor"]) == 2
    assert "Linux and Windows" in capsys.readouterr().out


# --- doctor on Windows ---------------------------------------------------------------------------


def windows_runtime(engine, **kwargs) -> Runtime:
    return Runtime("tools:test", docker="docker", wsl_exe=engine.wsl, platform_name="windows", **kwargs)


def by_name(checks):
    return {c.name: c for c in checks}


def test_doctor_on_windows_reads_the_utf16_distro_list(engine, monkeypatch):
    monkeypatch.setenv("FAKE_WSL_DISTROS", "Ubuntu,Debian")
    engine.configure(stdout="pandoc 3.8.2.1\n")
    checks = by_name(diagnose(windows_runtime(engine, wsl_distro="Debian")))
    assert checks["wsl"].status == "ok" and "Debian (WSL 2)" in checks["wsl"].detail
    assert checks["container"].status == "ok"


def test_doctor_on_windows_names_a_missing_distro(engine, monkeypatch):
    monkeypatch.setenv("FAKE_WSL_DISTROS", "Ubuntu")
    checks = by_name(diagnose(windows_runtime(engine, wsl_distro="Fedora")))
    assert checks["wsl"].status == "FAIL" and "Installed: Ubuntu" in checks["wsl"].detail


def test_doctor_on_windows_rejects_wsl_1(engine, monkeypatch):
    monkeypatch.setenv("FAKE_WSL_VERSION", "1")
    checks = by_name(diagnose(windows_runtime(engine)))
    assert checks["wsl"].status == "FAIL" and "wsl --set-version" in checks["wsl"].hint
    assert "docker" not in checks


# --- the runtime section of py-doc.yml -------------------------------------------------------------


def test_the_runtime_section_is_read(tmp_path):
    config = parse_config({"runtime": {"docker": "/usr/bin/docker", "wsl_distro": "Ubuntu"}}, tmp_path)
    assert (config.runtime.docker, config.runtime.wsl_distro) == ("/usr/bin/docker", "Ubuntu")


def test_a_typo_in_the_runtime_section_names_its_place(tmp_path):
    with pytest.raises(ConfigError, match="unknown key 'wsl_distroo' in runtime"):
        parse_config({"runtime": {"wsl_distroo": "x"}}, tmp_path)
