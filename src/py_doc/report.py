"""The JSON build report: what was built, with what, and everything that went wrong on the way.

Keys are in a fixed order and nothing depends on the clock unless ``timestamps`` is asked for, so two
builds of the same input give the same report and it diffs cleanly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .directives import Fence
from .runtime import Runtime

SCHEMA = Path(__file__).with_name("report.schema.json")
_LOCATION = re.compile(r"^(?P<file>(?:[A-Za-z]:)?[^:\n]+?):(?P<line>\d+):\s*(?P<message>.*)$", re.S)
_VERSION_FLAGS = {"dot": ["-V"], "java": ["-version"], "plantuml": ["-version"]}
_WORDS = re.compile(r"\w+(?:['’-]\w+)*")
_SENTENCE_END = re.compile(r"[.!?]+(?:\s|$)")


def counts(text: str) -> dict[str, int]:
    """Words, sentences and paragraphs of the prose in ``text``: code blocks and headings do not count."""
    prose: list[str] = []
    fence = Fence()
    for line in text.splitlines():
        if fence.inside(line) or line.lstrip().startswith("#"):
            prose.append("")
        else:
            prose.append(line)
    body = "\n".join(prose)
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    return {
        "words": len(_WORDS.findall(body)),
        "sentences": len(_SENTENCE_END.findall(body)),
        "paragraphs": len(paragraphs),
    }


class _Collector(logging.Handler):
    def __init__(self, sink: list[dict]) -> None:
        super().__init__(logging.WARNING)
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage()
        found = _LOCATION.match(text)
        entry: dict[str, Any] = {"level": record.levelname.lower(), "message": found["message"] if found else text}
        if found:
            entry["file"] = found["file"]
            entry["line"] = int(found["line"])
        self.sink.append(entry)


class BuildReport:
    """Collects the facts of one ``py-doc build``. Use :meth:`recording` around the build."""

    def __init__(self, root: Path, timestamps: bool = False) -> None:
        self.root = root
        self.timestamps = timestamps
        self.error: str | None = None
        self.image: dict[str, Any] = {}
        self.tools: dict[str, str | None] = {}
        self.documents: list[dict[str, Any]] = []
        self.steps: list[dict[str, str]] = []
        self.diagrams: list[dict[str, Any]] = []
        self.templates: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self._handler = _Collector(self.warnings)
        self._tools_wanted: set[str] = set()

    # --- collecting -------------------------------------------------------------------------------

    def recording(self):
        """A context manager that collects the warnings and errors logged while it is open."""
        logger = logging.getLogger("py_doc")
        report = self

        class _Scope:
            def __enter__(self_inner):
                logger.addHandler(report._handler)
                return report

            def __exit__(self_inner, *exc):
                logger.removeHandler(report._handler)

        return _Scope()

    def shown(self, path: Path) -> str:
        try:
            return Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return Path(path).as_posix()

    def document(self, doc_id: str) -> dict[str, Any]:
        for entry in self.documents:
            if entry["id"] == doc_id:
                return entry
        entry = {"id": doc_id, "status": "ok", "sources": [], "outputs": []}
        self.documents.append(entry)
        return entry

    def sources(self, doc_id: str, parts: list[tuple[Path, str]]) -> None:
        self.document(doc_id)["sources"] = [{"file": self.shown(file), **counts(text)} for file, text in parts]

    def output(self, doc_id: str, fmt: str, path: Path) -> None:
        data = Path(path).read_bytes()
        self.document(doc_id)["outputs"].append(
            {"format": fmt, "path": self.shown(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )

    def icons(self, doc_id: str, manifest: list[dict[str, str]]) -> None:
        """The icons a poster uses, each with its source and licence, such as the MDI icons Apache 2.0 covers."""
        if manifest:
            self.document(doc_id)["icons"] = manifest

    def diagram(self, doc_id: str, fmt: str, event: dict[str, Any]) -> None:
        entry = {"document": doc_id, "format": fmt, **event}
        if "file" in entry:
            entry["file"] = self.shown(Path(entry["file"]))
        self.diagrams.append(entry)

    def template(self, doc_id: str, template_report) -> None:
        self.templates.append(
            {
                "document": doc_id,
                "path": self.shown(template_report.path),
                "failures": [f"{f.check}: {f.message}" for f in template_report.failures],
                "warnings": [f"{f.check}: {f.message}" for f in template_report.warnings],
            }
        )

    def step(self, name: str, status: str, detail: str = "") -> None:
        """A stage of the build pipeline: generate, lint, documents, posters, site or verify."""
        self.steps.append({"step": name, "status": status, **({"detail": detail} if detail else {})})

    def failed(self, doc_id: str, error: BaseException) -> None:
        self.document(doc_id)["status"] = "failed"
        self.document(doc_id)["error"] = str(error)
        self.error = self.error or f"{doc_id}: {error}"

    def want_tool(self, name: str) -> None:
        self._tools_wanted.add(name)

    def describe_runtime(self, runtime: Runtime | None) -> None:
        """Record the image and the version of each tool that was used. Never raises: a report is best effort."""
        if runtime is None:
            return
        self.image = {"tag": runtime.image, "id": None}
        try:
            found = runtime.engine(["image", "inspect", "--format", "{{.Id}}", runtime.image], check=False)
            if found.returncode == 0 and found.stdout.strip():
                self.image["id"] = found.stdout.strip()
        except Exception:  # noqa: BLE001
            pass
        for tool in sorted(self._tools_wanted):
            self.tools[tool] = self._version(runtime, tool)

    @staticmethod
    def _version(runtime: Runtime, tool: str) -> str | None:
        try:
            result = runtime.run([tool, *_VERSION_FLAGS.get(tool, ["--version"])], check=False)
        except Exception:  # noqa: BLE001
            return None
        for line in (result.stdout + "\n" + result.stderr).splitlines():
            if line.strip():
                return line.strip()
        return None

    # --- output -----------------------------------------------------------------------------------

    def data(self) -> dict[str, Any]:
        failed = (
            bool(self.error)
            or any(d["status"] == "failed" for d in self.documents)
            or any(s["status"] == "failed" for s in self.steps)
        )
        data: dict[str, Any] = {
            "schema": 1,
            "py_doc": __version__,
            "status": "failed" if failed else "ok",
            "error": self.error,
            "image": self.image,
            "tools": dict(sorted(self.tools.items())),
            "documents": self.documents,
            "diagrams": self.diagrams,
            "templates": self.templates,
            "warnings": self.warnings,
        }
        if self.steps:
            data["steps"] = self.steps
        if self.timestamps:
            data["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        else:
            for entry in self.diagrams:
                entry.pop("seconds", None)
        return data

    def write(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        return path
