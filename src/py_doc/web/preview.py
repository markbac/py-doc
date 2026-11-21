"""Live previews: an HTML page of one Markdown file, built again whenever a file of its project changes.

The page asks for a preview of a file as a document, a deck or a poster, and polls its status. A save,
an upload or a move in the project marks every preview of that project out of date, and it is built
again in the background. A build that fails keeps the last good page, with the error beside it.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

KINDS = {"document": "preview-document", "deck": "preview-deck", "poster": "preview-poster"}
IDLE = 3600  # a preview nobody has asked about for this long is forgotten
TIMEOUT = 600


@dataclass
class Preview:
    id: str
    source: Path  # the Markdown file
    project: Path
    kind: str
    output: Path
    version: int = 0  # goes up with every good build
    error: str | None = None
    building: bool = False
    pending: bool = False  # a change came while building, so build again when done
    seen: float = field(default_factory=time.time)
    log: str = ""

    def status(self) -> dict:
        return {"id": self.id, "kind": self.kind, "version": self.version, "error": self.error,
                "building": self.building or self.pending, "ready": self.output.is_file()}  # fmt: skip


class PreviewManager:
    def __init__(self, command: list[str] | None = None, timeout: float = TIMEOUT) -> None:
        # The renderer. By default a worker that stays running (python -m py_doc.web.render --serve), so each
        # preview skips starting Python and connecting to the tool container. A ``command`` given instead is
        # run once a preview with KIND SOURCE OUTPUT: tests give a fake one.
        self.command = command
        self.timeout = timeout
        self.worker: subprocess.Popen | None = None
        self.replies: queue.Queue = queue.Queue()
        self.previews: dict[str, Preview] = {}
        self.lock = threading.Lock()
        self.slot = threading.Semaphore(1)  # one preview build at a time: each runs a container or more

    def open(self, source: Path, project: Path, kind: str) -> Preview:
        if kind not in KINDS:
            raise ValueError(f"A preview is one of {', '.join(KINDS)}")
        key = hashlib.sha1(f"{source}|{kind}".encode()).hexdigest()[:16]
        with self.lock:
            self._forget_idle()
            preview = self.previews.get(key)
            if preview is None:
                output = project / ".py-doc" / "web" / "preview" / f"{key}.html"
                preview = Preview(key, source, project, kind, output)
                self.previews[key] = preview
                fresh = True
            else:
                fresh = False
            preview.seen = time.time()
        if fresh or not preview.output.is_file():
            self.schedule(preview)
        return preview

    def get(self, preview_id: str) -> Preview | None:
        with self.lock:
            preview = self.previews.get(preview_id)
        if preview is not None:
            preview.seen = time.time()
        return preview

    def changed(self, path: Path) -> None:
        """A file changed: build again every preview of the project it is in."""
        path = path.resolve()
        with self.lock:
            hit = [p for p in self.previews.values() if p.project == path or p.project in path.parents]
        for preview in hit:
            if path.suffix.lower() == ".html" and path.parent == preview.output.parent:
                continue  # one of the previews themselves
            self.schedule(preview)

    def schedule(self, preview: Preview) -> None:
        with self.lock:
            if preview.building:
                preview.pending = True
                return
            preview.building = True
        threading.Thread(target=self._build, args=(preview,), daemon=True, name=f"preview-{preview.id}").start()

    def _build(self, preview: Preview) -> None:
        while True:
            with self.slot:
                time.sleep(0.2)  # a burst of saves (an upload of many files) builds once
                with self.lock:
                    preview.pending = False
                self._run(preview)
            with self.lock:
                if not preview.pending:
                    preview.building = False
                    return

    def _run(self, preview: Preview) -> None:
        if not preview.source.is_file():
            preview.error = f"{preview.source.name} is no longer there"
            return
        preview.output.parent.mkdir(parents=True, exist_ok=True)
        partial = preview.output.with_suffix(".building.html")
        if self.command:
            ok, log = self._run_once(preview, partial)
        else:
            ok, log = self._ask_worker(preview, partial)
        preview.log = log
        if ok and partial.is_file():
            partial.replace(preview.output)
            preview.error = None
            preview.version += 1
        else:
            preview.error = _reason(log) or "The preview failed"

    def _run_once(self, preview: Preview, partial: Path) -> tuple[bool, str]:
        command = [*self.command, KINDS[preview.kind], str(preview.source), str(partial)]
        try:
            done = subprocess.run(
                command, cwd=preview.source.parent, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=self.timeout, stdin=subprocess.DEVNULL,
            )  # fmt: skip
        except subprocess.TimeoutExpired:
            return False, f"Error: the preview took longer than {self.timeout:.0f} s"
        return done.returncode == 0, (done.stdout or "") + (done.stderr or "")

    def _ask_worker(self, preview: Preview, partial: Path) -> tuple[bool, str]:
        """Have the worker build the preview, starting it first if it is not running."""
        from .render import REPLY

        if self.worker is None or self.worker.poll() is not None:
            self._start_worker()
        assert self.worker is not None and self.worker.stdin is not None
        request = {"kind": KINDS[preview.kind], "source": str(preview.source), "output": str(partial)}
        try:
            self.worker.stdin.write(json.dumps(request) + "\n")
            self.worker.stdin.flush()
        except OSError:
            self._stop_worker()
            return False, "Error: the preview worker stopped; it starts again on the next save"
        deadline = time.monotonic() + self.timeout
        log: list[str] = []
        while True:
            try:
                line = self.replies.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                self._stop_worker()  # stuck: a new one starts with the next preview
                return False, "".join(log) + f"Error: the preview took longer than {self.timeout:.0f} s"
            if line is None:  # the worker ended
                self._stop_worker()
                return False, "".join(log) + "Error: the preview worker stopped; it starts again on the next save"
            if line.startswith(REPLY):
                answer = json.loads(line[len(REPLY) :])
                return bool(answer.get("ok")), "".join(log) + answer.get("log", "")
            log.append(line)  # anything else the worker printed

    def _start_worker(self) -> None:
        from .jobs import _new_group  # its own process group: stopping it stops what it started

        env = {k: v for k, v in os.environ.items() if k != "FORCE_COLOR"}
        env.update(PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", NO_COLOR="1")
        self.worker = subprocess.Popen(
            [sys.executable, "-m", "py_doc.web.render", "--serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env, **_new_group(),
        )  # fmt: skip
        self.replies = queue.Queue()
        threading.Thread(target=_pump, args=(self.worker, self.replies), daemon=True, name="preview-worker").start()

    def _stop_worker(self) -> None:
        if self.worker is not None and self.worker.poll() is None:
            from .jobs import _kill

            _kill(self.worker)
        self.worker = None

    def close(self) -> None:
        """Stop the worker, when the server stops."""
        if self.worker is not None and self.worker.stdin:
            with contextlib.suppress(OSError):
                self.worker.stdin.close()
        self._stop_worker()

    def _forget_idle(self) -> None:
        now = time.time()
        for key in [k for k, p in self.previews.items() if now - p.seen > IDLE and not p.building]:
            self.previews.pop(key, None)


def _reason(log: str) -> str:
    """The lines of the output that say what went wrong, rather than all of it."""
    lines = [line for line in log.splitlines() if line.strip()]
    errors = [line for line in lines if "error" in line.lower()]
    return "\n".join((errors or lines)[-12:])


def _pump(worker: subprocess.Popen, replies: queue.Queue) -> None:
    """Pass the worker's lines on as they come, then None when it ends."""
    assert worker.stdout is not None
    for line in worker.stdout:
        replies.put(line)
    replies.put(None)
