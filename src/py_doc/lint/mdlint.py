"""markdownlint (markdownlint-cli2), run in the tool container. Its findings become lint issues with rule ``MD0xx``."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

import yaml

from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Mount, Runtime

from .config import MarkdownlintSettings
from .model import LintIssue

logger = logging.getLogger(__name__)

TIMEOUT = 600
# a.md:4:1 error MD004/ul-style Unordered list style [Expected: dash; Actual: asterisk]
_FINDING = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?\s+(?P<level>error|warning)\s+"
    r"(?P<rule>MD\d+)/(?P<name>[\w-]+)\s*(?P<message>.*)$"
)


def parse_findings(output: str, base: Path) -> list[tuple[Path, int, str, str]]:
    """``(file, line, rule, message)`` for each finding line of the tool's output."""
    found = []
    for line in output.splitlines():
        match = _FINDING.match(line.strip())
        if match:
            file = Path(match["file"])
            found.append(
                (file if file.is_absolute() else base / file, int(match["line"]), match["rule"],
                 f"{match['message'].strip()} ({match['name']})"),
            )  # fmt: skip
    return found


def run_markdownlint(
    files: list[Path], settings: MarkdownlintSettings, runtime: Callable[[], Runtime]
) -> list[LintIssue]:
    """Lint ``files`` with markdownlint in the container. Raises ConversionError when the tool itself fails."""
    files = [f.resolve() for f in files if f.is_file()]
    if not files:
        return []
    base = Path(os.path.commonpath([str(f.parent) for f in files]))
    box = runtime()
    with tempfile.TemporaryDirectory(prefix="py-doc-mdl-") as folder:
        work = Path(folder)
        if settings.inline is not None:
            config = work / "markdownlint.yaml"
            config.write_text(yaml.safe_dump(settings.inline, sort_keys=False), encoding="utf-8")
            mounts = [Mount(work)]
        else:
            config = settings.config
            mounts = [Mount(config.parent)] if config is not None else []
        argv: list = ["markdownlint-cli2", "--no-globs"]
        if config is not None:
            argv += ["--config", config]
        argv += [f.relative_to(base).as_posix() for f in files]
        result = box.run(argv, mounts=[Mount(base), *mounts], workdir=base, timeout=TIMEOUT, check=False)
    output = result.stdout + "\n" + result.stderr
    found = parse_findings(output, base)
    if result.returncode not in (0, 1) or (result.returncode == 1 and not found):
        raise ToolFailed("markdownlint-cli2", result.returncode, output.strip(), "it did not finish the check")
    if result.returncode == 0 and found:
        raise ConversionError("markdownlint-cli2 reported findings but exited 0")
    return [
        LintIssue(file, line, rule, "Markdown", message, settings.severity)
        for file, line, rule, message in found
    ]  # fmt: skip
