"""The tool runner: start a program in a container and report what happened.

Rules the runner keeps for every call:

- The command is an argument list. No shell is involved, on either platform.
- Paths in the arguments are translated for the engine (``wslpath`` on Windows) and must lie under a
  mount, so a tool can never be pointed at a file it was not given.
- Inputs are read-only unless a mount says otherwise, and there is no network unless a step asks.
- The container runs as the calling user, so files it writes belong to that user.
- A failing tool raises an error that carries its whole output. Nothing is turned into a warning.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..errors import EnvironmentProblem, ToolFailed, ToolTimeout
from ..platform import require_supported

logger = logging.getLogger(__name__)

CACHE_VOLUME = "py-doc-cache"
CACHE_DIR = "/cache"
DEFAULT_TIMEOUT = 600.0

_DAEMON_DOWN = (
    "cannot connect to the docker daemon",
    "failed to connect to the docker api",
    "is the docker daemon running",
)
_NO_DOCKER = ("execvpe(docker) failed", "docker: command not found", 'executable file not found in $path')
_IMAGE_MISSING = ("unable to find image", "no such image", "pull access denied")
_MISSING_BIND = "bind source path does not exist"


@dataclass(frozen=True)
class Mount:
    """A host folder made visible to the tool at the same (engine-side) path. Read-only by default."""

    source: str | os.PathLike
    writable: bool = False


@dataclass
class ToolResult:
    returncode: int
    stdout: str
    stderr: str


def decode_wsl(data: bytes) -> str:
    """Text from ``wsl.exe`` itself (not from a program run through it), which writes UTF-16."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in data[:8]:
        return data.decode("utf-16", errors="replace").lstrip("﻿")
    return data.decode("utf-8", errors="replace")


def _command(value: str | Sequence[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def _csv_field(text: str) -> str:
    """A value for ``--mount``, which splits on commas, quoted when it holds a comma or a quote."""
    return '"' + text.replace('"', '""') + '"' if ("," in text or '"' in text) else text


class Runtime:
    """Docker on Linux, or Docker inside a WSL distro on Windows."""

    def __init__(
        self,
        image: str,
        *,
        docker: str | Sequence[str] = "docker",
        wsl_distro: str | None = None,
        wsl_exe: str | Sequence[str] = "wsl.exe",
        platform_name: str | None = None,
        cache_volume: str | None = CACHE_VOLUME,
    ):
        self.image = image
        self.platform = platform_name or require_supported()
        self.docker = _command(docker)
        self.wsl_distro = wsl_distro
        self.wsl_exe = _command(wsl_exe)
        self.cache_volume = cache_volume
        self._paths: dict[str, str] = {}
        self._ids: tuple[int, int] | None = None

    # --- reaching the engine -----------------------------------------------------------------

    @property
    def windows(self) -> bool:
        return self.platform == "windows"

    def _prefix(self) -> list[str]:
        """What starts a program inside the engine's world."""
        if not self.windows:
            return []
        return [*self.wsl_exe, *(["-d", self.wsl_distro] if self.wsl_distro else []), "--exec"]

    def _spawn(self, args: Sequence[str], *, capture_input: bytes | None = None) -> subprocess.Popen:
        command = [*self._prefix(), *args]
        logger.debug("Running: %s", " ".join(command))
        try:
            return subprocess.Popen(
                command,
                stdin=subprocess.PIPE if capture_input is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            if self.windows and command[0] == self.wsl_exe[0]:
                raise EnvironmentProblem(
                    "wsl.exe was not found. Install WSL 2 (`wsl --install`) and Docker Engine inside the distro"
                ) from exc
            raise EnvironmentProblem(
                f"'{command[0]}' was not found. Install Docker Engine, or set runtime.docker in py-doc.yml"
            ) from exc

    def _execute(
        self,
        args: Sequence[str],
        *,
        timeout: float | None,
        stdin: bytes | None = None,
        stream: bool = False,
        on_line: Callable[[str], None] | None = None,
    ) -> tuple[int | None, bytes, bytes]:
        """Run ``args`` in the engine's world. Returns (exit status or None on timeout, stdout, stderr)."""
        proc = self._spawn(args, capture_input=stdin)
        chunks: dict[str, list[bytes]] = {"out": [], "err": []}

        def pump(pipe, key: str) -> None:
            for line in iter(pipe.readline, b""):
                chunks[key].append(line)
                if stream or on_line:
                    text = line.decode("utf-8", errors="replace").rstrip()
                    logger.debug("%s", text)
                    if on_line:
                        on_line(text)
            pipe.close()

        threads = [
            threading.Thread(target=pump, args=(proc.stdout, "out")),
            threading.Thread(target=pump, args=(proc.stderr, "err")),
        ]
        for thread in threads:
            thread.start()
        if stdin is not None:
            try:
                proc.stdin.write(stdin)
                proc.stdin.close()
            except OSError:
                pass
        try:
            code: int | None = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            code = None
        for thread in threads:
            thread.join()
        return code, b"".join(chunks["out"]), b"".join(chunks["err"])

    def _execute_host(self, command: Sequence[str]) -> tuple[int, bytes, bytes]:
        """Run a program on the host itself (such as ``wsl.exe -l``), not inside the engine."""
        try:
            done = subprocess.run(list(command), capture_output=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return 1, b"", b""
        return done.returncode, done.stdout, done.stderr

    def engine(
        self,
        args: Sequence[str],
        *,
        timeout: float | None = 60,
        check: bool = True,
        stream: bool = False,
        on_line: Callable[[str], None] | None = None,
    ) -> ToolResult:
        """Run ``docker <args>`` (build, image inspect, info, and so on). ``on_line`` sees each output line as it arrives."""
        code, out, err = self._execute([*self.docker, *args], timeout=timeout, stream=stream, on_line=on_line)
        if code is None:
            raise ToolTimeout("docker " + args[0], timeout or 0)
        result = ToolResult(code, _text(out), _text(err))
        if code != 0:
            self._raise_environment(result, running=True)
            if check:
                raise ToolFailed("docker " + args[0], code, result.stderr or result.stdout)
        return result

    def _raise_environment(self, result: ToolResult, running: bool = False) -> None:
        """Turn the engine's own failures into environment problems, with what to do about them."""
        low = result.stderr.lower()
        if any(marker in low for marker in _NO_DOCKER):
            where = "inside the WSL distro (`wsl -d <distro>`, then follow https://docs.docker.com/engine/install/ubuntu/)" if self.windows else "(https://docs.docker.com/engine/install/)"
            raise EnvironmentProblem(
                f"Docker Engine is not installed {where}. "
                "Set runtime.wsl_distro in py-doc.yml if Docker is in a distro other than the default"
            )
        if any(marker in low for marker in _DAEMON_DOWN):
            hint = (
                "Start it inside the WSL distro, for example `sudo service docker start`"
                if self.windows
                else "Start it, for example `sudo systemctl start docker`"
            )
            raise EnvironmentProblem(f"The Docker engine is not running. {hint}")
        if running:  # engine commands such as `image inspect` report a missing image themselves
            return
        if any(marker in low for marker in _IMAGE_MISSING):
            raise EnvironmentProblem(f"The tool image '{self.image}' is not built here. Run `py-doc tools build`")
        if _MISSING_BIND in low:
            raise EnvironmentProblem(f"A folder given to the tool does not exist: {result.stderr.strip()}")

    # --- paths ---------------------------------------------------------------------------------

    def container_path(self, path: str | os.PathLike) -> str:
        """The path of ``path`` as the engine and the tool see it."""
        text = os.fspath(path)
        if text in self._paths:
            return self._paths[text]
        if self.windows:
            code, out, err = self._execute(["wslpath", "-a", "-u", text], timeout=30)
            converted = out.decode("utf-8", errors="replace").strip()
            if code != 0 or not converted:
                raise EnvironmentProblem(f"WSL cannot see '{text}': {err.decode('utf-8', errors='replace').strip()}")
        else:
            converted = Path(text).resolve().as_posix()
        self._paths[text] = converted
        return converted

    def user(self) -> str:
        """``uid:gid`` of the calling user, in the engine's world."""
        if self._ids is None:
            if self.windows:
                values = []
                for flag in ("-u", "-g"):
                    code, out, _ = self._execute(["id", flag], timeout=30)
                    if code != 0 or not out.strip().isdigit():
                        raise EnvironmentProblem("Cannot read the user id inside WSL (`id` failed)")
                    values.append(int(out.strip()))
                self._ids = (values[0], values[1])
            else:
                self._ids = (os.getuid(), os.getgid())
        return f"{self._ids[0]}:{self._ids[1]}"

    # --- running a tool ------------------------------------------------------------------------

    def run(
        self,
        argv: Sequence[str | os.PathLike],
        *,
        mounts: Sequence[Mount] = (),
        workdir: str | os.PathLike | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        network: bool | str = False,
        shm_size: str | None = None,
        image: str | None = None,
        check: bool = True,
    ) -> ToolResult:
        """Run ``argv`` in a fresh container. ``Path`` arguments are translated and must lie under a mount."""
        if not argv:
            raise ValueError("argv is empty")
        mounted = [(self.container_path(m.source), m.writable) for m in mounts]

        def covered(cpath: str) -> bool:
            return any(cpath == root or cpath.startswith(root.rstrip("/") + "/") for root, _ in mounted)

        words: list[str] = []
        for item in argv:
            if isinstance(item, os.PathLike):
                cpath = self.container_path(item)
                if not covered(cpath):
                    raise EnvironmentProblem(f"'{os.fspath(item)}' is not under any folder given to the tool")
                words.append(cpath)
            else:
                words.append(str(item))
        tool = Path(words[0]).name

        name = f"py-doc-{uuid.uuid4().hex[:12]}"
        command = [*self.docker, "run", "--rm", "--pull", "never", "--name", name, "--user", self.user()]
        command += ["--cap-drop", "ALL", "--security-opt", "no-new-privileges"]
        if isinstance(network, str):
            command += ["--network", network]  # a user-defined network, such as the one the Structurizr stack runs in
        elif not network:
            command += ["--network", "none"]
        if shm_size:
            command += ["--shm-size", shm_size]
        for root, writable in mounted:
            command += [
                "--mount",
                "type=bind,"
                + _csv_field(f"source={root}")
                + ","
                + _csv_field(f"target={root}")
                + ("" if writable else ",readonly"),
            ]
        environment = {"HOME": f"{CACHE_DIR}/home"} if self.cache_volume else {}
        if self.cache_volume:
            command += ["--mount", f"type=volume,source={self.cache_volume},target={CACHE_DIR}"]
        environment.update(env or {})
        for key, value in environment.items():
            command += ["-e", f"{key}={value}"]
        if workdir is not None:
            cwd = self.container_path(workdir)
            if not covered(cwd):
                raise EnvironmentProblem(
                    f"The working folder '{os.fspath(workdir)}' is not under any folder given to the tool"
                )
            command += ["-w", cwd]
        command += [image or self.image, *words]

        logger.info("Running %s", tool)
        code, out, err = self._execute(command, timeout=timeout, stream=True)
        if code is None:
            self._kill(name)
            raise ToolTimeout(tool, timeout, _text(err) or _text(out))
        result = ToolResult(code, _text(out), _text(err))
        if code != 0:
            if code == 125 or any(
                marker in result.stderr.lower() for marker in (*_DAEMON_DOWN, *_IMAGE_MISSING, _MISSING_BIND)
            ):
                self._raise_environment(result)
                raise EnvironmentProblem(f"The container engine could not start {tool}: {result.stderr.strip()}")
            if check:
                raise ToolFailed(tool, code, "\n".join(part for part in (result.stderr, result.stdout) if part.strip()))
        return result

    def _kill(self, name: str) -> None:
        try:
            self._execute([*self.docker, "kill", name], timeout=30)
        except EnvironmentProblem:
            logger.debug("Could not stop container %s", name)

    def keep_alive(self, detached: bool = False) -> subprocess.Popen | None:
        """Keep the WSL distro running while a container must outlive this command (None on Linux).

        WSL stops a distro soon after its last ``wsl.exe`` exits, and Docker and every container with it. The
        process returned is a ``sleep`` inside the distro: end it with ``terminate()``. A ``detached`` one has
        no console and survives this program, for ``py-doc c4 up --detach``.
        """
        if not self.windows:
            return None
        flags = 0x00000008 | 0x00000200 if detached else 0x08000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP, else NO_WINDOW
        command = [*self._prefix(), "sleep", "infinity"]
        logger.debug("Keeping WSL running: %s", " ".join(command))
        try:
            return subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags
            )
        except FileNotFoundError as exc:
            raise EnvironmentProblem("wsl.exe was not found. Install WSL 2 (`wsl --install`)") from exc


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("Tool output is not valid UTF-8. Undecodable bytes are replaced")
        return data.decode("utf-8", errors="replace")
