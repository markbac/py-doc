"""Jobs: py-doc commands that the page starts, each run as a process of its own, one or two at a time.

A job keeps its output so the page can show it as it runs, and is forgotten some time after it ends.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")  # colour codes, should a tool print them anyway
KEEP = 50  # finished jobs kept for the page to show
MAX_LOG = 2 * 1024 * 1024  # output kept per job; the rest is cut from the middle


@dataclass
class Job:
    id: str
    title: str
    project: str
    command: list[str]
    cwd: Path
    timeout: float
    after: Callable[[Job], None] | None = None  # run when the job ends, such as reading a lint report
    state: str = "queued"  # queued, running, ok, failed, stopped
    returncode: int | None = None
    log: str = ""
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    result: dict | None = None  # what ``after`` found
    process: subprocess.Popen | None = field(default=None, repr=False)

    def summary(self, with_log: bool = False) -> dict:
        data = {
            "id": self.id, "title": self.title, "project": self.project, "state": self.state,
            "returncode": self.returncode, "created": self.created, "started": self.started,
            "finished": self.finished, "result": self.result,
        }  # fmt: skip
        if with_log:
            data["log"] = self.log
        return data


def py_doc_command(*args: str) -> list[str]:
    """The command line of ``py-doc ARGS`` with the Python running this server."""
    return [sys.executable, "-m", "py_doc", *args]


class JobManager:
    def __init__(self, workers: int = 1, timeout: float = 1800) -> None:
        self.timeout = timeout
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.slots = threading.Semaphore(max(1, workers))
        self.on_finish: list[Callable[[Job], None]] = []

    def start(
        self,
        title: str,
        project: str,
        command: Sequence[str],
        cwd: Path,
        *,
        after: Callable[[Job], None] | None = None,
        timeout: float | None = None,
    ) -> Job:
        job = Job(uuid.uuid4().hex[:12], title, project, list(command), Path(cwd), timeout or self.timeout, after)
        with self.lock:
            self.jobs[job.id] = job
            self._forget_old()
        threading.Thread(target=self._run, args=(job,), daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def list(self) -> list[Job]:
        with self.lock:
            return sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)

    def stop(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None or job.state not in ("queued", "running"):
            return False
        job.state = "stopped"
        if job.process and job.process.poll() is None:
            _kill(job.process)
        return True

    def _forget_old(self) -> None:
        done = sorted((j for j in self.jobs.values() if j.finished), key=lambda j: j.finished or 0)
        for job in done[: max(0, len(done) - KEEP)]:
            self.jobs.pop(job.id, None)

    def _append(self, job: Job, text: str) -> None:
        job.log += ANSI.sub("", text)
        if len(job.log) > MAX_LOG:
            half = MAX_LOG // 2
            job.log = job.log[:half] + "\n... (output cut) ...\n" + job.log[-half:]

    def _run(self, job: Job) -> None:
        with self.slots:
            if job.state == "stopped":
                job.finished = time.time()
                return
            job.state, job.started = "running", time.time()
            self._append(job, "$ " + " ".join(_shown(job.command)) + "\n")
            env = {k: v for k, v in os.environ.items() if k != "FORCE_COLOR"}
            env.update(PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", NO_COLOR="1")
            try:
                job.process = subprocess.Popen(
                    job.command, cwd=job.cwd, env=env, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                    **_new_group(),
                )  # fmt: skip
            except OSError as exc:
                self._append(job, f"Could not start: {exc}\n")
                job.state, job.finished = "failed", time.time()
                return
            timer = threading.Timer(job.timeout, self._time_out, args=(job,))
            timer.start()
            try:
                assert job.process.stdout is not None
                for line in job.process.stdout:
                    self._append(job, line)
                job.returncode = job.process.wait()
            finally:
                timer.cancel()
            if job.state != "stopped":
                job.state = "ok" if job.returncode == 0 else "failed"
            if job.after is not None:
                try:
                    job.after(job)
                except Exception as exc:  # a report that could not be read is shown, not raised
                    self._append(job, f"\nCould not read the result: {exc}\n")
            job.finished = time.time()
            for callback in self.on_finish:
                callback(job)

    def _time_out(self, job: Job) -> None:
        if job.process and job.process.poll() is None:
            self._append(job, f"\nStopped after {job.timeout:.0f} s\n")
            job.state = "stopped"
            _kill(job.process)


def _shown(command: list[str]) -> list[str]:
    """The command as the user would type it: ``py-doc ...`` rather than the Python path."""
    if command[:3] == [sys.executable, "-m", "py_doc"]:
        return ["py-doc", *command[3:]]
    if command[:3] == [sys.executable, "-m", "py_doc.web.render"]:
        return ["render", *command[3:]]
    return command


def _new_group() -> dict:
    """Start the process in a group of its own, so stopping it stops what it started too."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill(process: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
        else:
            import signal

            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
