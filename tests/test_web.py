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
