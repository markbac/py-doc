"""``py-doc setup``: install Docker Engine for the tool runner, in the WSL distro on Windows or on Linux itself.

Only Ubuntu and Debian are handled, with Docker's own apt repository. The steps are one shell script run as
root, so a person can read exactly what will happen first (``py-doc setup --dry-run``). Nothing here runs
unless the command line asks for it, and a build never calls it.
"""

from __future__ import annotations

import getpass
import logging
import os
import shlex
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..errors import EnvironmentProblem
from .engine import _DAEMON_DOWN, _NO_DOCKER, Runtime, decode_wsl

logger = logging.getLogger(__name__)

UNSUPPORTED = 3  # the exit status the script uses for a distribution it does not know

STEPS = (
    "Add Docker's apt repository and its signing key",
    "Install docker-ce, docker-ce-cli, containerd.io and docker-buildx-plugin",
    "Add the user to the docker group",
    "Turn on systemd in /etc/wsl.conf, so Docker starts with the distro",  # Windows only, see script()
    "Start the Docker service",
)

_SCRIPT = r"""set -eu
. /etc/os-release
case "$ID" in
  ubuntu|debian) ;;
  *) echo "py-doc setup supports Ubuntu and Debian, not '$ID'" >&2; exit 3 ;;
esac
CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $CODENAME stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
usermod -aG docker __USER__
"""

_WSL_BOOT = r"""if [ ! -d /run/systemd/system ] && ! grep -qs '^systemd' /etc/wsl.conf; then
  printf '\n[boot]\nsystemd=true\n' >> /etc/wsl.conf
fi
"""

_START = r"""(systemctl start docker 2>/dev/null || service docker start) || true
"""

Run = Callable[..., "subprocess.CompletedProcess"]


@dataclass
class State:
    name: str  # ready, stopped, no-permission, missing
    detail: str = ""


def script(user: str, windows: bool) -> str:
    """The commands run as root. ``user`` is added to the docker group."""
    return _SCRIPT.replace("__USER__", shlex.quote(user)) + (_WSL_BOOT if windows else "") + _START


def probe(runtime: Runtime) -> State:
    """Can Docker be used the way the tool runner uses it?"""
    try:
        code, out, err = runtime._execute([*runtime.docker, "info"], timeout=60)  # noqa: SLF001
    except EnvironmentProblem as exc:  # the program itself is not there
        return State("missing", str(exc))
    text = (err or out).decode("utf-8", errors="replace")
    if code == 0:
        return State("ready")
    low = text.lower()
    if any(marker in low for marker in _NO_DOCKER):
        return State("missing", text.strip())
    if "permission denied" in low:
        return State("no-permission", text.strip())
    if any(marker in low for marker in _DAEMON_DOWN):
        return State("stopped", text.strip())
    return State("missing", text.strip())


def target_user(runtime: Runtime, run: Run = subprocess.run) -> str:
    """The person who will use Docker: the distro's default user on Windows, the calling user on Linux."""
    if not runtime.windows:
        return os.environ.get("SUDO_USER") or getpass.getuser()
    done = run([*runtime._prefix(), "id", "-un"], capture_output=True, timeout=60)  # noqa: SLF001
    name = done.stdout.decode("utf-8", errors="replace").strip()
    if done.returncode != 0 or not name or name == "root":
        raise EnvironmentProblem(
            "Cannot tell which WSL user should run Docker (the default user is root or unknown). "
            "Create a normal user in the distro, make it the default, then run `py-doc setup` again"
        )
    return name


def command(runtime: Runtime) -> list[str]:
    """The program and arguments that run a script, read from standard input, as root."""
    if runtime.windows:
        prefix = runtime._prefix()  # noqa: SLF001  [wsl.exe, -d, NAME, --exec]
        return [*prefix[:-1], "--user", "root", "--exec", "bash", "-s"]
    return [*([] if os.geteuid() == 0 else ["sudo"]), "bash", "-s"]


def install(runtime: Runtime, user: str, run: Run = subprocess.run) -> None:
    """Run the script. Output goes to the terminal, and sudo asks for its password on the terminal."""
    argv = command(runtime)
    logger.debug("Running the setup script: %s", " ".join(argv))
    body = "export DEBIAN_FRONTEND=noninteractive\n" + script(user, runtime.windows)
    try:
        done = run(argv, input=body.encode("utf-8"))
    except FileNotFoundError as exc:
        raise EnvironmentProblem(f"'{argv[0]}' was not found") from exc
    if done.returncode == UNSUPPORTED:
        raise EnvironmentProblem("py-doc setup supports Ubuntu and Debian. Install Docker Engine yourself: https://docs.docker.com/engine/install/")
    if done.returncode != 0:
        raise EnvironmentProblem(f"The setup script stopped with exit status {done.returncode}. Its output is above")


def restart(runtime: Runtime, run: Run = subprocess.run) -> None:
    """Windows: stop the distro, so the new group and systemd apply the next time it starts."""
    if not runtime.windows:
        return
    argv = [*runtime.wsl_exe, "--terminate", runtime.wsl_distro or default_distro(runtime)]
    run(argv, capture_output=True, timeout=120)


def default_distro(runtime: Runtime) -> str:
    code, out, _ = runtime._execute_host([*runtime.wsl_exe, "-l", "-q"])  # noqa: SLF001
    names = [line.strip() for line in decode_wsl(out).splitlines() if line.strip()] if code == 0 else []
    if not names:
        raise EnvironmentProblem("No WSL distribution found. Install one with `wsl --install -d Ubuntu`")
    return names[0]


def start_service(runtime: Runtime, run: Run = subprocess.run) -> None:
    """Start Docker in a distro that does not run systemd (yet)."""
    if not runtime.windows:
        return
    prefix = runtime._prefix()  # noqa: SLF001
    run([*prefix[:-1], "--user", "root", "--exec", "service", "docker", "start"], capture_output=True, timeout=120)


def describe(runtime: Runtime) -> Sequence[str]:
    """The steps, for the person to read before they agree."""
    return [s for s in STEPS if runtime.windows or "wsl.conf" not in s]
