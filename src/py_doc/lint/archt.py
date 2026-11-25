"""arch-text's own check of the ```archt fences of Markdown files, run in the tool container.

arch-text has no check command, so ``arch-text build`` compiles each fence and its diagnostics are read from what it
prints: ``0.archt:3:5: error AT008: message``, the source line with a caret, and ``= hint`` when there is one. Each
finding keeps arch-text's code (``AT008`` ...) as its rule, at the line of the Markdown file it is on.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from py_doc.errors import ToolFailed
from py_doc.runtime import Mount, Runtime

from . import bpmn
from .model import LintIssue

TIMEOUT = 300
_FINDING = re.compile(r"^(\d+)\.archt:(\d+):(\d+): (error|warning) (AT\d{3}): (.*)$")
_HINT = re.compile(r"^\s+= (.*)$")


def fences(files: list[Path]) -> list[tuple[Path, int, str]]:
    """``(file, line of the opening fence, body)`` of every ```archt fence of ``files``."""
    return bpmn.fences(files, "archt")


def parse(output: str) -> list[tuple[int, int, int, str, str, str]]:
    """``(fence number, line, column, code, severity, message)`` of each diagnostic ``arch-text build`` printed."""
    found: list[tuple[int, int, int, str, str, str]] = []
    for line in output.splitlines():
        match = _FINDING.match(line)
        if match:
            number, row, col, severity, code, message = match.groups()
            found.append((int(number), int(row), int(col), code, severity, message))
        elif found and (hint := _HINT.match(line)):
            *head, message = found[-1]
            found[-1] = (*head, f"{message} {hint.group(1)}")  # type: ignore[assignment]
    return found


def check(found: list[tuple[Path, int, str]], runtime: Runtime) -> list[LintIssue]:
    """Compile the fences with ``arch-text build``, in one container run. Raises ToolFailed when it does not finish."""
    with tempfile.TemporaryDirectory(prefix="py-doc-archt-") as folder:
        work = Path(folder)
        names = []
        for number, (_, _, body) in enumerate(found):
            names.append(f"{number}.archt")
            (work / names[-1]).write_text(body + "\n", encoding="utf-8", newline="\n")
        # writable: arch-text build writes each scene beside its fence, here in a folder of py-doc's own
        result = runtime.run(
            ["arch-text", "build", *names],
            mounts=[Mount(work, writable=True)], workdir=work, env={"NO_COLOR": "1"}, timeout=TIMEOUT, check=False,
        )  # fmt: skip
    diagnostics = parse(result.stderr)
    # 1 is an error in an input; a 1 with no error printed is arch-text itself failing
    finished = result.returncode == 0 or (result.returncode == 1 and any(d[4] == "error" for d in diagnostics))
    if not finished:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise ToolFailed("arch-text", result.returncode, output, "it did not finish the check")
    issues = []
    for number, row, col, code, severity, message in diagnostics:
        if number >= len(found):
            continue
        file, fence_line, _ = found[number]
        issues.append(LintIssue(file, fence_line + row, code, "Architecture", message, severity, column=col))
    return issues
