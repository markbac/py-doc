"""The tool image: its definition, tag, lock file, build, and the tools and doctor commands."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
from fake_engine import install

from py_doc import tools_cli
from py_doc.app import main
from py_doc.errors import ConversionError, EnvironmentProblem
from py_doc.runtime import Runtime, image

REAL = image.IMAGE_DIR


@pytest.fixture
def definition(tmp_path, monkeypatch) -> Path:
    """A private copy of the image definition, so tests can change it."""
    copy = tmp_path / "definition"
    shutil.copytree(REAL, copy)
    monkeypatch.setattr(image, "IMAGE_DIR", copy)
    monkeypatch.setattr(image, "LOCK_FILE", copy / "tools.lock")
    return copy


def record_checksums(definition: Path) -> None:
    lock = definition / "tools.lock"
    lock.write_text(re.sub(r" -$", " " + "a" * 64, lock.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")


@pytest.fixture
def engine(tmp_path, monkeypatch):
    return install(tmp_path, monkeypatch)


def runtime_for(engine, ref: str = "py-doc-tools:test") -> Runtime:
    return Runtime(ref, docker=engine.docker, platform_name="linux")


# --- the definition itself ---------------------------------------------------------------------


def test_the_dockerfile_copies_only_files_that_exist_and_pins_its_base():
    text = (REAL / "Dockerfile").read_text(encoding="utf-8")
    from_line = next(line for line in text.splitlines() if line.startswith("FROM "))
    assert ":" in from_line and "latest" not in from_line
    for line in text.splitlines():
        if line.startswith("COPY "):
            sources = line.split()[1:-1]
            for source in sources:
                assert (REAL / source.rstrip("/")).exists(), f"COPY of missing {source}"


def test_every_tool_the_dockerfile_fetches_is_in_the_lock_file():
    text = (REAL / "Dockerfile").read_text(encoding="utf-8")
    fetched = set(re.findall(r"fetch\.sh (\w+) ", text))
    assert fetched == {entry.name for entry in image.read_lock(REAL / "tools.lock")}


def test_the_node_and_python_pins_are_exact():
    for line in (REAL / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            assert "==" in line or "@ git+" in line, line
    import json

    for name, version in json.loads((REAL / "package.json").read_text(encoding="utf-8"))["dependencies"].items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"{name} {version}"


# --- the tag -------------------------------------------------------------------------------------


def test_the_tag_comes_from_the_content(definition):
    first = image.image_ref()
    assert re.fullmatch(r"py-doc-tools:[0-9a-f]{12}", first)
    assert image.image_ref() == first
    (definition / "requirements.txt").write_text("Pillow==1.0\n", encoding="utf-8")
    assert image.image_ref() != first


def test_the_tag_is_the_same_after_a_windows_checkout(definition):
    first = image.content_hash()
    path = definition / "fetch.sh"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert image.content_hash() == first


# --- tools.lock ----------------------------------------------------------------------------------


def test_the_shipped_lock_file_lists_the_tools_and_records_nothing_invented():
    entries = image.read_lock(REAL / "tools.lock")
    assert [e.name for e in entries] == ["pandoc", "plantuml", "ditaa"]
    assert all(not e.recorded for e in entries)
    assert next(e for e in entries if e.name == "pandoc").version == "3.8.2.1"


def test_a_malformed_lock_line_names_its_place(tmp_path):
    path = tmp_path / "tools.lock"
    path.write_text("pandoc 3.8.2.1\n", encoding="utf-8")
    with pytest.raises(ConversionError, match=r"tools.lock:1: expected"):
        image.read_lock(path)


def test_lock_records_checksums_and_refuses_a_changed_file(tmp_path):
    source = tmp_path / "tool.bin"
    source.write_bytes(b"first")
    lock = tmp_path / "tools.lock"
    lock.write_text(f"# header\ntool 1.0 {source.as_uri()} -\n", encoding="utf-8")
    assert image.lock(lock) == ["tool"]
    recorded = image.read_lock(lock)[0].sha256
    assert len(recorded) == 64 and lock.read_text(encoding="utf-8").startswith("# header")
    assert image.lock(lock) == []
    source.write_bytes(b"changed")
    with pytest.raises(ConversionError, match="no longer the one|tools.lock records"):
        image.lock(lock)
    assert image.read_lock(lock)[0].sha256 == recorded


# --- building ------------------------------------------------------------------------------------


def test_a_build_is_refused_until_every_checksum_is_recorded(definition, engine):
    with pytest.raises(EnvironmentProblem, match="py-doc tools lock"):
        image.build(runtime_for(engine))
    assert engine.docker_calls() == []


def test_a_build_runs_docker_build_on_a_copy_of_the_definition(definition, engine, monkeypatch):
    record_checksums(definition)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:3128")
    image.build(runtime_for(engine, "py-doc-tools:abc"))
    (call,) = [c for c in engine.docker_calls() if c[0] == "build"]
    assert call[call.index("--tag") + 1] == "py-doc-tools:abc"
    assert call[call.index("--file") + 1].endswith("/Dockerfile")
    assert "HTTPS_PROXY=http://proxy.example:3128" in call
    (record,) = engine.builds()
    assert {"Dockerfile", "tools.lock", "fetch.sh", "extra-ca"} <= set(record["files"]) and not record["ca"]


def test_the_build_context_has_unix_line_endings(definition, engine):
    record_checksums(definition)
    script = definition / "fetch.sh"
    script.write_bytes(script.read_bytes().replace(b"\n", b"\r\n"))
    seen = []

    # the fake engine records the context listing only, so check the copy through the runtime call
    from py_doc.runtime import engine as engine_module

    real = engine_module.Runtime.engine

    def spying(self, args, **kwargs):
        if args[0] == "build":
            context = Path(args[-1])
            seen.append((context / "fetch.sh").read_bytes())
        return real(self, args, **kwargs)

    image_runtime = runtime_for(engine)
    engine_module.Runtime.engine = spying
    try:
        image.build(image_runtime)
    finally:
        engine_module.Runtime.engine = real
    assert seen and b"\r\n" not in seen[0]


def test_a_certificate_is_added_to_the_build_context(definition, engine, tmp_path):
    record_checksums(definition)
    cert = tmp_path / "corp.crt"
    cert.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    image.build(runtime_for(engine), ca_file=cert)
    assert engine.builds()[0]["ca"] is True
    assert not (definition / "extra-ca" / "extra-ca.crt").exists()


def test_ensure_builds_a_missing_image_and_skips_an_existing_one(definition, engine):
    record_checksums(definition)
    runtime = runtime_for(engine, "py-doc-tools:new")
    image.ensure(runtime)
    assert len(engine.builds()) == 1
    image.ensure(runtime)
    assert len(engine.builds()) == 1


def test_ensure_with_no_build_says_what_to_run(definition, engine):
    with pytest.raises(EnvironmentProblem, match="py-doc tools build"):
        image.ensure(runtime_for(engine, "py-doc-tools:new"), allow_build=False)
    assert engine.builds() == []


def test_a_failed_build_shows_the_builders_output(definition, engine):
    record_checksums(definition)
    engine.configure(build_exit=1, build_error="apt exploded")
    with pytest.raises(ConversionError, match="apt exploded"):
        image.build(runtime_for(engine))


def test_prune_removes_every_tag_but_the_current_one(engine):
    engine.configure(images=["py-doc-tools:old1", "py-doc-tools:cur", "py-doc-tools:old2", "other:1"])
    assert image.prune(runtime_for(engine, "py-doc-tools:cur")) == ["py-doc-tools:old1", "py-doc-tools:old2"]
    removed = [c[-1] for c in engine.docker_calls() if c[:2] == ["image", "rm"]]
    assert removed == ["py-doc-tools:old1", "py-doc-tools:old2"]


# --- commands ------------------------------------------------------------------------------------


@pytest.fixture
def cli(engine, monkeypatch):
    monkeypatch.setattr(tools_cli, "make_runtime", lambda settings: runtime_for(engine, "tools:test"))
    return engine


def test_tools_status_reports_versions_from_inside_the_image(cli, capsys):
    cli.configure(images=["tools:test"], stdout="v1.2.3\n")
    assert main(["tools", "status"]) == 0
    out = capsys.readouterr().out
    assert "tools:test  built" in out and "pandoc   v1.2.3" in out and "lock" in out


def test_tools_status_for_an_unbuilt_image_stops_after_the_tag(cli, capsys):
    cli.configure(images=[])
    assert main(["tools", "status"]) == 0
    assert "not built" in capsys.readouterr().out
    assert cli.runs() == []


def test_a_stopped_engine_gives_exit_status_2(cli, capsys):
    cli.configure(daemon=False)
    assert main(["tools", "status"]) == 2
    assert "not running" in capsys.readouterr().err
