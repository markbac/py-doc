"""The ``py-doc.yml`` project configuration: one file for documents, outputs and lint policy.

Paths in the file are relative to the file. Loading checks every key, so a typo is an error that
names its place (``documents.guide.sources[1].page_brek``), never a setting that is silently ignored.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .files import DEFAULT_EXCLUDE_DIRS
from .lint.config import DEFAULT_ALLOWED_ACRONYMS, LintConfig
from .markdown.frontmatter import Metadata

logger = logging.getLogger(__name__)

CONFIG_NAMES = ("py-doc.yml", "py-doc.yaml")
FORMATS = {"docx": ".docx", "pptx": ".pptx"}
SEVERITIES = ("error", "warning", "info")
DEFAULT_OUTPUT_DIR = "build"

# Top-level sections that are accepted and kept, but nothing uses them yet.
RESERVED_SECTIONS = ("collections", "bundles", "content", "site")

_META_KEYS = (
    "title", "subtitle", "author", "date", "version", "status", "document_number", "description",
    "classification", "subject", "keywords", "category", "company", "toc_depth",
)  # fmt: skip
_OUTPUT_OPTIONS = {
    "docx": ("path", "template", "keep_template_body", "allow_missing_template"),
    "pptx": (
        "path", "template", "keep_template_slides", "allow_missing_template", "split_level", "title_layout",
        "content_layout",
    ),
}  # fmt: skip


class ConfigError(Exception):
    """The configuration file cannot be found, read or understood."""


@dataclass
class Source:
    file: Path
    heading_offset: int = 0
    title: str | None = None
    page_break: bool = False
    include: bool = True


@dataclass
class OutputSettings:
    """What one output format needs. ``path`` is the file for a document, or the folder in the defaults."""

    path: Path | None = None
    template: Path | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentConfig:
    id: str
    meta: dict[str, Any] = field(default_factory=dict)
    sources: list[Source] = field(default_factory=list)
    outputs: dict[str, OutputSettings] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)

    def metadata(self) -> Metadata:
        """The document properties set in the configuration. Unset ones stay None."""
        meta = self.meta
        extra = {k: v for k, v in meta.items() if k not in ("title", "subtitle", "author", "date", "version", "status", "document_number", "keywords")}
        return Metadata(
            title=_text(meta.get("title")),
            subtitle=_text(meta.get("subtitle")),
            author=_text(meta.get("author")),
            date=_text(meta.get("date")),
            version=_text(meta.get("version")),
            status=_text(meta.get("status")),
            document_id=_text(meta.get("document_number")),
            keywords=_text(meta.get("keywords")),
            extra=extra,
        )


@dataclass
class ProjectConfig:
    root: Path
    name: str | None = None
    documents: dict[str, DocumentConfig] = field(default_factory=dict)
    outputs: dict[str, OutputSettings] = field(default_factory=dict)
    lint: LintConfig = field(default_factory=LintConfig)
    build: dict[str, Any] = field(default_factory=dict)
    reserved: dict[str, Any] = field(default_factory=dict)

    def output_path(self, document: DocumentConfig, fmt: str) -> Path:
        settings = document.outputs.get(fmt)
        if settings and settings.path:
            return settings.path
        default = self.outputs.get(fmt)
        folder = default.path if default and default.path else self.root / DEFAULT_OUTPUT_DIR
        return folder / f"{document.id}{FORMATS[fmt]}"

    def output_formats(self, document: DocumentConfig) -> list[str]:
        """Formats a document builds: the ones it lists, else docx."""
        return [fmt for fmt in FORMATS if fmt in document.outputs] or ["docx"]


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) or None
    return str(value).strip() or None


def find_config(start: Path) -> Path | None:
    """The nearest ``py-doc.yml`` in ``start`` or a parent directory."""
    start = start.resolve()
    for folder in (start, *start.parents):
        for name in CONFIG_NAMES:
            if (folder / name).is_file():
                return folder / name
    return None


def load_config(path: Path) -> ProjectConfig:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"{path}: not valid UTF-8") from exc
    try:
        return parse_config(data if data is not None else {}, path.resolve().parent)
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from None


# --- checking helpers ----------------------------------------------------------------------------


def _mapping(value: Any, where: str) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{where} must be a mapping")
    return value


def _only(data: dict, allowed, where: str) -> None:
    for key in data:
        if key not in allowed:
            raise ConfigError(f"unknown key '{key}' in {where}. Allowed: {', '.join(sorted(allowed))}")


def _typed(data: dict, key: str, kind, where: str, default=None):
    value = data.get(key, default)
    if value is None:
        return default
    if kind is int and isinstance(value, bool) or not isinstance(value, kind):
        raise ConfigError(f"{where}.{key} must be {getattr(kind, '__name__', 'of the right type')}")
    return value


def _path(root: Path, value: Any, where: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{where} must be a path")
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()


# --- sections ------------------------------------------------------------------------------------


def parse_config(data: Any, root: Path) -> ProjectConfig:
    top = _mapping(data, "the configuration")
    _only(top, ("project", "documents", "outputs", "lint", "build", *RESERVED_SECTIONS), "the top level")
    config = ProjectConfig(root=root)

    project = _mapping(top.get("project", {}), "project")
    _only(project, ("name",), "project")
    config.name = _typed(project, "name", str, "project")

    config.outputs = _parse_outputs(_mapping(top.get("outputs", {}), "outputs"), root, "outputs", defaults=True)

    for doc_id, raw in _mapping(top.get("documents", {}), "documents").items():
        config.documents[str(doc_id)] = _parse_document(str(doc_id), raw, root)

    config.lint = _parse_lint(_mapping(top.get("lint", {}), "lint"))
    config.build = _mapping(top.get("build", {}), "build")

    for name in RESERVED_SECTIONS:
        if name in top:
            config.reserved[name] = top[name]
            logger.warning(f"The '{name}' section is accepted but not used yet")
    return config


def _parse_outputs(data: dict, root: Path, where: str, defaults: bool = False) -> dict[str, OutputSettings]:
    _only(data, FORMATS, where)
    result: dict[str, OutputSettings] = {}
    for fmt, raw in data.items():
        place = f"{where}.{fmt}"
        raw = {} if raw is None else _mapping(raw, place)
        _only(raw, ("dir", *_OUTPUT_OPTIONS[fmt]) if defaults else _OUTPUT_OPTIONS[fmt], place)
        key = "dir" if defaults else "path"
        settings = OutputSettings()
        if key in raw:
            settings.path = _path(root, raw[key], f"{place}.{key}")
        elif defaults and "path" in raw:
            raise ConfigError(f"{place} takes 'dir', not 'path'")
        if "template" in raw and raw["template"] is not None:
            settings.template = _path(root, raw["template"], f"{place}.template")
        for option in _OUTPUT_OPTIONS[fmt]:
            if option in ("path", "template") or option not in raw:
                continue
            kind = int if option == "split_level" else str if option.endswith("layout") else bool
            settings.options[option] = _typed(raw, option, kind, place)
        if "split_level" in settings.options and not 1 <= settings.options["split_level"] <= 6:
            raise ConfigError(f"{place}.split_level must be 1 to 6")
        result[fmt] = settings
    return result


def _parse_document(doc_id: str, raw: Any, root: Path) -> DocumentConfig:
    where = f"documents.{doc_id}"
    data = _mapping(raw, where)
    _only(data, (*_META_KEYS, "sources", "outputs", "variables", "conditions"), where)
    doc = DocumentConfig(id=doc_id)
    for key in _META_KEYS:
        if key in data and data[key] is not None:
            doc.meta[key] = data[key]
    if "toc_depth" in doc.meta:
        _typed(doc.meta, "toc_depth", int, where)

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ConfigError(f"{where}.sources must be a list with at least one file")
    for index, item in enumerate(sources):
        place = f"{where}.sources[{index}]"
        entry = {"file": item} if isinstance(item, str) else _mapping(item, place)
        _only(entry, ("file", "heading_offset", "title", "page_break", "include"), place)
        if "file" not in entry:
            raise ConfigError(f"{place} needs a 'file'")
        doc.sources.append(
            Source(
                file=_path(root, entry["file"], f"{place}.file"),
                heading_offset=_typed(entry, "heading_offset", int, place, 0),
                title=_typed(entry, "title", str, place),
                page_break=_typed(entry, "page_break", bool, place, False),
                include=_typed(entry, "include", bool, place, True),
            )
        )
    doc.outputs = _parse_outputs(_mapping(data.get("outputs", {}), f"{where}.outputs"), root, f"{where}.outputs")
    doc.variables = _mapping(data.get("variables", {}), f"{where}.variables")
    doc.conditions = _mapping(data.get("conditions", {}), f"{where}.conditions")
    return doc


def _parse_lint(data: dict) -> LintConfig:
    _only(data, ("exclude", "rules", "glossary", "phrases", "acronyms"), "lint")
    config = LintConfig()

    if "exclude" in data:
        names = _typed(data, "exclude", list, "lint")
        config.exclude_dirs = DEFAULT_EXCLUDE_DIRS | frozenset(str(name) for name in names)

    rules = _mapping(data.get("rules", {}), "lint.rules")
    severities = dict(config.severities)
    disabled: set[str] = set()
    for rule, level in rules.items():
        if rule not in severities:
            raise ConfigError(f"lint.rules has unknown rule '{rule}'. Rules: {', '.join(sorted(severities))}")
        if level in (False, "off", "none"):  # YAML reads a bare `off` as false
            disabled.add(rule)
        elif level in SEVERITIES:
            severities[rule] = level
        else:
            raise ConfigError(f"lint.rules.{rule} must be one of {', '.join(SEVERITIES)} or off, not {level!r}")
    config.severities = severities
    config.disabled_rules = frozenset(disabled)

    if "glossary" in data:
        glossary = _mapping(data["glossary"], "lint.glossary")
        for term, variants in glossary.items():
            if not isinstance(variants, list):
                raise ConfigError(f"lint.glossary.{term} must be a list of wrong spellings")
            config.glossary[str(term)] = [str(v) for v in variants]
    if "phrases" in data:
        for phrase, suggestion in _mapping(data["phrases"], "lint.phrases").items():
            config.redundant_phrases[str(phrase)] = "" if suggestion is None else str(suggestion)

    acronyms = _mapping(data.get("acronyms", {}), "lint.acronyms")
    _only(acronyms, ("min_length", "allowed"), "lint.acronyms")
    if "min_length" in acronyms:
        config.acronym_min_length = _typed(acronyms, "min_length", int, "lint.acronyms")
        if config.acronym_min_length < 2:
            raise ConfigError("lint.acronyms.min_length must be at least 2")
    if "allowed" in acronyms:
        allowed = _typed(acronyms, "allowed", list, "lint.acronyms")
        config.allowed_acronyms = DEFAULT_ALLOWED_ACRONYMS | frozenset(str(a) for a in allowed)
    return config
