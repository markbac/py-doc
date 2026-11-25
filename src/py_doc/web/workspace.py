"""The workspace: a folder of projects, and every file operation the explorer asks for.

Every path the page sends is relative to the workspace root and is checked to stay inside it, so no
request can read or write anything else on the server.
"""

from __future__ import annotations

import io
import os
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

HIDDEN = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache"}  # never listed
WEB_DIR = PurePosixPath(".py-doc") / "web"  # the server's own files inside a project: previews and lint reports
MAX_ENTRIES = 20000  # a tree bigger than this is cut short, so one huge folder cannot stall the page
MAX_TEXT = 5 * 1024 * 1024  # files larger than this are not opened in the editor
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".yml", ".yaml", ".json", ".csv", ".tsv", ".py", ".puml", ".iuml", ".plantuml",
    ".dot", ".gv", ".mmd", ".dsl", ".svg", ".html", ".css", ".js", ".lua", ".toml", ".ini", ".cfg", ".xml",
    ".bpmn", ".bpmnt", ".archt", ".d2", ".pikchr", ".tex", ".bib", ".sh", ".ps1", ".gitignore", ".rst", ".adoc",
}  # fmt: skip


class WorkspaceError(Exception):
    """A request the workspace refuses: a path outside it, a missing file, a name already taken."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@dataclass
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # --- paths ---------------------------------------------------------------------------------

    def resolve(self, relative: str | None, *, must_exist: bool = False) -> Path:
        """The real path of ``relative``, which must stay inside the workspace."""
        text = (relative or "").replace("\\", "/").strip("/")
        parts = PurePosixPath(text).parts if text else ()
        if any(part in ("..", "") or ":" in part for part in parts):
            raise WorkspaceError(f"Not a path in the workspace: {relative}")
        path = self.root.joinpath(*parts)
        real = path.resolve()
        if real != self.root and self.root not in real.parents:
            raise WorkspaceError(f"Not a path in the workspace: {relative}")
        if must_exist and not path.exists():
            raise WorkspaceError(f"Not found: {relative}", 404)
        return path

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def project_of(self, relative: str) -> Path:
        """The project folder that ``relative`` is in: its first part."""
        first = (relative or "").replace("\\", "/").strip("/").split("/", 1)[0]
        if not first:
            raise WorkspaceError("Choose a project first")
        return self.resolve(first, must_exist=True)

    # --- listing -------------------------------------------------------------------------------

    def projects(self) -> list[dict]:
        found = []
        for entry in sorted(self.root.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                found.append({"name": entry.name, "config": (entry / "py-doc.yml").is_file()})
        return found

    def tree(self, relative: str) -> dict:
        """The folder ``relative`` and everything below it, folders first, as nested dictionaries."""
        top = self.resolve(relative, must_exist=True)
        if not top.is_dir():
            raise WorkspaceError(f"Not a folder: {relative}")
        count = 0

        def walk(folder: Path) -> list[dict]:
            nonlocal count
            try:
                entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except OSError:
                return []
            children = []
            for entry in entries:
                if entry.name in HIDDEN or entry.is_symlink():
                    continue
                if entry.name == ".py-doc" and folder == top:
                    continue  # previews, reports and caches: not the user's files
                count += 1
                if count > MAX_ENTRIES:
                    break
                node = {"name": entry.name, "path": self.relative(entry)}
                if entry.is_dir():
                    node["type"] = "dir"
                    node["children"] = walk(entry)
                else:
                    info = entry.stat()
                    node.update(type="file", size=info.st_size, modified=info.st_mtime)
                children.append(node)
            return children

        return {"name": top.name, "path": self.relative(top), "type": "dir", "children": walk(top),
                "truncated": count > MAX_ENTRIES}  # fmt: skip

    # --- files ---------------------------------------------------------------------------------

    def read_text(self, relative: str) -> str:
        path = self.resolve(relative, must_exist=True)
        if not path.is_file():
            raise WorkspaceError(f"Not a file: {relative}")
        if path.stat().st_size > MAX_TEXT:
            raise WorkspaceError(f"{path.name} is too large to edit here; download it instead", 413)
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            raise WorkspaceError(f"{path.name} is not a text file", 415)
        return data.decode("utf-8", errors="replace")

    def write_text(self, relative: str, text: str) -> Path:
        path = self.resolve(relative)
        if path == self.root or path.parent == self.root:
            raise WorkspaceError("Files go inside a project")
        if path.is_dir():
            raise WorkspaceError(f"{relative} is a folder")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as handle:  # the line endings the page sends
            handle.write(text)
        return path

    def write_bytes(self, relative: str, data: bytes | io.BufferedIOBase) -> Path:
        path = self.resolve(relative)
        if path == self.root or path.parent == self.root:
            raise WorkspaceError("Files go inside a project")
        if path.is_dir():
            raise WorkspaceError(f"{relative} is a folder")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            if isinstance(data, bytes):
                handle.write(data)
            else:
                shutil.copyfileobj(data, handle, 1024 * 1024)
        return path

    def mkdir(self, relative: str) -> Path:
        path = self.resolve(relative)
        if path == self.root:
            raise WorkspaceError("Give the folder a name")
        if path.exists() and not path.is_dir():
            raise WorkspaceError(f"{relative} is a file")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def move(self, source: str, target: str) -> Path:
        src = self.resolve(source, must_exist=True)
        dst = self.resolve(target)
        if src == self.root or dst == self.root:
            raise WorkspaceError("The workspace itself cannot be moved")
        if dst.exists():
            raise WorkspaceError(f"{target} already exists", 409)
        if src.is_dir() and (dst == src or src in dst.parents):
            raise WorkspaceError("A folder cannot go inside itself")
        if dst.parent == self.root and not src.is_dir():
            raise WorkspaceError("Files go inside a project")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return dst

    def delete(self, relative: str) -> None:
        path = self.resolve(relative, must_exist=True)
        if path == self.root:
            raise WorkspaceError("The workspace itself cannot be deleted")
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, onerror=_writable_and_retry)
        else:
            path.unlink()

    # --- zips ----------------------------------------------------------------------------------

    def extract_zip(self, data: io.BufferedIOBase | bytes, folder: str) -> list[str]:
        """Unpack a zip into ``folder``. A zip whose files are all inside one folder is unpacked without it,
        so a project zipped as ``my-docs/...`` lands in the folder chosen, not a level below."""
        target = self.resolve(folder)
        if target == self.root:
            raise WorkspaceError("Unpack a zip into a project")
        stream = io.BytesIO(data) if isinstance(data, bytes) else data
        try:
            archive = zipfile.ZipFile(stream)
        except zipfile.BadZipFile as exc:
            raise WorkspaceError("That is not a zip file") from exc
        with archive:
            names = [info for info in archive.infolist() if not info.is_dir() and not _junk(info.filename)]
            tops = {info.filename.replace("\\", "/").split("/", 1)[0] for info in names}
            strip = len(tops) == 1 and all("/" in info.filename.replace("\\", "/") for info in names)
            written = []
            for info in names:
                name = info.filename.replace("\\", "/")
                if strip:
                    name = name.split("/", 1)[1]
                destination = f"{self.relative(target)}/{name}" if self.relative(target) != "." else name
                path = self.resolve(destination)  # refuses ../ and absolute names (zip slip)
                if stat.S_ISLNK(info.external_attr >> 16):
                    continue  # links could point anywhere
                with archive.open(info) as source:
                    self.write_bytes(self.relative_path(path), source)
                written.append(self.relative_path(path))
        return written

    def relative_path(self, path: Path) -> str:
        """Like :meth:`relative`, for a path that may not exist yet."""
        return path.relative_to(self.root).as_posix()

    def zip_folder(self, relative: str) -> tuple[str, Path]:
        """A zip of ``relative`` in a temporary file, and the name to download it as."""
        import tempfile

        folder = self.resolve(relative, must_exist=True)
        if not folder.is_dir():
            raise WorkspaceError(f"Not a folder: {relative}")
        handle = tempfile.NamedTemporaryFile(prefix="py-doc-", suffix=".zip", delete=False)
        handle.close()
        with zipfile.ZipFile(handle.name, "w", zipfile.ZIP_DEFLATED) as archive:
            for root, dirs, files in os.walk(folder):
                dirs[:] = [d for d in dirs if d not in HIDDEN and not (Path(root) == folder and d == ".py-doc")]
                for name in files:
                    path = Path(root, name)
                    if not path.is_symlink():
                        archive.write(path, Path(folder.name, path.relative_to(folder)).as_posix())
        return f"{folder.name}.zip", Path(handle.name)


def is_text(path: str) -> bool:
    suffix = PurePosixPath(path).suffix.lower()
    return suffix in TEXT_SUFFIXES or (not suffix and PurePosixPath(path).name.startswith("."))


def _junk(name: str) -> bool:
    parts = name.replace("\\", "/").split("/")
    return "__MACOSX" in parts or parts[-1] in (".DS_Store", "Thumbs.db")


def _writable_and_retry(func, path, _info):  # files Git marks read-only on Windows
    os.chmod(path, stat.S_IWRITE)
    func(path)
