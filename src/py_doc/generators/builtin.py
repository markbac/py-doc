"""The generators py-doc ships. Each returns Markdown; the registry writes it to the generator's ``output``.

Every one reads its options from ``spec.options`` (checked against ``OPTIONS`` when py-doc.yml loads) and
resolves paths against the project folder, so a generator never depends on the working folder.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from py_doc.markdown import nodes as n
from py_doc.markdown import parse, read_metadata

from .registry import GeneratorError

if TYPE_CHECKING:
    from py_doc.config import GeneratorSpec, ProjectConfig

# Options each type accepts besides type, name and output. A leading * marks a required one.
OPTIONS: dict[str, tuple[str, ...]] = {
    "glossary": ("source", "title"),
    "documents": ("documents", "title", "link"),
    "toc": ("*document", "title", "depth"),
    "adr-index": ("*source", "title"),
    "requirements": ("*sources", "pattern", "title"),
    "openapi": ("*source", "title", "engine", "html", "validate", "ruleset", "samples", "heading_offset"),
    "asyncapi": ("*source", "title", "engine", "html", "heading_offset"),  # the AsyncAPI parser always validates
    "python-api": ("*source", "title", "private"),
    "diagram": ("*source", "language", "caption", "title"),
    "command": ("*run", "timeout"),
    "python": ("*callable",),
}
DIAGRAM_LANGUAGES = {
    ".mmd": "mermaid",
    ".mermaid": "mermaid",
    ".puml": "plantuml",
    ".plantuml": "plantuml",
    ".dot": "dot",
    ".gv": "dot",
    ".d2": "d2",
}


# --- helpers -------------------------------------------------------------------------------------


def _path(spec: GeneratorSpec, project: ProjectConfig, key: str = "source") -> Path:
    value = spec.options[key]
    path = Path(value)
    return path if path.is_absolute() else (project.root / path).resolve()


def _files(spec: GeneratorSpec, project: ProjectConfig, key: str) -> list[Path]:
    """Files and patterns, relative to the project, each pattern's matches sorted."""
    raw = spec.options[key]
    entries = raw if isinstance(raw, list) else [raw]
    files: list[Path] = []
    for entry in entries:
        if set("*?[") & set(str(entry)):
            files += sorted(p.resolve() for p in project.root.glob(str(entry)) if p.is_file())
        else:
            files.append((project.root / str(entry)).resolve())
    return list(dict.fromkeys(files))


def _link(spec: GeneratorSpec, target: Path) -> str:
    """A link from the generated file to ``target``."""
    try:
        return Path(os.path.relpath(target, spec.output.parent)).as_posix()
    except ValueError:  # another drive on Windows
        return target.as_posix()


def _cell(text: Any) -> str:
    return " ".join(str(text or "").split()).replace("|", "\\|")


def _table(header: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(_cell(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _heading(spec: GeneratorSpec, default: str) -> str:
    return f"# {spec.options.get('title') or default}\n\n"


def _read_data(path: Path) -> Any:
    if not path.is_file():
        raise GeneratorError(f"{path} is not there")
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise GeneratorError(f"{path} cannot be read: {exc}") from exc


def _parsed(path: Path) -> n.Document:
    if not path.is_file():
        raise GeneratorError(f"{path} is not there")
    return parse(path.read_text(encoding="utf-8-sig"))


def _first_heading(document: n.Document) -> str | None:
    for node in n.walk(document):
        if isinstance(node, n.Heading):
            return " ".join(n.plain_text(node.children).split())
    return None


def _anchor(text: str) -> str:
    """The anchor pandoc and GitHub give a heading: lower case, punctuation dropped, spaces as hyphens."""
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"\s+", "-", text)


# --- generators ----------------------------------------------------------------------------------


def glossary(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """A glossary table from ``source`` (term: definition, in YAML or JSON), sorted by term. Without a source,
    the terms of ``lint.glossary`` and the spellings to avoid."""
    if "source" in spec.options:
        data = _read_data(_path(spec, project))
        if not isinstance(data, dict):
            raise GeneratorError(f"{spec.options['source']} must map each term to its definition")
        rows = [[term, definition] for term, definition in sorted(data.items(), key=lambda item: str(item[0]).lower())]
        return _heading(spec, "Glossary") + _table(["Term", "Definition"], rows)
    rows = [
        [term, ", ".join(variants)]
        for term, variants in sorted(project.lint.glossary.items(), key=lambda item: item[0].lower())
    ]
    return _heading(spec, "Glossary") + _table(["Term", "Not written as"], rows)


def documents(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """A table of the documents with their number, version and status, each linked to its first source
    (or with ``link: pdf`` and the like, to that built output)."""
    from py_doc.build import _combine_metadata
    from py_doc.markdown import Metadata

    names = spec.options.get("documents") or project.own_documents
    link = spec.options.get("link", "source")
    rows = []
    for name in names:
        if name not in project.documents:
            raise GeneratorError(f"documents names '{name}', which is not under documents")
        doc = project.documents[name]
        first = next((s.file for s in doc.sources if s.include and s.structurizr is None), None)
        tree = _parsed(first) if first is not None and first.is_file() else None
        meta = _combine_metadata(
            doc, read_metadata(tree) if tree else Metadata(), _first_heading(tree) if tree else None, project.root
        )
        target = first if link == "source" else project.output_path(doc, link, meta.version)
        title = f"[{_cell(meta.title)}]({_link(spec, target)})" if target is not None else _cell(meta.title)
        rows.append([title, meta.document_id or "", meta.version or "", meta.status or ""])
    return _heading(spec, "Documents") + _table(["Document", "Number", "Version", "Status"], rows)


def toc(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """The contents of a document: its headings down to ``depth`` (default 3), linked to their source files."""
    name = spec.options["document"]
    if name not in project.documents:
        raise GeneratorError(f"toc names '{name}', which is not under documents")
    depth = int(spec.options.get("depth", 3))
    lines = []
    for source in project.documents[name].sources:
        if not source.include or source.structurizr is not None or not source.file.is_file():
            continue
        for node in n.walk(_parsed(source.file)):
            if isinstance(node, n.Heading):
                level = min(max(node.level + source.heading_offset, 1), 6)
                if level <= depth:
                    text = " ".join(n.plain_text(node.children).split())
                    lines.append(f"{'  ' * (level - 1)}- [{text}]({_link(spec, source.file)}#{_anchor(text)})")
    return _heading(spec, "Contents") + "\n".join(lines)


_ADR_STATUS = re.compile(r"^\s*(?:\*\*)?status(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def adr_index(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """An index of the architecture decision records in a folder: number, title, status and date of each.

    The status comes from the front matter, a ``Status: ...`` line, or the first paragraph under a Status heading.
    """
    folder = _path(spec, project)
    if not folder.is_dir():
        raise GeneratorError(f"{folder} is not a folder")
    rows = []
    for file in sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in (".md", ".markdown") and p.stem.lower() not in ("readme", "index")
    ):
        text = file.read_text(encoding="utf-8-sig")
        tree = parse(text)
        meta = read_metadata(tree)
        status = meta.status
        if not status:
            found = _ADR_STATUS.search(text)
            status = found.group(1) if found else _under_heading(tree, "status")
        number = re.match(r"^(\d+)", file.stem)
        title = meta.title or _first_heading(tree) or file.stem
        rows.append(
            [number.group(1) if number else "", f"[{_cell(title)}]({_link(spec, file)})", status or "", meta.date or ""]
        )
    return _heading(spec, "Architecture decisions") + _table(["Number", "Decision", "Status", "Date"], rows)


def _under_heading(tree: n.Document, title: str) -> str | None:
    blocks = tree.children
    for index, block in enumerate(blocks):
        if isinstance(block, n.Heading) and n.plain_text(block.children).strip().lower() == title:
            following = blocks[index + 1] if index + 1 < len(blocks) else None
            if isinstance(following, n.Paragraph):
                return " ".join(n.plain_text(following.children).split())
    return None


def requirements(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """A traceability table: each requirement identifier (``pattern``, default letters, a hyphen and two or more digits, such as FR-001), where it is
    defined (the first cell of a table row or a heading) and every other file and line that refers to it."""
    pattern = re.compile(spec.options.get("pattern", r"\b[A-Z][A-Z0-9]*-\d{2,}\b"))
    defined: dict[str, tuple[Path, int]] = {}
    refs: dict[str, list[tuple[Path, int]]] = {}
    for file in _files(spec, project, "sources"):
        if not file.is_file():
            raise GeneratorError(f"{file} is not there")
        tree = _parsed(file)
        for node in n.walk(tree):
            if isinstance(node, n.TableRow) and not node.header and node.children:
                for match in pattern.finditer(n.plain_text(node.children[0].children)):
                    defined.setdefault(match.group(0), (file, node.line))
            elif isinstance(node, n.Heading):
                for match in pattern.finditer(n.plain_text(node.children)):
                    defined.setdefault(match.group(0), (file, node.line))
        for number, line in enumerate(file.read_text(encoding="utf-8-sig").splitlines(), start=1):
            for match in pattern.finditer(line):
                refs.setdefault(match.group(0), []).append((file, number))

    def place(file: Path, line: int) -> str:
        return f"[{file.name}:{line}]({_link(spec, file)})"

    rows = []
    for ident in sorted(set(defined) | set(refs), key=_natural):
        home = defined.get(ident)
        others = [place(f, line) for f, line in refs.get(ident, []) if (f, line) != home]
        rows.append([ident, place(*home) if home else "not defined", ", ".join(others) or "none"])
    return _heading(spec, "Traceability") + _table(["Requirement", "Defined", "Referred to"], rows)


def _natural(text: str) -> list:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def _engine(spec: GeneratorSpec) -> str:
    from .apidocs import ENGINES

    engine = spec.options.get("engine", "tool")
    if engine not in ENGINES:
        raise GeneratorError(f"The generator {spec.name}: engine must be one of {', '.join(ENGINES)}")
    if engine == "summary" and (spec.options.get("html") or spec.options.get("samples") or "ruleset" in spec.options):
        raise GeneratorError(f"The generator {spec.name}: html, samples and ruleset need engine: tool")
    return engine


def openapi(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """The reference documentation of an OpenAPI (or Swagger) description. With ``engine: tool`` (the default),
    Redocly checks and bundles it and Widdershins writes every operation, parameter, body, response and schema;
    with ``engine: summary``, py-doc writes an overview without the container."""
    source = _path(spec, project)
    if not source.is_file():
        raise GeneratorError(f"{source} is not there")
    if _engine(spec) == "tool":
        from .apidocs import openapi_tool

        return openapi_tool(spec, project, source)
    return openapi_summary(spec, project)


def asyncapi(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """The reference documentation of an AsyncAPI description. With ``engine: tool`` (the default), the AsyncAPI
    generator and its Markdown template write every server, channel, operation and message; with
    ``engine: summary``, py-doc writes an overview without the container."""
    source = _path(spec, project)
    if not source.is_file():
        raise GeneratorError(f"{source} is not there")
    if _engine(spec) == "tool":
        from .apidocs import asyncapi_tool

        return asyncapi_tool(spec, project, source)
    return asyncapi_summary(spec, project)


def openapi_summary(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """An OpenAPI (or Swagger) description as an overview: its title, version and description, a table of the
    operations and a list of the schemas."""
    api = _read_data(_path(spec, project))
    if not isinstance(api, dict) or not ("openapi" in api or "swagger" in api):
        raise GeneratorError(f"{spec.options['source']} is not an OpenAPI description (no openapi or swagger key)")
    info = api.get("info") or {}
    out = _heading(spec, f"{info.get('title', 'API')} {info.get('version', '')}".strip())
    if info.get("description"):
        out += str(info["description"]).strip() + "\n\n"
    rows = []
    for path, item in (api.get("paths") or {}).items():
        for method in _METHODS:
            operation = (item or {}).get(method)
            if isinstance(operation, dict):
                rows.append(
                    [f"`{method.upper()}`", f"`{path}`", operation.get("summary") or operation.get("operationId") or ""]
                )
    out += "## Operations\n\n" + (_table(["Method", "Path", "Summary"], rows) if rows else "None.")
    schemas = (api.get("components") or {}).get("schemas") or api.get("definitions") or {}
    if schemas:
        out += "\n\n## Schemas\n\n" + "\n".join(
            f"- `{name}`" + (f": {_cell((body or {}).get('description'))}" if (body or {}).get("description") else "")
            for name, body in schemas.items()
        )
    return out


def asyncapi_summary(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """An AsyncAPI description as an overview: its title, version, description and a table of the channels."""
    api = _read_data(_path(spec, project))
    if not isinstance(api, dict) or "asyncapi" not in api:
        raise GeneratorError(f"{spec.options['source']} is not an AsyncAPI description (no asyncapi key)")
    info = api.get("info") or {}
    out = _heading(spec, f"{info.get('title', 'API')} {info.get('version', '')}".strip())
    if info.get("description"):
        out += str(info["description"]).strip() + "\n\n"
    rows = []
    for name, channel in (api.get("channels") or {}).items():
        channel = channel or {}
        address = channel.get("address") or name
        operations = [
            (kind, channel[kind]) for kind in ("publish", "subscribe") if isinstance(channel.get(kind), dict)
        ]  # version 2
        for kind, operation in operations:
            message = operation.get("message") or {}
            rows.append(
                [
                    f"`{address}`",
                    kind,
                    message.get("name") or message.get("title") or _ref(message),
                    operation.get("summary") or channel.get("description") or "",
                ]
            )
        if not operations:
            messages = ", ".join(str(m) for m in (channel.get("messages") or {}))
            rows.append([f"`{address}`", "", messages, channel.get("description") or channel.get("summary") or ""])
    for name, operation in (api.get("operations") or {}).items():  # version 3
        operation = operation or {}
        channel = _ref(operation.get("channel") or {})
        rows.append([f"`{channel}`", operation.get("action", ""), name, operation.get("summary") or ""])
    return out + "## Channels\n\n" + (_table(["Channel", "Operation", "Message", "Summary"], rows) if rows else "None.")


def _ref(value: Any) -> str:
    return str(value.get("$ref", "")).rsplit("/", 1)[-1] if isinstance(value, dict) else str(value)


def python_api(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """Reference documentation of a Python package or module, read with ``ast`` (nothing is imported): each
    module, class, function and method with its signature and the first paragraph of its docstring."""
    source = _path(spec, project)
    private = bool(spec.options.get("private", False))
    files = sorted(source.rglob("*.py")) if source.is_dir() else [source]
    if not files or not all(f.is_file() for f in files):
        raise GeneratorError(f"{source} is not a Python file or a folder of them")
    base = source.parent
    out = _heading(spec, f"{source.stem} reference")
    for file in files:
        module = ".".join(file.relative_to(base).with_suffix("").parts).removesuffix(".__init__")
        if not private and any(
            part.startswith("_") and part != "__init__" for part in file.relative_to(base).with_suffix("").parts
        ):
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8-sig"), str(file))
        except SyntaxError as exc:
            raise GeneratorError(f"{file} is not valid Python: {exc}") from exc
        body = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (
                private or not node.name.startswith("_")
            ):
                body.append(_describe(node, 3, private))
        doc = _summary(ast.get_docstring(tree))
        if body or doc:
            out += f"## `{module}`\n\n" + (f"{doc}\n\n" if doc else "") + "\n\n".join(body) + "\n\n"
    return out


def _summary(doc: str | None) -> str:
    return doc.strip().split("\n\n", 1)[0].replace("\n", " ") if doc else ""


def _describe(node: ast.AST, level: int, private: bool) -> str:
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        text = f"{'#' * level} class `{node.name}{f'({bases})' if bases else ''}`\n\n{_summary(ast.get_docstring(node))}".rstrip()
        methods = [
            _describe(child, level + 1, private)
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and (private or not child.name.startswith("_") or child.name == "__init__")
        ]
        return "\n\n".join([text, *methods])
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    signature = f"{prefix}{node.name}({ast.unparse(node.args)}){returns}"
    return f"{'#' * min(level, 6)} `{signature}`\n\n{_summary(ast.get_docstring(node))}".rstrip()


def diagram(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """A diagram file (Mermaid, PlantUML, Graphviz, D2 or another language py-doc draws) as a fenced block, with
    a caption, so a diagram kept in its own file can be a page or a section that the build draws."""
    source = _path(spec, project)
    if not source.is_file():
        raise GeneratorError(f"{source} is not there")
    language = spec.options.get("language") or DIAGRAM_LANGUAGES.get(source.suffix.lower())
    if not language:
        raise GeneratorError(f"Say the language of {source.name} with language: (mermaid, plantuml, dot, ...)")
    text = source.read_text(encoding="utf-8-sig").rstrip("\n")
    fence = "`" * max(3, max((len(m) for m in re.findall(r"`+", text)), default=0) + 1)
    out = _heading(spec, spec.options["title"]) if spec.options.get("title") else ""
    caption = spec.options.get("caption")
    return out + f"{fence}{language}\n{text}\n{fence}" + (f"\n\n[[CAPTION:Figure]] {caption}" if caption else "")


def command(spec: GeneratorSpec, project: ProjectConfig) -> str:
    """Any program, run in the project folder: what it writes to standard output is the Markdown. ``run`` is
    the program and its arguments as a list (no shell), and ``timeout`` is in seconds (default 300)."""
    run = spec.options["run"]
    argv = [str(word) for word in run] if isinstance(run, list) else None
    if not argv:
        raise GeneratorError(f"The generator {spec.name}: run must be a list, such as [python, tools/make_table.py]")
    try:
        result = subprocess.run(
            argv,
            cwd=project.root,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(spec.options.get("timeout", 300)),
        )
    except FileNotFoundError as exc:
        raise GeneratorError(f"The generator {spec.name}: {argv[0]} is not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise GeneratorError(f"The generator {spec.name}: {argv[0]} took longer than {exc.timeout} s") from exc
    if result.returncode != 0:
        raise GeneratorError(
            f"The generator {spec.name}: {argv[0]} exited with status {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


GENERATORS = {
    "glossary": glossary,
    "documents": documents,
    "toc": toc,
    "adr-index": adr_index,
    "requirements": requirements,
    "openapi": openapi,
    "asyncapi": asyncapi,
    "python-api": python_api,
    "diagram": diagram,
    "command": command,
}
