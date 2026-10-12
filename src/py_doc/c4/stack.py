"""The Structurizr Lite container that draws the views, run through the container engine.

Lite is the route the Structurizr documentation gives for PNG and SVG: the diagrams are drawn in a browser,
so styles, themes and icons are exactly what the team sees. py-doc starts Lite on its own network, lets the
tool container's headless Chromium open it, and stops it afterwards if it started it.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Runtime

logger = logging.getLogger(__name__)

NETWORK = "py-doc-c4"
LITE = "py-doc-c4-lite"
LITE_IMAGE = "structurizr/lite"
LITE_PORT = 8080
READY_SECONDS = 120


class Stack:
    network: str | bool = NETWORK  # what the tool container joins to reach Lite

    def __init__(self, runtime: Runtime, workspace: Path, *, image: str = LITE_IMAGE, port: int = LITE_PORT) -> None:
        """``workspace`` is the ``.dsl`` or ``workspace.json`` file. Lite is given its folder."""
        self.runtime = runtime
        self.file = Path(workspace).resolve()
        self.workspace = self.file.parent
        self.image = image
        self.port = port

    @property
    def url(self) -> str:
        """Where the tool container reaches Lite, on the shared network."""
        return f"http://{LITE}:{LITE_PORT}/workspace/diagrams"

    def status(self) -> str:
        """``running``, ``stopped`` or ``absent``."""
        result = self.runtime.engine(["inspect", "--format", "{{.State.Running}}", LITE], check=False)
        if result.returncode != 0:
            return "absent"
        return "running" if result.stdout.strip() == "true" else "stopped"

    def up(self) -> bool:
        """Start Lite. Returns True if this call started it, False if it was already running."""
        state = self.status()
        if state == "running":
            return False
        if state == "stopped":
            self.runtime.engine(["rm", "-f", LITE])
        if self.runtime.engine(["network", "inspect", NETWORK], check=False).returncode != 0:
            self.runtime.engine(["network", "create", NETWORK])
        folder = self.runtime.container_path(self.workspace)
        name = self._workspace_name()
        args = ["run", "-d", "--name", LITE, "--network", NETWORK, "-p", f"127.0.0.1:{self.port}:{LITE_PORT}"]
        args += ["--mount", f"type=bind,source={folder},target=/usr/local/structurizr"]
        if name:
            args += ["-e", f"STRUCTURIZR_WORKSPACE_FILENAME={name}"]
        args.append(self.image)
        try:
            self.runtime.engine(args, timeout=600)
        except ToolFailed as exc:
            raise ConversionError(f"Structurizr Lite did not start: {exc}") from exc
        self._wait()
        return True

    def _workspace_name(self) -> str | None:
        return None if self.file.stem == "workspace" else self.file.stem

    def _wait(self) -> None:
        url = f"http://127.0.0.1:{self.port}/workspace"
        deadline = time.monotonic() + READY_SECONDS
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as reply:  # noqa: S310
                    if reply.status < 500:
                        logger.info("Structurizr Lite is ready")
                        return
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(2)
        logs = self.runtime.engine(["logs", "--tail", "30", LITE], check=False)
        self.down()
        raise ConversionError(
            f"Structurizr Lite did not answer within {READY_SECONDS} seconds.\n{(logs.stdout + logs.stderr).strip()}"
        )

    def down(self) -> None:
        self.runtime.engine(["rm", "-f", LITE], check=False)
        self.runtime.engine(["network", "rm", NETWORK], check=False)


class ExternalStack:
    """A Structurizr Lite or server that is already running (``--url``). py-doc neither starts nor stops it."""

    network: str | bool = True

    def __init__(self, url: str) -> None:
        base = url.rstrip("/")
        self.url = base if base.endswith("/diagrams") else f"{base}/workspace/diagrams"

    def up(self) -> bool:
        return False

    def down(self) -> None:
        return None
