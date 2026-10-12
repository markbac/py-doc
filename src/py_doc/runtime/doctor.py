"""``py-doc doctor``: say what works, what does not, and what to do about it."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass

from ..errors import EnvironmentProblem, ToolFailed
from ..platform import current
from .engine import Runtime, decode_wsl


@dataclass
class Check:
    name: str
    status: str  # "ok", "info" or "FAIL"
    detail: str
    hint: str = ""


def _wsl_listing(runtime: Runtime, *flags: str) -> str:
    code, out, _ = runtime._execute_host([*runtime.wsl_exe, "-l", *flags])  # noqa: SLF001
    return decode_wsl(out) if code == 0 else ""


def diagnose(runtime: Runtime) -> list[Check]:
    """Run the checks in order. Later ones are skipped when an earlier one makes them meaningless."""
    checks = [Check("platform", "ok", current())]

    if runtime.windows:
        distros = [line.strip() for line in _wsl_listing(runtime, "-q").splitlines() if line.strip()]
        if not distros:
            checks.append(Check("wsl", "FAIL", "no WSL distribution found", "Install one: `wsl --install -d Ubuntu`"))
            return checks
        wanted = runtime.wsl_distro or distros[0]
        if wanted not in distros:
            checks.append(Check("wsl", "FAIL", f"distribution '{wanted}' not found. Installed: {', '.join(distros)}",
                                "Set runtime.wsl_distro in py-doc.yml"))  # fmt: skip
            return checks
        version = _wsl_version(_wsl_listing(runtime, "-v"), wanted)
        if version == 1:
            checks.append(Check("wsl", "FAIL", f"'{wanted}' is WSL 1, which cannot run Docker",
                                f"Convert it: `wsl --set-version {wanted} 2`"))  # fmt: skip
            return checks
        checks.append(Check("wsl", "ok", f"{wanted} (WSL {version or '2'})"))

    try:
        result = runtime.engine(["--version"], check=False)
        checks.append(Check("docker", "ok", result.stdout.strip() or "found"))
    except EnvironmentProblem as exc:
        hint = ""
        if runtime.windows and shutil.which("docker"):
            hint = "Docker Desktop is not a supported route. Install Docker Engine inside the WSL distro"
        checks.append(Check("docker", "FAIL", str(exc), hint))
        return checks

    try:
        info = runtime.engine(["info", "--format", "{{.ServerVersion}}"])
        checks.append(Check("engine", "ok", f"running, version {info.stdout.strip()}"))
    except (EnvironmentProblem, ToolFailed) as exc:
        checks.append(Check("engine", "FAIL", str(exc)))
        return checks

    try:
        found = runtime.engine(["image", "inspect", runtime.image], check=False)
    except EnvironmentProblem as exc:
        checks.append(Check("image", "FAIL", str(exc)))
        return checks
    if found.returncode != 0:
        checks.append(
            Check(
                "image",
                "info",
                f"{runtime.image} is not built yet",
                "It is built on first use, or run `py-doc tools build`",
            )
        )
        return checks
    size = _size(found.stdout)
    checks.append(Check("image", "ok", f"{runtime.image}" + (f" ({size})" if size else "")))

    try:
        first = runtime.run(["pandoc", "--version"]).stdout.splitlines()[0]
        checks.append(Check("container", "ok", f"a trivial run works: {first}"))
    except (EnvironmentProblem, ToolFailed) as exc:
        checks.append(Check("container", "FAIL", str(exc)))
    return checks


def _wsl_version(listing: str, distro: str) -> int | None:
    for line in listing.splitlines():
        match = re.match(rf"^\s*\*?\s*{re.escape(distro)}\s+\S+\s+(\d)\s*$", line)
        if match:
            return int(match.group(1))
    return None


def _size(inspect_json: str) -> str:
    try:
        size = json.loads(inspect_json)[0]["Size"]
    except (ValueError, KeyError, IndexError, TypeError):
        return ""
    return f"{size / 1e9:.1f} GB" if size >= 1e9 else f"{size / 1e6:.0f} MB"


def render(checks: list[Check]) -> str:
    lines = []
    for check in checks:
        lines.append(f"{check.status:<5} {check.name:<10} {check.detail}")
        if check.hint:
            lines.append(f"      {'':<10} {check.hint}")
    return "\n".join(lines)


def failed(checks: list[Check]) -> bool:
    return any(check.status == "FAIL" for check in checks)
