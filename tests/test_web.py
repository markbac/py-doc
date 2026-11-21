"""py-doc web: the workspace's file operations, uploads, jobs, lint and previews, without a container."""

from __future__ import annotations

import base64
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402

from py_doc.web.app import Settings, create_app  # noqa: E402
from py_doc.web.jobs import JobManager  # noqa: E402
from py_doc.web.preview import PreviewManager  # noqa: E402
from py_doc.web.workspace import Workspace, WorkspaceError  # noqa: E402

# A renderer for previews: copies the Markdown into a page, or fails when it says FAIL
FAKE_RENDER = """
import sys, pathlib
kind, source, output = sys.argv[1:]
text = pathlib.Path(source).read_text(encoding="utf-8")
if "FAIL" in text:
    print("Error: the diagram on line 3 did not draw", file=sys.stderr)
    sys.exit(1)
pathlib.Path(output).write_text(f"<html><body><p>{kind}</p><pre>{text}</pre></body></html>", encoding="utf-8")
"""


@pytest.fixture
def root(tmp_path):
    workspace = tmp_path / "ws"
    (workspace / "demo" / "images").mkdir(parents=True)
    (workspace / "demo" / "guide.md").write_text("# Guide\n\nHello.\n", encoding="utf-8")
    (workspace / "demo" / "images" / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0")
    (workspace / "outside.txt").write_text("secret", encoding="utf-8")
    return workspace


@pytest.fixture
def previews(tmp_path):
    script = tmp_path / "fake_render.py"
    script.write_text(FAKE_RENDER, encoding="utf-8")
    return PreviewManager(command=[sys.executable, str(script)], timeout=60)


@pytest.fixture
def client(root, previews):
    app = create_app(Settings(root=root), JobManager(1, timeout=120), previews)
    with TestClient(app) as test_client:
        yield test_client


def wait_job(client, job_id, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] not in ("queued", "running") and job["finished"]:
            return job
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} did not finish")


def wait_preview(client, preview_id, version, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/preview/{preview_id}").json()
        if not status["building"] and (status["version"] >= version or status["error"]):
            return status
        time.sleep(0.1)
    raise AssertionError("the preview did not build")


# --- the workspace ------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["../x", "demo/../../x", "C:/Windows", "demo/..", "demo/./../x"])
def test_paths_outside_the_workspace_are_refused(root, path):
    with pytest.raises(WorkspaceError):
        Workspace(root).resolve(path)


@pytest.mark.parametrize("path", ["/etc/passwd", "a//b", r"\\server\share"])
def test_absolute_looking_paths_stay_inside(root, path):
    resolved = Workspace(root).resolve(path).resolve()
    assert root.resolve() in resolved.parents


def test_projects_and_tree(client):
    assert client.get("/api/projects").json() == [{"name": "demo", "config": False}]
    tree = client.get("/api/tree", params={"path": "demo"}).json()
    assert [c["name"] for c in tree["children"]] == ["images", "guide.md"]  # folders first
    assert tree["children"][0]["children"][0]["path"] == "demo/images/a.png"


def test_the_servers_own_files_are_not_listed(client, root):
    (root / "demo" / ".py-doc" / "web").mkdir(parents=True)
    (root / "demo" / ".git").mkdir()
    names = [c["name"] for c in client.get("/api/tree", params={"path": "demo"}).json()["children"]]
    assert ".py-doc" not in names and ".git" not in names


def test_read_save_and_refuse_outside(client, root):
    assert client.get("/api/file", params={"path": "demo/guide.md"}).json()["text"].startswith("# Guide")
    assert client.put("/api/file", json={"path": "demo/new/page.md", "text": "# New\r\n"}).status_code == 200
    assert (root / "demo" / "new" / "page.md").read_bytes() == b"# New\r\n"  # as sent, line endings and all
    assert client.get("/api/file", params={"path": "../outside.txt"}).status_code == 400
    assert client.put("/api/file", json={"path": "loose.md", "text": "x"}).status_code == 400  # files go in a project
    assert client.get("/api/file", params={"path": "demo/images/a.png"}).status_code == 415


def test_mkdir_move_and_delete(client, root):
    assert client.post("/api/mkdir", json={"path": "demo/chapters"}).status_code == 200
    assert client.post("/api/move", json={"source": "demo/guide.md", "target": "demo/chapters/guide.md"}).is_success
    assert (root / "demo" / "chapters" / "guide.md").is_file()
    clash = client.post("/api/move", json={"source": "demo/images", "target": "demo/chapters"})
    assert clash.status_code == 409
    inside = client.post("/api/move", json={"source": "demo/chapters", "target": "demo/chapters/deeper"})
    assert inside.status_code == 400
    assert client.delete("/api/path", params={"path": "demo/chapters"}).is_success
    assert not (root / "demo" / "chapters").exists()
    assert client.delete("/api/path", params={"path": ""}).status_code == 400


def test_new_project(client, root):
    assert client.post("/api/projects", json={"name": "pump docs"}).is_success
    assert (root / "pump docs").is_dir()
    assert client.post("/api/projects", json={"name": "pump docs"}).status_code == 409
    assert client.post("/api/projects", json={"name": "../evil"}).status_code == 400


# --- uploads and downloads ------------------------------------------------------------------------


def test_dropped_folder_keeps_its_folders(client, root):
    files = [("files", ("notes.md", b"# Notes\n")), ("files", ("data.csv", b"a,b\n"))]
    data = {"folder": "demo", "paths": json.dumps(["dropped/notes.md", "dropped/sub/data.csv"])}
    written = client.post("/api/upload", data=data, files=files).json()["written"]
    assert written == ["demo/dropped/notes.md", "demo/dropped/sub/data.csv"]
    assert (root / "demo" / "dropped" / "sub" / "data.csv").read_bytes() == b"a,b\n"


def test_upload_cannot_escape(client, root):
    data = {"folder": "demo", "paths": json.dumps(["../../escaped.md"])}
    response = client.post("/api/upload", data=data, files=[("files", ("x.md", b"x"))])
    assert response.status_code == 400
    assert not (root.parent / "escaped.md").exists()


def make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_zip_is_unpacked_without_its_one_top_folder(client, root):
    data = make_zip({"my-docs/py-doc.yml": b"documents: {}\n", "my-docs/docs/a.md": b"# A\n", "__MACOSX/x": b""})
    response = client.post("/api/upload", data={"folder": "demo", "unzip": "true"},
                           files=[("files", ("my-docs.zip", data))])  # fmt: skip
    assert response.is_success, response.text
    assert (root / "demo" / "py-doc.yml").is_file() and (root / "demo" / "docs" / "a.md").is_file()
    assert not (root / "demo" / "__MACOSX").exists()


def test_zip_slip_is_refused(client, root):
    data = make_zip({"../../evil.txt": b"x"})
    response = client.post("/api/upload", data={"folder": "demo", "unzip": "true"}, files=[("files", ("a.zip", data))])
    assert response.status_code == 400
    assert not (root.parent / "evil.txt").exists()


def test_download_a_folder_as_zip(client):
    response = client.get("/api/download", params={"path": "demo"})
    assert response.is_success
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert sorted(names) == ["demo/guide.md", "demo/images/a.png"]


def test_raw_files_are_sandboxed(client):
    response = client.get("/raw/demo/guide.md")
    assert response.is_success and "sandbox" in response.headers["content-security-policy"]
    assert client.get("/raw/../outside.txt").status_code in (400, 404)


# --- the page and the password --------------------------------------------------------------------


def test_the_page_and_its_assets(client):
    assert "py-doc" in client.get("/").text
    assert (
        client.get("/static/app.js").headers["content-type"].startswith(("application/javascript", "text/javascript"))
    )
    assert client.get("/static/..%2Fapp.py").status_code == 404


def test_password(root, previews):
    app = create_app(Settings(root=root, password="hunter2"), JobManager(1), previews)
    with TestClient(app) as test_client:
        assert test_client.get("/api/projects").status_code == 401
        good = base64.b64encode(b"anyone:hunter2").decode()
        bad = base64.b64encode(b"anyone:wrong").decode()
        assert test_client.get("/api/projects", headers={"Authorization": f"Basic {bad}"}).status_code == 401
        assert test_client.get("/api/projects", headers={"Authorization": f"Basic {good}"}).is_success


# --- jobs, lint and previews ------------------------------------------------------------------------


def test_jobs_run_keep_their_output_and_stop(tmp_path):
    jobs = JobManager(1, timeout=60)
    done = jobs.start("hello", "demo", [sys.executable, "-c", "print('hello from a job')"], tmp_path)
    while done.finished is None:
        time.sleep(0.05)
    assert done.state == "ok" and "hello from a job" in done.log
    slow = jobs.start("slow", "demo", [sys.executable, "-c", "import time; time.sleep(60)"], tmp_path)
    while slow.state != "running":
        time.sleep(0.05)
    assert jobs.stop(slow.id)
    while slow.finished is None:
        time.sleep(0.05)
    assert slow.state == "stopped"


def test_jobs_time_out(tmp_path):
    jobs = JobManager(1, timeout=0.5)
    job = jobs.start("slow", "demo", [sys.executable, "-c", "import time; time.sleep(30)"], tmp_path)
    while job.finished is None:
        time.sleep(0.05)
    assert job.state == "stopped" and "Stopped after" in job.log


def test_lint_reports_issues_by_workspace_path(client, root):
    (root / "demo" / "guide.md").write_text("# Guide\n\nWe utilize the the tool.\n", encoding="utf-8")
    job = client.post("/api/lint", json={"path": "demo"}).json()
    finished = wait_job(client, job["id"])
    report = finished["result"]["lint"]
    assert report["summary"]["files_scanned"] == 1
    assert report["issues"], finished["log"]
    assert all(issue["path"] == "demo/guide.md" for issue in report["issues"])


def test_build_needs_a_config(client):
    response = client.post("/api/build", json={"project": "demo"})
    assert response.status_code == 400 and "py-doc.yml" in response.json()["error"]


def test_convert_only_markdown(client):
    assert client.post("/api/convert", json={"path": "demo/images/a.png", "kind": "docx"}).status_code == 400
    assert client.post("/api/convert", json={"path": "demo/guide.md", "kind": "exe"}).status_code == 400


def test_preview_builds_again_on_save_and_keeps_the_last_good_page(client):
    status = client.post("/api/preview", json={"path": "demo/guide.md", "kind": "deck"}).json()
    first = wait_preview(client, status["id"], 1)
    assert first["version"] == 1 and first["error"] is None
    page = client.get(f"/preview/{status['id']}")
    assert "<p>preview-deck</p>" in page.text and "pydocScroll" in page.text
    assert "sandbox" in page.headers["content-security-policy"]

    client.put("/api/file", json={"path": "demo/guide.md", "text": "# Guide\n\nChanged.\n"})
    second = wait_preview(client, status["id"], 2)
    assert second["version"] == 2 and "Changed." in client.get(f"/preview/{status['id']}").text

    client.put("/api/file", json={"path": "demo/guide.md", "text": "# Guide\n\nFAIL\n"})
    time.sleep(0.4)
    broken = wait_preview(client, status["id"], 3)
    assert broken["version"] == 2 and "did not draw" in broken["error"]
    assert "Changed." in client.get(f"/preview/{status['id']}").text  # the last good page stays


def test_preview_of_a_file_in_another_project_is_not_rebuilt(client, root, previews):
    (root / "other").mkdir()
    status = client.post("/api/preview", json={"path": "demo/guide.md", "kind": "document"}).json()
    wait_preview(client, status["id"], 1)
    client.put("/api/file", json={"path": "other/x.md", "text": "# X\n"})
    time.sleep(0.5)
    assert client.get(f"/api/preview/{status['id']}").json()["version"] == 1


def test_web_command_is_listed():
    from py_doc.app import _DELEGATES

    assert "web" in _DELEGATES


def test_render_rejects_unknown_kinds(capsys):
    from py_doc.web.render import main

    assert main(["exe", "a.md", "b"]) == 2
    assert "usage" in capsys.readouterr().err


def test_static_files_are_packaged():
    folder = Path(__file__).resolve().parents[1] / "src" / "py_doc" / "web" / "static"
    assert {p.name for p in folder.iterdir()} >= {"index.html", "app.js", "app.css"}


# --- the editor's py-doc highlighting -----------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
MODE = (ROOT / "src" / "py_doc" / "web" / "static" / "pydoc-mode.js").read_text(encoding="utf-8")
GRAMMAR = json.loads((ROOT / "editors" / "vscode" / "syntaxes" / "pydoc.markdown.tmLanguage.json").read_text("utf-8"))


def js_pattern(name: str) -> str:
    import re

    found = re.search(rf"const {name} = /(.+)/i?;", MODE)
    assert found, f"{name} is not in pydoc-mode.js"
    return found.group(1)


def test_the_web_editor_marks_what_the_vscode_grammar_marks():
    repository = GRAMMAR["repository"]
    assert js_pattern("DIRECTIVE") == repository["directive"]["match"]
    assert js_pattern("VARIABLE") == repository["variable"]["match"]
    assert js_pattern("SLOT") == repository["slot"]["match"]
    assert js_pattern("CALLOUT") == repository["callout"]["patterns"][0]["match"].removeprefix("(?i)")


def test_the_web_editor_knows_every_documented_directive():
    import re

    documented = set()
    for path in (ROOT / "docs" / "guide").glob("*.md"):
        documented |= set(re.findall(r"^\[\[([A-Z][A-Z-]*)", path.read_text(encoding="utf-8"), re.M))
    known = set(re.findall(r'"([A-Z][A-Z-]*)"', MODE.split("const KNOWN", 1)[1].split(");", 1)[0]))
    assert documented and documented <= known, documented - known


def test_the_diagram_modes_are_up_to_date_with_the_vscode_grammars():
    """diagram-modes.js is written from the grammars by scripts/web_editor_modes.py: run it after a change."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("web_editor_modes", ROOT / "scripts" / "web_editor_modes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    written = (ROOT / "src" / "py_doc" / "web" / "static" / "diagram-modes.js").read_text(encoding="utf-8")
    assert written == module.render(), "run: python scripts/web_editor_modes.py"
    fences = module.fence_names()
    assert fences["mermaid"] == "pydoc-mermaid" and fences["puml"] == "pydoc-plantuml"
    assert fences["vega-lite"] == "application/json" and fences["chart"] == "pydoc-block"
    assert fences["bpmnt"] == "pydoc-bpmnt"


def test_the_default_port_is_8888(monkeypatch, tmp_path):
    import py_doc.web.cli as web_cli

    seen = {}
    monkeypatch.delenv("PYDOC_WEB_PORT", raising=False)
    monkeypatch.setattr("uvicorn.run", lambda app, host, port, log_level: seen.update(host=host, port=port))
    assert web_cli.run_web(["--root", str(tmp_path / "ws"), "-q"]) == 0
    assert seen == {"host": "127.0.0.1", "port": 8888}


# --- example projects and the dark preview --------------------------------------------------------------


def test_example_projects_are_offered_and_copied(client, root):
    offered = {s["name"]: s for s in client.get("/api/samples").json()}
    assert set(offered) == {"py-doc-docs", "sensor-node-examples", "poster-examples"}
    assert not offered["poster-examples"]["installed"]

    first = client.post("/api/samples", json={"name": "poster-examples"}).json()
    assert first["name"] == "poster-examples" and first["files"] > 5
    assert (root / "poster-examples" / "poster.md").is_file()
    assert not (root / "poster-examples" / "build").exists()  # outputs are not copied
    assert client.get("/api/samples").json()[2]["installed"]

    second = client.post("/api/samples", json={"name": "poster-examples"}).json()
    assert second["name"] == "poster-examples-2"  # an edited first copy is never overwritten
    assert client.post("/api/samples", json={"name": "nothing"}).status_code == 404


def test_the_documentation_sample_builds_from_its_own_config(client, root):
    client.post("/api/samples", json={"name": "py-doc-docs"})
    project = root / "py-doc-docs"
    assert (project / "py-doc.yml").is_file() and (project / "docs" / "guide" / "00_introduction.md").is_file()
    from py_doc.config import load_config

    config = load_config(project / "py-doc.yml")
    files = [project / s.file for d in config.documents.values() for s in d.sources if s.file]
    assert len(files) > 20 and all(path.is_file() for path in files)


def test_example_projects_are_git_repositories_when_git_is_there(client, root):
    import shutil

    if shutil.which("git") is None:
        pytest.skip("no git")
    client.post("/api/samples", json={"name": "poster-examples"})
    assert (root / "poster-examples" / ".git").is_dir()
    tree = client.get("/api/tree", params={"path": "poster-examples"}).json()
    assert ".git" not in [c["name"] for c in tree["children"]]


def test_previews_can_be_shown_dark(client):
    status = client.post("/api/preview", json={"path": "demo/guide.md", "kind": "document"}).json()
    waiting = client.get(f"/preview/{status['id']}")
    assert "Building the preview" in waiting.text and "t=dark" in waiting.text
    wait_preview(client, status["id"], 1)
    page = client.get(f"/preview/{status['id']}").text
    assert "pydoc-dark" in page and "pydocDark" in page and "invert(1)" in page


# --- previews in their project, and the preview worker ---------------------------------------------------


def test_a_file_is_previewed_with_its_documents_settings(tmp_path):
    """slides.md has [[IF: internal]]: the condition is set by the deck document in py-doc.yml, not the file."""
    import shutil

    from py_doc.web.render import context

    project = tmp_path / "examples"
    shutil.copytree(ROOT / "examples", project, ignore=shutil.ignore_patterns("build", ".py-doc"))
    found = context(project / "docs" / "deck" / "slides.md")
    assert found.conditions == {"internal": False} and found.variables == {"version": "1.0"}
    poster = context(project / "poster" / "landscape.md")  # commissioning: branded in py-doc.yml
    assert poster.poster and "theme" in poster.poster
    loose = context(project / "docs" / "includes" / "audience.md")  # only included: every document's settings
    assert "internal" in loose.conditions and "audience" in loose.conditions


def test_a_file_outside_any_project_has_no_settings(tmp_path):
    from py_doc.web.render import context

    (tmp_path / "a.md").write_text("# A\n", encoding="utf-8")
    found = context(tmp_path / "a.md")
    assert found.variables == {} and found.conditions == {} and found.poster is None


def test_the_worker_answers_each_request_and_keeps_going():
    from py_doc.web.render import REPLY, serve

    def build(kind, source, output):
        if "bad" in str(source):
            raise ValueError("the diagram on line 3 did not draw")
        print("drawing", kind)
        logging.getLogger("py_doc.test").info("Running pandoc")
        return output

    import io
    import logging

    requests = io.StringIO(
        json.dumps({"kind": "preview-deck", "source": "good.md", "output": "a.html"})
        + "\n\n"
        + json.dumps({"kind": "preview-deck", "source": "bad.md", "output": "b.html"})
        + "\nnot json\n"
    )
    replies = io.StringIO()
    logging.getLogger().setLevel(logging.INFO)
    assert serve(requests, replies, build) == 0
    answers = [json.loads(line[len(REPLY) :]) for line in replies.getvalue().splitlines()]
    assert [a["ok"] for a in answers] == [True, False, False]
    assert "drawing preview-deck" in answers[0]["log"] and "Running pandoc" in answers[0]["log"]
    assert "did not draw" in answers[1]["log"]
