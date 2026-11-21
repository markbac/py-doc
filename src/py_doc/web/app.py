"""The web server: the page, its files, and the API the page uses."""

from __future__ import annotations

import base64
import hmac
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from starlette.background import BackgroundTask

from .. import __version__
from .jobs import Job, JobManager, py_doc_command
from .preview import KINDS as PREVIEW_KINDS
from .preview import PreviewManager
from .render import KINDS as RENDER_KINDS
from .workspace import WEB_DIR, Workspace, WorkspaceError

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}$")  # a project's folder name
CONVERT = {  # what one file converts to: the kind, the suffix, and how the page names it
    "docx": (".docx", "Word"),
    "pptx": (".pptx", "PowerPoint"),
    "pdf": (".pdf", "PDF"),
    "html": (".html", "HTML page"),
    "deck": (".deck.html", "HTML deck"),
    "poster": (".poster.html", "Poster"),
}
BUILD_FORMATS = ("docx", "html", "pdf", "pptx", "poster")
# Added to a preview page: keep the place on the page when it is built again. The page is sandboxed, so it
# tells the explorer where it is by message, and is told where to go back to by the address's #y=.
SCROLL = """<script>(function(){var m=/[#&]y=(\\d+)/.exec(location.hash);
if(m){var y=+m[1];var go=function(){window.scrollTo(0,y);};go();addEventListener('load',go);setTimeout(go,300);}
addEventListener('load',function(){parent.postMessage({pydocLoaded:document.title},'*');});
var t;addEventListener('scroll',function(){clearTimeout(t);t=setTimeout(function(){
parent.postMessage({pydocScroll:Math.round(window.scrollY)},'*');},100);});})();</script>"""


@dataclass
class Settings:
    root: Path
    password: str | None = None  # when set, the page asks for it (HTTP Basic, any user name)
    user: str = "py-doc"
    workers: int = 1  # jobs run at the same time
    timeout: float = 1800  # seconds a job may take
    output_dir: str = "out"  # where single-file conversions go, inside the project


class SaveBody(BaseModel):
    path: str
    text: str


class PathBody(BaseModel):
    path: str


class MoveBody(BaseModel):
    source: str
    target: str


class ProjectBody(BaseModel):
    name: str
    init: bool = False
    title: str | None = None


class ConvertBody(BaseModel):
    path: str
    kind: str


class BuildBody(BaseModel):
    project: str
    format: str | None = None
    documents: list[str] = []
    lint: bool = False
    site: bool = False


class LintBody(BaseModel):
    path: str  # a project, a folder or a file


class PreviewBody(BaseModel):
    path: str
    kind: str = "document"


def create_app(settings: Settings, jobs: JobManager | None = None, previews: PreviewManager | None = None) -> FastAPI:
    workspace = Workspace(settings.root)
    jobs = jobs or JobManager(settings.workers, settings.timeout)
    previews = previews or PreviewManager()
    app = FastAPI(title="py-doc web", version=__version__, docs_url=None, redoc_url=None)
    app.state.workspace, app.state.jobs, app.state.previews = workspace, jobs, previews

    # --- sign-in -------------------------------------------------------------------------------

    @app.middleware("http")
    async def password(request: Request, call_next):
        if (
            settings.password
            and request.url.path != "/healthz"
            and not _signed_in(request.headers.get("authorization"), settings.password)
        ):
            return Response("Sign in to py-doc", 401, {"WWW-Authenticate": 'Basic realm="py-doc", charset="UTF-8"'})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    @app.exception_handler(WorkspaceError)
    async def refused(_request: Request, exc: WorkspaceError):
        return JSONResponse({"error": str(exc)}, exc.status)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    # --- the page ------------------------------------------------------------------------------

    static = resources.files("py_doc.web") / "static"

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(static.joinpath("index.html").read_text(encoding="utf-8"), headers=_no_store())

    @app.get("/static/{name}")
    def asset(name: str):
        if "/" in name or "\\" in name or name.startswith("."):
            return Response(status_code=404)
        item = static.joinpath(name)
        if not item.is_file():
            return Response(status_code=404)
        kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
        return Response(item.read_bytes(), media_type=kind, headers=_no_store())

    @app.get("/api/info")
    def info():
        return {"version": __version__, "root": str(workspace.root), "convert": {k: v[1] for k, v in CONVERT.items()},
                "build_formats": BUILD_FORMATS, "preview_kinds": list(PREVIEW_KINDS)}  # fmt: skip

    # --- projects and files --------------------------------------------------------------------

    @app.get("/api/projects")
    def projects():
        return workspace.projects()

    @app.post("/api/projects")
    def new_project(body: ProjectBody):
        name = body.name.strip()
        if not NAME.match(name):
            raise WorkspaceError("A project name is letters, digits, spaces, dots, dashes and underscores")
        path = workspace.resolve(name)
        if path.exists():
            raise WorkspaceError(f"{name} already exists", 409)
        if body.init:
            job = jobs.start(
                f"New project {name}", name,
                py_doc_command("init", name, "--name", body.title or name, "-y"), workspace.root,
            )  # fmt: skip
            return {"name": name, "job": job.summary()}
        path.mkdir()
        return {"name": name}

    @app.get("/api/tree")
    def tree(path: str = Query(...)):
        return workspace.tree(path)

    @app.get("/api/file")
    def read_file(path: str = Query(...)):
        full = workspace.resolve(path, must_exist=True)
        return {"path": path, "text": workspace.read_text(path), "modified": full.stat().st_mtime}

    @app.put("/api/file")
    def save_file(body: SaveBody):
        full = workspace.write_text(body.path, body.text)
        previews.changed(full)
        return {"path": body.path, "modified": full.stat().st_mtime}

    @app.post("/api/mkdir")
    def mkdir(body: PathBody):
        workspace.mkdir(body.path)
        return {"path": body.path}

    @app.post("/api/move")
    def move(body: MoveBody):
        moved = workspace.move(body.source, body.target)
        previews.changed(moved)
        return {"path": body.target}

    @app.delete("/api/path")
    def delete(path: str = Query(...)):
        full = workspace.resolve(path, must_exist=True)
        workspace.delete(path)
        previews.changed(full)
        return {"deleted": path}

    @app.post("/api/upload")
    def upload(folder: str = Form(...), files: list[UploadFile] = File(...), paths: str = Form("[]"),
               unzip: bool = Form(False)):  # fmt: skip
        """Files dropped on a folder. ``paths`` gives each file's path below the folder, for a dropped folder;
        a zip is unpacked when ``unzip`` is set."""
        relative = json.loads(paths) if paths else []
        written: list[str] = []
        for index, upload_file in enumerate(files):
            name = relative[index] if index < len(relative) and relative[index] else upload_file.filename or "file"
            name = name.replace("\\", "/").lstrip("/")
            if unzip and name.lower().endswith(".zip"):
                written += workspace.extract_zip(
                    upload_file.file, f"{folder}/{PurePosixPath(name).parent}".rstrip("/.")
                )
                continue
            path = f"{folder.rstrip('/')}/{name}"
            workspace.write_bytes(path, upload_file.file)
            written.append(path)
        if written:
            previews.changed(workspace.resolve(written[0]))
        return {"written": written}

    @app.get("/api/download")
    def download(path: str = Query(...)):
        full = workspace.resolve(path, must_exist=True)
        if full.is_dir():
            name, archive = workspace.zip_folder(path)
            return FileResponse(archive, filename=name, media_type="application/zip",
                                background=BackgroundTask(os.unlink, archive))  # fmt: skip
        return FileResponse(full, filename=full.name)

    @app.get("/raw/{path:path}")
    def raw(path: str):
        """A file as it is, for the explorer's picture view and a page's links. HTML is shown as text unless
        it is a py-doc output, so an uploaded page cannot act as this site."""
        full = workspace.resolve(path, must_exist=True)
        if not full.is_file():
            raise WorkspaceError(f"Not a file: {path}", 404)
        kind = mimetypes.guess_type(full.name)[0] or "application/octet-stream"
        headers = {"Cache-Control": "no-store", "Content-Security-Policy": "sandbox allow-scripts allow-popups"}
        return FileResponse(full, media_type=kind, headers=headers)

    # --- converting, building and linting -------------------------------------------------------

    @app.post("/api/convert")
    def convert(body: ConvertBody):
        if body.kind not in CONVERT:
            raise WorkspaceError(f"Convert to one of {', '.join(CONVERT)}")
        source = workspace.resolve(body.path, must_exist=True)
        if source.suffix.lower() not in (".md", ".markdown"):
            raise WorkspaceError("Only Markdown files are converted")
        project = workspace.project_of(body.path)
        below = source.relative_to(project).with_suffix("")
        output = project / settings.output_dir / f"{below.as_posix()}{CONVERT[body.kind][0]}"
        assert body.kind in RENDER_KINDS
        command = [jobs_python(), "-m", "py_doc.web.render", body.kind, str(source), str(output)]

        def found(job: Job) -> None:
            if output.is_file():
                job.result = {"outputs": [workspace.relative(output)]}

        job = jobs.start(f"{source.name} to {CONVERT[body.kind][1]}", project.name, command, source.parent,
                         after=found)  # fmt: skip
        return job.summary()

    @app.post("/api/build")
    def build(body: BuildBody):
        project = workspace.project_of(body.project)
        if not (project / "py-doc.yml").is_file():
            raise WorkspaceError(f"{project.name} has no py-doc.yml, so convert its files one at a time instead")
        args = ["build", *body.documents]
        if body.format:
            if body.format not in BUILD_FORMATS:
                raise WorkspaceError(f"Build one of {', '.join(BUILD_FORMATS)}")
            args += ["-f", body.format]
        if body.lint:
            args.append("--lint")
        args.append("--site" if body.site else "--no-site")
        title = f"Build {project.name}" + (f" ({body.format})" if body.format else "")
        return jobs.start(title, project.name, py_doc_command(*args), project).summary()

    @app.post("/api/check")
    def check(body: PathBody):
        project = workspace.project_of(body.path)
        return jobs.start(f"Check {project.name}", project.name, py_doc_command("check"), project).summary()

    @app.post("/api/lint")
    def lint(body: LintBody):
        target = workspace.resolve(body.path, must_exist=True)
        project = workspace.project_of(body.path)
        report = project / WEB_DIR / "lint.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.unlink(missing_ok=True)

        def read(job: Job) -> None:
            if not report.is_file():
                return
            data = json.loads(report.read_text(encoding="utf-8"))
            for issue in data.get("issues", []) + data.get("errors", []):
                issue["path"] = _workspace_path(workspace, issue.get("file"), project)
            job.result = {"lint": data}

        command = py_doc_command("lint", str(target), "--format", "json", "--output", str(report))
        return jobs.start(f"Lint {workspace.relative(target)}", project.name, command, project, after=read).summary()

    @app.get("/api/jobs")
    def list_jobs():
        return [job.summary() for job in jobs.list()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str, since: int = 0):
        job = jobs.get(job_id)
        if job is None:
            raise WorkspaceError("No such job", 404)
        data = job.summary()
        data["log"], data["length"] = job.log[since:], len(job.log)
        return data

    @app.post("/api/jobs/{job_id}/stop")
    def stop_job(job_id: str):
        return {"stopped": jobs.stop(job_id)}

    # --- live previews -------------------------------------------------------------------------

    @app.post("/api/preview")
    def open_preview(body: PreviewBody):
        source = workspace.resolve(body.path, must_exist=True)
        if source.suffix.lower() not in (".md", ".markdown"):
            raise WorkspaceError("Only Markdown files have a preview")
        if body.kind not in PREVIEW_KINDS:
            raise WorkspaceError(f"A preview is one of {', '.join(PREVIEW_KINDS)}")
        preview = previews.open(source.resolve(), workspace.project_of(body.path).resolve(), body.kind)
        return preview.status()

    @app.get("/api/preview/{preview_id}")
    def preview_status(preview_id: str):
        preview = previews.get(preview_id)
        if preview is None:
            raise WorkspaceError("That preview has ended; open it again", 404)
        data = preview.status()
        if preview.error:
            data["log"] = preview.log[-20000:]
        return data

    @app.get("/preview/{preview_id}")
    def preview_page(preview_id: str):
        preview = previews.get(preview_id)
        if preview is None or not preview.output.is_file():
            return HTMLResponse("<!doctype html><p style='font:15px sans-serif;color:#777;padding:1em'>Building the "
                                "preview...</p>", headers=_no_store())  # fmt: skip
        page = preview.output.read_text(encoding="utf-8", errors="replace")
        page = page.replace("</body>", SCROLL + "</body>", 1) if "</body>" in page else page + SCROLL
        # The page is the user's Markdown made HTML, so it runs in a sandbox of its own, away from this site
        headers = {**_no_store(), "Content-Security-Policy": "sandbox allow-scripts allow-popups allow-modals"}
        return HTMLResponse(page, headers=headers)

    return app


def jobs_python() -> str:
    import sys

    return sys.executable


def _signed_in(header: str | None, password: str) -> bool:
    if not header or not header.lower().startswith("basic "):
        return False
    try:
        _user, _, given = base64.b64decode(header[6:]).decode("utf-8").partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    return hmac.compare_digest(given.encode(), password.encode())


def _no_store() -> dict:
    return {"Cache-Control": "no-store"}


def _workspace_path(workspace: Workspace, file: str | None, project: Path) -> str | None:
    """A file named in a lint report, relative to the workspace, or None when it is outside it."""
    if not file:
        return None
    path = Path(file)
    if not path.is_absolute():
        path = project / path
    try:
        return workspace.relative(path)
    except ValueError:
        return None
