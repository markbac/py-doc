"""Fake ``docker`` and ``wsl.exe`` programs, so the tool runner is tested without a container engine.

Both are small Python scripts started as ``[sys.executable, script]``, which works on every platform.
Behaviour comes from a JSON file named by ``FAKE_DOCKER_STATE``. Every call is appended to the log
named by ``FAKE_DOCKER_LOG`` as one JSON line.

The docker fake can also run the tool for real on the host (``mode: host``): the part of the command
after the image is executed in the working folder that ``-w`` names. That lets tests drive pandoc,
dot and the rest through the whole runner when they are installed, without a daemon.
"""

from __future__ import annotations

import json
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

DOCKER = textwrap.dedent(
    """
    import json, os, subprocess, sys, time

    state = json.load(open(os.environ["FAKE_DOCKER_STATE"]))
    args = sys.argv[1:]
    with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps(args) + "\\n")

    def fail(message, code=1):
        sys.stderr.write(message + "\\n")
        sys.exit(code)

    if args and args[0] == "--version":
        print("Docker version 27.0.0, build fake")
        sys.exit(0)
    if not state.get("daemon", True):
        fail("Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?")

    cmd = args[0]
    images = state.get("images", [])
    if cmd == "info":
        print("27.0.0")
    elif cmd == "image" and args[1] == "inspect":
        if args[-1] not in images:
            fail("Error: No such image: " + args[-1])
        print(json.dumps([{"Id": "sha256:" + "ab" * 32, "Size": 123456789}]))
    elif cmd == "image" and args[1] == "ls":
        print("\\n".join(images))
    elif cmd == "image" and args[1] == "rm":
        pass
    elif cmd == "build":
        if state.get("build_exit", 0):
            fail("build failed: " + state.get("build_error", "boom"), state["build_exit"])
        context = args[-1]
        with open(os.environ["FAKE_DOCKER_LOG"] + ".builds", "a", encoding="utf-8") as builds:
            builds.write(json.dumps({"files": sorted(os.listdir(context)),
                                     "ca": os.path.exists(os.path.join(context, "extra-ca", "extra-ca.crt"))}) + "\\n")
        state.setdefault("images", []).append(args[args.index("--tag") + 1])
        json.dump(state, open(os.environ["FAKE_DOCKER_STATE"], "w"))
        print("Step 1/1 : FROM scratch")
    elif cmd in ("kill", "save", "load"):
        pass
    elif cmd == "run":
        flags_with_value = {"--name", "--user", "--cap-drop", "--security-opt", "--network", "--shm-size",
                            "--mount", "-e", "-w", "--pull"}
        i, env, workdir = 1, {}, None
        while args[i].startswith("-"):
            if args[i] in flags_with_value:
                if args[i] == "-e":
                    key, _, value = args[i + 1].partition("=")
                    env[key] = value
                if args[i] == "-w":
                    workdir = args[i + 1]
                i += 2
            else:
                i += 1
        image, command = args[i], args[i + 1:]
        if state.get("require_image", True) and image not in images:
            fail("Unable to find image '" + image + "' locally", 125)
        if state.get("sleep"):
            time.sleep(state["sleep"])
        if state.get("mode") == "host":
            env.pop("HOME", None)
            import shutil

            found = shutil.which(command[0])  # finds name.bat on Windows, where a script cannot start by its bare name
            done = subprocess.run([found or command[0], *command[1:]], cwd=workdir, env={**os.environ, **env})
            sys.exit(done.returncode)
        sys.stdout.buffer.write(bytes.fromhex(state["stdout_hex"]) if "stdout_hex" in state else state.get("stdout", "").encode("utf-8"))
        sys.stderr.buffer.write(state.get("stderr", "").encode("utf-8"))
        sys.stdout.flush()
        sys.exit(state.get("exit", 0))
    else:
        fail("unknown command " + cmd)
    """
)

WSL = textwrap.dedent(
    """
    import json, os, subprocess, sys

    args = sys.argv[1:]
    with open(os.environ["FAKE_WSL_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps(args) + "\\n")

    distros = os.environ.get("FAKE_WSL_DISTROS", "Ubuntu").split(",")
    if args[:1] == ["-l"]:
        if "-v" in args:
            text = "  NAME      STATE           VERSION\\r\\n" + "\\r\\n".join(
                ("* " if i == 0 else "  ") + d + "      Running         " + os.environ.get("FAKE_WSL_VERSION", "2")
                for i, d in enumerate(distros)) + "\\r\\n"
        else:
            text = "\\r\\n".join(distros) + "\\r\\n"
        sys.stdout.buffer.write(b"\\xff\\xfe" + text.encode("utf-16-le"))
        sys.exit(0)

    distro = None
    if args[:1] == ["-d"]:
        distro, args = args[1], args[2:]
    if distro is not None and distro not in distros:
        sys.stdout.buffer.write(("There is no distribution with the supplied name.\\r\\n").encode("utf-16-le"))
        sys.exit(1)
    def print(text=""):  # the real wsl.exe writes UTF-8 whatever the console code page is
        sys.stdout.buffer.write((str(text) + "\\n").encode("utf-8"))
        sys.stdout.flush()

    assert args[0] == "--exec", args
    rest = args[1:]
    if rest[0] == "wslpath":
        path = rest[-1]
        if path.startswith("\\\\\\\\wsl$\\\\") or path.startswith("\\\\\\\\wsl.localhost\\\\"):
            parts = path.split("\\\\")[4:]
            print("/" + "/".join(parts))
        elif path.startswith("\\\\\\\\"):
            sys.stderr.write("wslpath: cannot translate " + path + "\\n")
            sys.exit(1)
        elif len(path) > 1 and path[1] == ":":
            print("/mnt/" + path[0].lower() + path[2:].replace("\\\\", "/"))
        else:
            print(path)
    elif rest[0] == "id":
        print(1000)
    elif rest[0] == "docker":
        done = subprocess.run([sys.executable, os.environ["FAKE_DOCKER_SCRIPT"], *rest[1:]])
        sys.exit(done.returncode)
    else:
        sys.stderr.write("unexpected " + repr(rest) + "\\n")
        sys.exit(127)
    """
)


@dataclass
class FakeEngine:
    docker: list[str]
    wsl: list[str]
    state_path: Path
    docker_log: Path
    wsl_log: Path

    def configure(self, **state) -> None:
        current = json.loads(self.state_path.read_text(encoding="utf-8"))
        current.update(state)
        self.state_path.write_text(json.dumps(current), encoding="utf-8")

    def docker_calls(self) -> list[list[str]]:
        if not self.docker_log.exists():
            return []
        return [json.loads(line) for line in self.docker_log.read_text(encoding="utf-8").splitlines()]

    def wsl_calls(self) -> list[list[str]]:
        if not self.wsl_log.exists():
            return []
        return [json.loads(line) for line in self.wsl_log.read_text(encoding="utf-8").splitlines()]

    def builds(self) -> list[dict]:
        path = Path(str(self.docker_log) + ".builds")
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def runs(self) -> list[list[str]]:
        return [call for call in self.docker_calls() if call[:1] == ["run"]]


def install(tmp_path: Path, monkeypatch, **state) -> FakeEngine:
    folder = tmp_path / "fake-engine"
    folder.mkdir()
    docker_script, wsl_script = folder / "docker.py", folder / "wsl.py"
    docker_script.write_text(DOCKER, encoding="utf-8")
    wsl_script.write_text(WSL, encoding="utf-8")
    engine = FakeEngine(
        docker=[sys.executable, str(docker_script)],
        wsl=[sys.executable, str(wsl_script)],
        state_path=folder / "state.json",
        docker_log=folder / "docker.log",
        wsl_log=folder / "wsl.log",
    )
    engine.state_path.write_text(json.dumps({"images": ["tools:test"], **state}), encoding="utf-8")
    monkeypatch.setenv("FAKE_DOCKER_STATE", str(engine.state_path))
    monkeypatch.setenv("FAKE_DOCKER_LOG", str(engine.docker_log))
    monkeypatch.setenv("FAKE_DOCKER_SCRIPT", str(docker_script))
    monkeypatch.setenv("FAKE_WSL_LOG", str(engine.wsl_log))
    return engine
