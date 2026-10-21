"""API reference documentation from OpenAPI and AsyncAPI descriptions, made by the standard tools in the tool
container.

OpenAPI
    ``redocly lint`` checks the description (``ruleset``, default ``minimal``), ``redocly bundle`` resolves its
    ``$ref`` files into one, ``widdershins`` writes the Markdown, and ``redocly build-docs`` writes a Redoc
    HTML page when ``html`` is set.
AsyncAPI
    The AsyncAPI generator with ``@asyncapi/markdown-template`` writes the Markdown, after the parser has
    checked the description, and ``@asyncapi/html-template`` writes an HTML page when ``html`` is set.

The tools write Markdown for web pages, with HTML headings and asides that a Word or PDF build would drop, so
``clean_markdown`` turns them into Markdown headings and py-doc callouts. Everything runs without a network.
"""

from __future__ import annotations

import html
import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from py_doc.errors import ConversionError
from py_doc.runtime import Mount

from .registry import GeneratorError, tool_runtime

if TYPE_CHECKING:
    from py_doc.config import GeneratorSpec, ProjectConfig

TIMEOUT = 600
RULESETS = ("minimal", "recommended", "recommended-strict", "spec")
ENGINES = ("tool", "summary")

_HTML_HEADING = re.compile(r"^<h([1-6])(?:\s[^>]*)?>(.*?)</h\1>\s*$", re.MULTILINE | re.IGNORECASE)
_ASIDE = re.compile(r'<aside class="(\w+)">(.*?)</aside>', re.DOTALL | re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_FENCE = re.compile(r"^(```|~~~)")
_ATX = re.compile(r"^(#{1,6})(\s+.*)$")
_ANCHOR = re.compile(r'<a (?:id|name)="([^"]+)"\s*>\s*</a>', re.IGNORECASE)
_LINK = re.compile(r'<a href="([^"]+)"\s*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_CALLOUT = {"success": "NOTE", "notice": "NOTE", "info": "NOTE", "warning": "WARNING", "danger": "CAUTION"}
# Lines meant for the three-pane web page of Slate, which make no sense in a document
_SLATE_ONLY = re.compile(r"^>\s*(Scroll down for|Code samples)\b.*$", re.MULTILINE)


def clean_markdown(text: str, heading_offset: int = 0, title: str | None = None, nest: bool = False) -> str:
    """Markdown for the HTML a web page needs and a Word or PDF build would drop, then the headings arranged.

    HTML headings become Markdown ones, asides callouts, ``<a id>`` anchors pandoc anchors (bookmarks in Word,
    so links to a schema still work) and ``<a href>`` links Markdown links; Slate-only lines are dropped. With
    ``nest``, every heading after the first top one moves down a level, so the sections sit under the API's
    title. Then the headings move by ``heading_offset``, and ``title`` replaces the first top heading. Code
    blocks are left as they are.
    """
    text = _HTML_HEADING.sub(
        lambda m: f"{'#' * int(m.group(1))} {html.unescape(_TAG.sub('', m.group(2))).strip()}", text
    )
    text = _ASIDE.sub(lambda m: _callout(m.group(1), m.group(2)), text)
    text = _ANCHOR.sub(lambda m: f"[]{{#{m.group(1)}}}", text)
    text = _LINK.sub(lambda m: f"[{html.unescape(_TAG.sub('', m.group(2))).strip()}]({m.group(1)})", text)
    text = _SLATE_ONLY.sub("", text)
    lines: list[str] = []
    fence: str | None = None
    titled = False
    for line in text.splitlines():
        marker = _FENCE.match(line)
        if marker:
            fence = None if fence == marker.group(1) else (fence or marker.group(1))
        elif fence is None:
            heading = _ATX.match(line)
            if heading:
                level = len(heading.group(1))
                first = not titled and level == 1
                if nest and titled:
                    level += 1
                level = min(max(level + heading_offset, 1), 6)
                body = heading.group(2)
                if first:
                    titled = True
                    body = f" {title}" if title else body
                line = "#" * level + body
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def _callout(kind: str, body: str) -> str:
    text = " ".join(html.unescape(_TAG.sub("", body)).split())
    return f"\n> [!{_CALLOUT.get(kind.lower(), 'NOTE')}]\n> {text}\n"


def _options(spec: GeneratorSpec) -> tuple[int, str | None]:
    offset = spec.options.get("heading_offset", 0)
    if not isinstance(offset, int) or isinstance(offset, bool):
        raise GeneratorError(f"The generator {spec.name}: heading_offset must be a whole number")
    return offset, spec.options.get("title")


def _html_target(spec: GeneratorSpec, project: ProjectConfig) -> Path | None:
    value = spec.options.get("html")
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (project.root / path).resolve()


def _run(project: ProjectConfig, spec: GeneratorSpec, source: Path, script: list[str], work: Path) -> None:
    """Run a shell script in the container, with the project read-only and the work folder writable."""
    runtime = tool_runtime(project)
    (work / "run.sh").write_text("set -e\n" + "\n".join(script) + "\n", encoding="utf-8", newline="\n")
    mounts = [Mount(project.root), Mount(work, writable=True)]
    if not source.resolve().is_relative_to(project.root.resolve()):
        mounts.append(Mount(source.parent))
    env = {"REDOCLY_TELEMETRY": "off", "REDOCLY_SUPPRESS_UPDATE_NOTICE": "true", "NO_COLOR": "1"}
    try:
        runtime.run(["sh", work / "run.sh"], mounts=mounts, workdir=work, env=env, timeout=TIMEOUT)
    except ConversionError as exc:
        raise GeneratorError(f"The generator {spec.name} ({spec.type}): {exc}") from exc


def _quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def openapi_tool(spec: GeneratorSpec, project: ProjectConfig, source: Path) -> str:
    offset, title = _options(spec)
    ruleset = spec.options.get("ruleset", "minimal")
    if ruleset not in RULESETS:
        raise GeneratorError(f"The generator {spec.name}: ruleset must be one of {', '.join(RULESETS)}")
    samples = spec.options.get("samples") or []
    if not isinstance(samples, list):
        raise GeneratorError(f"The generator {spec.name}: samples must be a list of languages, such as [shell, python]")
    runtime = tool_runtime(project)
    target = _html_target(spec, project)
    with tempfile.TemporaryDirectory(prefix="py-doc-openapi-") as folder:
        work = Path(folder)
        src, out = _quote(runtime.container_path(source)), runtime.container_path(work)
        script = []
        if spec.options.get("validate", True):
            script.append(f"redocly lint {src} --extends={ruleset} --format=stylish")
        script.append(f"redocly bundle {src} --output '{out}/bundled.yaml'")
        options = "--omitHeader --resolve --shallowSchemas false --expandBody"
        if samples:
            tabs = " ".join(_quote(f"{lang}:{lang}") for lang in samples)
            options += f" --language_tabs {tabs}"
        else:
            options += " --code false --language_tabs"  # no generated code samples in a document
        script.append(f"widdershins '{out}/bundled.yaml' -o '{out}/api.md' {options}")
        if target is not None:
            script.append(f"redocly build-docs '{out}/bundled.yaml' --output '{out}/api.html'")
        _run(project, spec, source, script, work)
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / "api.html", target)
        return clean_markdown((work / "api.md").read_text(encoding="utf-8"), offset, title, nest=True)


def asyncapi_tool(spec: GeneratorSpec, project: ProjectConfig, source: Path) -> str:
    offset, title = _options(spec)
    runtime = tool_runtime(project)
    target = _html_target(spec, project)
    with tempfile.TemporaryDirectory(prefix="py-doc-asyncapi-") as folder:
        work = Path(folder)
        src, out = _quote(runtime.container_path(source)), runtime.container_path(work)
        script = [f"node /opt/node/asyncapi-docs.js {src} '{out}/md' markdown toc=false"]
        if target is not None:
            script.append(f"node /opt/node/asyncapi-docs.js {src} '{out}/html' html")
        _run(project, spec, source, script, work)
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / "html" / "index.html", target)
        return clean_markdown((work / "md" / "asyncapi.md").read_text(encoding="utf-8"), offset, title)
