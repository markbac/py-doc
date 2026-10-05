"""Turn legacy ``createdocs`` YAML build files into one ``py-doc.yml``.

Every legacy file becomes one document, so the relations between files, folders, sources and
templates stay as they were. Only what is shared is lifted into the defaults (a template that every
Word document uses). Anything py-doc cannot do yet is listed in the report, never dropped quietly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import CONFIG_NAMES, parse_config
from .files import DEFAULT_EXCLUDE_DIRS

LEGACY_FORMATS = ("createdocs",)

_META_KEYS = {
    "title", "subtitle", "author", "date", "version", "status", "document_number", "description",
    "classification", "subject", "keywords", "category", "company", "toc_depth",
}  # fmt: skip
_ENTRY_KEYS = {"file", "heading_offset", "title", "page_break", "include"}
# What createdocs can build that py-doc cannot (yet), and the cli keys that only matter to those.
_UNSUPPORTED_EMIT = {"emit-pdf": "PDF", "emit-html": "HTML", "emit-md": "processed Markdown"}
_UNUSED_CLI = {
    "plantuml-jar-path": "PlantUML diagrams are not rendered",
    "ditaa-jar-path": "ditaa diagrams are not rendered",
    "css": "there is no HTML output",
    "keep-tmp": "there is no temporary build folder",
    "no-svg-to-png": "SVG pictures are not converted",
    "pdf-from-docx": "there is no PDF output",
    "verbose": "use -v on the command line",
}


@dataclass
class Finding:
    level: str  # "info" or "warning"
    file: Path
    message: str


@dataclass
class Migration:
    config: dict[str, Any] = field(default_factory=dict)
    migrated: list[tuple[Path, str]] = field(default_factory=list)  # legacy file, document id
    skipped: list[Path] = field(default_factory=list)  # YAML files that are not build files
    findings: list[Finding] = field(default_factory=list)

    def note(self, level: str, file: Path, message: str) -> None:
        self.findings.append(Finding(level, file, message))


def discover(paths: list[Path]) -> list[Path]:
    """YAML files named by ``paths``, or found below the directories among them."""
    found: list[Path] = []
    for path in paths:
        if path.is_file():
            found.append(path)
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in DEFAULT_EXCLUDE_DIRS)
            found += [
                Path(root) / name
                for name in sorted(files)
                if name.lower().endswith((".yml", ".yaml")) and name not in CONFIG_NAMES
            ]
    return sorted(dict.fromkeys(p.resolve() for p in found), key=lambda p: p.as_posix())


def read_createdocs(path: Path) -> dict | None:
    """The data of a createdocs build file, or None if the file is something else."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return None
    if not all(isinstance(e, dict) and "file" in e for e in data["entries"]):
        return None
    return data


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "document"


def _unique_id(path: Path, taken: set[str]) -> str:
    for candidate in (_slug(path.stem), _slug(f"{path.parent.name}-{path.stem}")):
        if candidate not in taken:
            return candidate
    number = 2
    while f"{_slug(path.stem)}-{number}" in taken:
        number += 1
    return f"{_slug(path.stem)}-{number}"


def _emit_formats(cli: dict, output: str | None) -> dict[str, bool]:
    """Which outputs createdocs would build: its emit flags, else what the output file name implies."""
    flags = {key: bool(cli.get(key)) for key in ("emit-docx", "emit-pdf", "emit-html", "emit-md")}
    if any(flags.values()):
        return flags
    suffix = Path(output).suffix.lower() if output else None
    guess = {".docx": "emit-docx", ".pdf": "emit-pdf", ".html": "emit-html", ".htm": "emit-html"}
    flags[guess.get(suffix, "emit-md")] = True
    return flags


def migrate(paths: list[Path], config_dir: Path, source_format: str = "createdocs") -> Migration:
    """Read the build files found at ``paths``. Paths in the result are relative to ``config_dir``."""
    if source_format not in LEGACY_FORMATS:
        raise ValueError(f"Unknown legacy format '{source_format}'. Supported: {', '.join(LEGACY_FORMATS)}")
    result = Migration()
    documents: dict[str, dict] = {}
    templates: dict[str, Path | None] = {}  # document id -> absolute docx template
    sources: dict[Path, list[str]] = {}
    taken: set[str] = set()

    def rel(path: Path) -> str:
        return Path(os.path.relpath(path, config_dir)).as_posix()

    for yaml_path in discover(paths):
        data = read_createdocs(yaml_path)
        if data is None:
            result.skipped.append(yaml_path)
            continue
        base = yaml_path.parent
        doc_id = _unique_id(yaml_path, taken)
        taken.add(doc_id)
        doc: dict[str, Any] = {}
        meta = dict(data.get("meta") or {})
        cli = data.get("cli") or {}

        # properties
        if "doc_number" in meta:
            meta.setdefault("document_number", meta.pop("doc_number"))
        for key, value in meta.items():
            if key in _META_KEYS:
                doc[key] = value
            else:
                result.note("warning", yaml_path, f"meta.{key} has no equivalent and was left out")
        if "toc-depth" in cli and "toc_depth" not in doc:
            doc["toc_depth"] = cli["toc-depth"]
        if doc.get("version"):
            result.note(
                "info", yaml_path, "createdocs added the version to the output file name. py-doc writes the exact path"
            )
        if doc.get("status"):
            result.note(
                "warning", yaml_path, "createdocs chose the template from the status. py-doc uses one template per output"
            )

        # sources
        doc_sources = []
        for index, entry in enumerate(data["entries"]):
            for key in entry:
                if key not in _ENTRY_KEYS:
                    result.note("warning", yaml_path, f"entries[{index}].{key} has no equivalent and was left out")
            source_file = (base / str(entry["file"])).resolve()
            if not source_file.is_file():
                result.note("warning", yaml_path, f"entries[{index}]: '{entry['file']}' does not exist")
            item: dict[str, Any] = {"file": rel(source_file)}
            if entry.get("heading_offset"):
                item["heading_offset"] = entry["heading_offset"]
            if entry.get("title"):
                item["title"] = entry["title"]
            if entry.get("page_break"):
                item["page_break"] = True
            if entry.get("include") is False:
                item["include"] = False
            doc_sources.append(item)
            sources.setdefault(source_file, []).append(doc_id)
        doc["sources"] = doc_sources

        # outputs
        output = cli.get("output")
        flags = _emit_formats(cli, output)
        for key, label in _UNSUPPORTED_EMIT.items():
            if flags[key]:
                result.note("warning", yaml_path, f"{label} output is not supported yet and was not carried over")
        for key, reason in _UNUSED_CLI.items():
            if cli.get(key):
                result.note("warning", yaml_path, f"cli.{key} was left out: {reason}")
        docx: dict[str, Any] = {}
        if not flags["emit-docx"]:
            result.note("warning", yaml_path, "createdocs built no Word file for this document. py-doc builds one")
        if output:
            docx["path"] = rel((base / output).with_suffix(".docx").resolve())
        template = None
        if cli.get("template") and cli.get("no-template"):
            result.note("info", yaml_path, "cli.template is ignored because cli.no-template is set")
        elif cli.get("template"):
            template = (base / cli["template"]).resolve()
            docx["template"] = rel(template)
        doc["outputs"] = {"docx": docx}
        templates[doc_id] = template

        for key in ("variables", "conditions"):
            if data.get(key):
                doc[key] = data[key]
                result.note("warning", yaml_path, f"{key} are kept in the file but py-doc does not apply them yet")

        documents[doc_id] = doc
        result.migrated.append((yaml_path, doc_id))

    # relationships
    for source_file, users in sources.items():
        if len(set(users)) > 1:
            result.note("info", source_file, f"is a source of several documents: {', '.join(sorted(set(users)))}")
    config: dict[str, Any] = {}
    shared = {t for t in templates.values() if t}
    if len(documents) > 1 and len(shared) == 1 and all(templates.values()):
        (common,) = shared
        config["outputs"] = {"docx": {"template": rel(common)}}
        for doc in documents.values():
            del doc["outputs"]["docx"]["template"]
        result.note("info", common, "is the Word template of every document, so it is set once under outputs")
    config["documents"] = documents
    result.config = config

    parse_config(config, config_dir)  # the file we write must load
    return result


def render(config: dict) -> str:
    header = "# Generated by `py-doc migrate`. Paths are relative to this file.\n"
    return header + yaml.safe_dump(config, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100)
