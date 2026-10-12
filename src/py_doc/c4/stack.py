"""The Structurizr Local container that draws the views, run through the container engine.

Structurizr Local (``structurizr/structurizr local``) replaces Structurizr Lite, which gets no more updates.
The diagrams are drawn in a browser, so styles, themes and icons are exactly what the team sees. py-doc starts
Local on its own network, lets the tool container's headless Chromium open it, and stops it afterwards if it
started it.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Runtime

logger = logging.getLogger(__name__)

NETWORK = "py-doc-c4"
SERVER = "py-doc-c4-local"
SERVER_IMAGE = "structurizr/structurizr"
SERVER_PORT = 8080
READY_SECONDS = 120


class Stack:
    network: str | bool = NETWORK  # what the tool container joins to reach Local

    def __init__(self, runtime: Runtime, workspace: Path, *, image: str = SERVER_IMAGE, port: int = SERVER_PORT) -> None:
        """``workspace`` is the ``.dsl`` or ``workspace.json`` file. Local is given its folder."""
        self.runtime = runtime
        self.file = Path(workspace).resolve()
        self.workspace = self.file.parent
        self.image = image
        self.port = port
        self._staged: Path | None = None

    @property
    def url(self) -> str:
        """Where the tool container reaches Local, on the shared network."""
        return f"http://{SERVER}:{SERVER_PORT}/workspace/diagrams"

    def status(self) -> str:
        """``running``, ``stopped`` or ``absent``."""
        result = self.runtime.engine(["inspect", "--format", "{{.State.Running}}", SERVER], check=False)
        if result.returncode != 0:
            return "absent"
        return "running" if result.stdout.strip() == "true" else "stopped"

    def up(self) -> bool:
        """Start Local. Returns True if this call started it, False if it was already running."""
        state = self.status()
        if state == "running":
            return False
        if state == "stopped":
            self.runtime.engine(["rm", "-f", SERVER])
        if self.runtime.engine(["network", "inspect", NETWORK], check=False).returncode != 0:
            self.runtime.engine(["network", "create", NETWORK])
        folder = self.runtime.container_path(self._folder())
        args = ["run", "-d", "--name", SERVER, "--network", NETWORK, "-p", f"127.0.0.1:{self.port}:{SERVER_PORT}"]
        args += ["--mount", f"type=bind,source={folder},target=/usr/local/structurizr"]
        # Drawing must not change the project: no auto-save, and the diagrams are read-only
        args += ["-e", "STRUCTURIZR_AUTOSAVEINTERVAL=0", "-e", "STRUCTURIZR_EDITABLE=false"]
        args += [self.image, "local"]
        try:
            self.runtime.engine(args, timeout=600)
        except ToolFailed as exc:
            raise ConversionError(f"Structurizr Local did not start: {exc}") from exc
        self._wait()
        return True

    def _folder(self) -> Path:
        """The folder Local reads. It only opens ``workspace.dsl`` or ``workspace.json``, so a workspace with
        another name is copied, with its neighbours (for ``!include``), into a folder of its own."""
        if self.file.stem == "workspace":
            return self.workspace
        self._staged = Path(tempfile.mkdtemp(prefix="py-doc-c4-"))
        folder = self._staged / "workspace"
        shutil.copytree(self.workspace, folder, ignore=shutil.ignore_patterns("workspace.dsl", "workspace.json", ".git", "node_modules"))
        shutil.copy2(self.file, folder / f"workspace{self.file.suffix}")
        return folder

    def _wait(self) -> None:
        url = f"http://127.0.0.1:{self.port}/workspace"
        deadline = time.monotonic() + READY_SECONDS
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as reply:  # noqa: S310
                    if reply.status < 500:
                        logger.info("Structurizr Local is ready")
                        return
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(2)
        logs = self.runtime.engine(["logs", "--tail", "30", SERVER], check=False)
        self.down()
        raise ConversionError(
            f"Structurizr Local did not answer within {READY_SECONDS} seconds.\n{(logs.stdout + logs.stderr).strip()}"
        )

    def down(self) -> None:
        self.runtime.engine(["rm", "-f", SERVER], check=False)
        self.runtime.engine(["network", "rm", NETWORK], check=False)
        if self._staged is not None:
            shutil.rmtree(self._staged, ignore_errors=True)
            self._staged = None


class ExternalStack:
    """A Structurizr Local or server that is already running (``--url``). py-doc neither starts nor stops it."""

    network: str | bool = True

    def __init__(self, url: str) -> None:
        base = url.rstrip("/")
        self.url = base if base.endswith("/diagrams") else f"{base}/workspace/diagrams"

    def up(self) -> bool:
        return False

    def down(self) -> None:
        return None
