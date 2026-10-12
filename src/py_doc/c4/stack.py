"""The Structurizr Local container that draws the views, run through the container engine.

Structurizr Local (``structurizr/structurizr local``) replaces Structurizr Lite, which gets no more updates.
The diagrams are drawn in a browser, so styles, themes and icons are exactly what the team sees. py-doc starts
Local on its own network, lets the tool container's headless Chromium open it, and stops it afterwards if it
started it.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import time
from pathlib import Path

from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Runtime

logger = logging.getLogger(__name__)

NETWORK = "py-doc-c4"
SERVER = "py-doc-c4-local"
SERVER_IMAGE = "structurizr/structurizr"
SERVER_PORT = 8080
READY_SECONDS = 300  # the first start of the Java server can take minutes on a busy machine
POLL_SECONDS = 3
NOTE_SECONDS = 30  # how often the wait says it is still waiting
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Structurizr Local only answers requests for ``localhost`` (any other host name gets a 400, so its scripts and
# styles fail to load). The tool container therefore shares Local's network namespace, where ``localhost`` is Local.
# The probe exits 0 once the diagrams page answers properly, on that same route, so it proves what the pictures need.
PROBE = (
    "const r = require('http').get(process.argv[1], x => process.exit(x.statusCode < 400 ? 0 : 1));"
    "r.on('error', () => process.exit(1)); r.setTimeout(5000, () => process.exit(1));"
)


class Stack:
    network: str | bool = f"container:{SERVER}"  # the tool container shares Local's network, so Local is localhost

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
        return f"http://localhost:{SERVER_PORT}/workspace/diagrams"

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
        url = self.url
        started = time.monotonic()
        next_note = NOTE_SECONDS
        logger.info("Waiting for Structurizr Local to start (up to %d seconds)", READY_SECONDS)
        while True:
            elapsed = time.monotonic() - started
            if self.status() != "running":
                self._fail("Structurizr Local stopped while starting.")
            if self.runtime.run(["node", "-e", PROBE, url], network=self.network, check=False, timeout=60).returncode == 0:
                logger.info("Structurizr Local is ready after %d seconds", elapsed)
                return
            if elapsed >= READY_SECONDS:
                self._fail(f"Structurizr Local did not answer within {READY_SECONDS} seconds.")
            if elapsed >= next_note:
                logger.info("Still waiting for Structurizr Local (%d of %d seconds)", elapsed, READY_SECONDS)
                next_note += NOTE_SECONDS
            time.sleep(POLL_SECONDS)

    def _fail(self, message: str) -> None:
        logs = self.runtime.engine(["logs", "--tail", "15", SERVER], check=False)
        text = _ANSI.sub("", logs.stdout + logs.stderr).strip()
        self.down()
        raise ConversionError(f"{message}\n{text}" if text else message)

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
