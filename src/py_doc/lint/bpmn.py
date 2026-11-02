"""bpmn-text's own check of the ```bpmnt fences of Markdown files, run in the tool container.

Each finding keeps bpmn-text's code (``BT202`` ...) as its rule, at the line of the Markdown file it is on.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from py_doc.diagrams.scan import find_blocks
from py_doc.errors import ToolFailed
from py_doc.runtime import Mount, Runtime

from .model import LintIssue

TIMEOUT = 300


def fences(files: list[Path]) -> list[tuple[Path, int, str]]:
    """``(file, line of the opening fence, body)`` of every ```bpmnt fence of ``files``."""
    found = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue  # reported by the file's own result
        found += [(file, block.line, block.body) for block in find_blocks(text) if block.fence == "bpmnt"]
    return found


def check(found: list[tuple[Path, int, str]], runtime: Runtime) -> list[LintIssue]:
    """Run ``bpmn-text check`` over the fences, in one container run. Raises ToolFailed when it does not finish."""
    with tempfile.TemporaryDirectory(prefix="py-doc-bpmnt-") as folder:
        work = Path(folder)
        names = []
        for number, (_, _, body) in enumerate(found):
            names.append(f"{number}.bpmnt")
            (work / names[-1]).write_text(body + "\n", encoding="utf-8", newline="\n")
        result = runtime.run(
            ["bpmn-text", "check", "--format", "json", *names],
            mounts=[Mount(work)], workdir=work, timeout=TIMEOUT, check=False,
        )  # fmt: skip
    try:
        report = json.loads(result.stdout) if result.returncode in (0, 1) else None
    except json.JSONDecodeError:
        report = None
    if report is None:
        output = (result.stdout + "\n" + result.stderr).strip()
        raise ToolFailed("bpmn-text", result.returncode, output, "it did not finish the check")
    issues = []
    for entry in report:
        file, fence_line, _ = found[names.index(entry["file"])]
        for d in entry["diagnostics"]:
            start = d["range"]["start"]
            issues.append(
                LintIssue(file, fence_line + start["line"], d["code"], "BPMN", d["message"], d["severity"],
                          column=start["col"]),
            )  # fmt: skip
    return issues
