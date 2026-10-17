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
from .lint.config import DEFAULT_ALLOWED_ACRONYMS, LintConfig, MarkdownlintSettings
from .lint.structure import StructureRuleError, load_rules, parse_rules
from .lint.vale_config import ValeConfigError, parse_vale
from .markdown.frontmatter import Metadata
from .naming import check_name_pattern, expand_name
from .runtime import RuntimeSettings

logger = logging.getLogger(__name__)

CONFIG_NAMES = ("py-doc.yml", "py-doc.yaml")
FORMATS = {"docx": ".docx", "pptx": ".pptx", "pdf": ".pdf", "html": ".html"}
# Options of the retired native renderers, with what to do instead.
REMOVED_OPTIONS = {
    "engine": "pandoc is the only engine now, so remove 'engine'",
    "keep_template_body": "the document goes where the template has its [[INSERTCONTENT]] line (see 'marker'), so remove it",
    "keep_template_slides": "pandoc starts from the template's layouts and drops its slides, so remove it",
    "title_layout": "pandoc picks the layouts by their standard names (Title Slide, Title and Content), so remove it",
    "content_layout": "pandoc picks the layouts by their standard names (Title Slide, Title and Content), so remove it",
}
SEVERITIES = ("error", "warning", "info")
DEFAULT_OUTPUT_DIR = "build"

# Top-level sections that are accepted and kept, but nothing uses them yet.
RESERVED_SECTIONS = ("collections", "bundles", "content")
SITE_ENGINES = ("mkdocs", "starlight")
DEFAULT_SITE_DIR = "site"

_META_KEYS = (
    "title", "subtitle", "author", "date", "version", "status", "document_number", "description",
    "classification", "subject", "keywords", "category", "company", "toc_depth",
)  # fmt: skip
_OUTPUT_OPTIONS = {
    "docx": (
        "path", "template", "allow_missing_template", "name", "placeholder_prefix", "marker", "toc", "heading_numbers",
    ),
    "pptx": (
        "path", "template", "allow_missing_template", "split_level", "name", "footer", "heading_numbers",
    ),
    "pdf": ("path", "template", "toc", "name", "number_sections", "heading_numbers"),
    "html": ("path", "template", "toc", "name", "number_sections", "heading_numbers"),
}  # fmt: skip


_OPTION_TYPES = {
    "split_level": int,
    "name": str, "placeholder_prefix": str, "marker": str, "footer": str, "heading_numbers": str,
}  # fmt: skip
HEADING_NUMBERS = ("auto", "strip", "keep")


class ConfigError(Exception):
    """The configuration file cannot be found, read or understood."""


@dataclass
class StructurizrSpec:
    """A source made from a Structurizr workspace: ``Source.file`` is the ``.dsl`` or ``workspace.json``."""

    levels: list[str] = field(default_factory=list)  # empty: all levels
    systems: list[str] = field(default_factory=list)  # empty: all systems
    engine: str = "browser"  # browser (Structurizr Local and Chromium) or source (the diagram source as a code block)
    format: str = "png"  # png or svg for the browser engine, plantuml or mermaid for source


@dataclass
class Source:
    file: Path
    heading_offset: int = 0
    title: str | None = None
    page_break: bool = False
    include: bool = True
    structurizr: StructurizrSpec | None = None
    site_path: str | None = None  # the page's path on a site below the document's folder, without .md: cloud/kafka


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
class C4Settings:
    """The ``c4:`` section: how Structurizr is run."""

    cli: str | None = None  # a structurizr-cli on this machine, instead of the one in the tool container
    image: str | None = None  # the Structurizr Local image, such as structurizr/structurizr@sha256:...
    port: int | None = None  # the local port Structurizr Local is published on


@dataclass
class SiteConfig:
    """The ``site:`` section: a web site made of the documents, built by MkDocs or Astro + Starlight."""

    engine: str
    dir: Path
    title: str | None = None
    documents: list[str] = field(default_factory=list)  # empty: every document, in the order they are defined
    downloads: list[str] = field(default_factory=list)  # built outputs (pdf, docx, ...) linked from each document's pages
    targets: dict[str, str] = field(default_factory=dict)  # MkDocs: a site per config file in site.dir, sharing the pages
    pages: dict[str, str] = field(default_factory=dict)  # hand-written pages for the navigation, after the documents: title -> path


@dataclass
class ProjectConfig:
    root: Path
    name: str | None = None
    documents: dict[str, DocumentConfig] = field(default_factory=dict)
    outputs: dict[str, OutputSettings] = field(default_factory=dict)
    lint: LintConfig = field(default_factory=LintConfig)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    c4: C4Settings = field(default_factory=C4Settings)
    report: Path | None = None  # reports.path: where `py-doc build` writes its JSON report
    site: SiteConfig | None = None
    build: dict[str, Any] = field(default_factory=dict)
    reserved: dict[str, Any] = field(default_factory=dict)

    def output_path(self, document: DocumentConfig, fmt: str, version: str | None = None) -> Path:
        """Where an output goes. With a ``name`` pattern the file name is the pattern, else exactly the path given."""
        settings = document.outputs.get(fmt)
        default = self.outputs.get(fmt)
        if settings and settings.path:
            path = settings.path
        else:
            folder = default.path if default and default.path else self.root / DEFAULT_OUTPUT_DIR
            path = folder / f"{document.id}{FORMATS[fmt]}"
        pattern = {**(default.options if default else {}), **(settings.options if settings else {})}.get("name")
        return path.with_name(expand_name(pattern, path.stem, version) + path.suffix) if pattern else path

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
    _only(top, ("project", "documents", "outputs", "lint", "build", "runtime", "reports", "c4", "site", *RESERVED_SECTIONS), "the top level")
    config = ProjectConfig(root=root)

    project = _mapping(top.get("project", {}), "project")
    _only(project, ("name",), "project")
    config.name = _typed(project, "name", str, "project")

    config.outputs = _parse_outputs(_mapping(top.get("outputs", {}), "outputs"), root, "outputs", defaults=True)

    for doc_id, raw in _mapping(top.get("documents", {}), "documents").items():
        config.documents[str(doc_id)] = _parse_document(str(doc_id), raw, root)

    config.lint = _parse_lint(_mapping(top.get("lint", {}), "lint"), root)
    config.lint.documents = {
        doc_id: [source.file for source in doc.sources if source.include and source.structurizr is None] for doc_id, doc in config.documents.items()
    }
    config.build = _mapping(top.get("build", {}), "build")
    c4 = _mapping(top.get("c4", {}), "c4")
    _only(c4, ("cli", "image", "port"), "c4")
    config.c4 = C4Settings(_typed(c4, "cli", str, "c4"), _typed(c4, "image", str, "c4"), _typed(c4, "port", int, "c4"))
    config.runtime = _parse_runtime(_mapping(top.get("runtime", {}), "runtime"))
    reports = _mapping(top.get("reports", {}), "reports")
    _only(reports, ("path",), "reports")
    if "path" in reports:
        config.report = _path(root, reports["path"], "reports.path")

    if "site" in top:
        config.site = _parse_site(_mapping(top["site"] or {}, "site"), root, config)

    for name in RESERVED_SECTIONS:
        if name in top:
            config.reserved[name] = top[name]
            logger.warning(f"The '{name}' section is accepted but not used yet")
    return config


def _parse_site(data: dict, root: Path, config: ProjectConfig) -> SiteConfig:
    _only(data, ("engine", "dir", "title", "documents", "downloads", "targets", "pages"), "site")
    engine = _typed(data, "engine", str, "site")
    if engine not in SITE_ENGINES:
        raise ConfigError(f"site.engine must be one of {', '.join(SITE_ENGINES)}, not {engine!r}")
    documents = [str(name) for name in _typed(data, "documents", list, "site", [])]
    for name in documents:
        if name not in config.documents:
            raise ConfigError(f"site.documents names '{name}', which is not under documents. Defined: {', '.join(config.documents)}")
    downloads = [str(fmt) for fmt in _typed(data, "downloads", list, "site", [])]
    for fmt in downloads:
        if fmt not in FORMATS:
            raise ConfigError(f"site.downloads names '{fmt}', which is not a format. Use {', '.join(FORMATS)}")
    targets = {str(name): str(file) for name, file in _mapping(data.get("targets") or {}, "site.targets").items()}
    if targets and engine != "mkdocs":
        raise ConfigError("site.targets needs engine: mkdocs. Each target is a MkDocs config file in site.dir")
    return SiteConfig(
        engine=engine,
        dir=_path(root, data.get("dir", DEFAULT_SITE_DIR), "site.dir"),
        title=_typed(data, "title", str, "site") or config.name,
        documents=documents,
        downloads=downloads,
        targets=targets,
        pages={str(title): str(path) for title, path in _mapping(data.get("pages") or {}, "site.pages").items()},
    )


def _parse_runtime(data: dict) -> RuntimeSettings:
    _only(data, ("docker", "wsl_distro"), "runtime")
    return RuntimeSettings(
        docker=_typed(data, "docker", str, "runtime"), wsl_distro=_typed(data, "wsl_distro", str, "runtime")
    )


def _parse_outputs(data: dict, root: Path, where: str, defaults: bool = False) -> dict[str, OutputSettings]:
    _only(data, FORMATS, where)
    result: dict[str, OutputSettings] = {}
    for fmt, raw in data.items():
        place = f"{where}.{fmt}"
        raw = {} if raw is None else _mapping(raw, place)
        for option, advice in REMOVED_OPTIONS.items():
            if option in raw:
                raise ConfigError(f"{place}.{option} is no longer an option: {advice}")
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
            settings.options[option] = _typed(raw, option, _OPTION_TYPES.get(option, bool), place)
        if "name" in settings.options:
            try:
                check_name_pattern(settings.options["name"], f"{place}.name")
            except ValueError as exc:
                raise ConfigError(str(exc)) from None
        if settings.options.get("heading_numbers", "auto") not in HEADING_NUMBERS:
            raise ConfigError(f"{place}.heading_numbers must be one of {', '.join(HEADING_NUMBERS)}")
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
        spec = None
        if "structurizr" in entry:
            _only(entry, ("structurizr", "levels", "systems", "diagrams", "heading_offset", "title", "page_break"), place)
            spec = _parse_structurizr(entry, place)
            entry = {**entry, "file": entry["structurizr"]}
        _only(entry, ("file", "structurizr", "levels", "systems", "diagrams", "heading_offset", "title", "page_break", "include", "site_path"), place)
        if "file" not in entry:
            raise ConfigError(f"{place} needs a 'file' or a 'structurizr' workspace")
        doc.sources.append(
            Source(
                structurizr=spec,
                file=_path(root, entry["file"], f"{place}.file"),
                heading_offset=_typed(entry, "heading_offset", int, place, 0),
                title=_typed(entry, "title", str, place),
                page_break=_typed(entry, "page_break", bool, place, False),
                include=_typed(entry, "include", bool, place, True),
                site_path=_site_path(entry, place),
            )
        )
    doc.outputs = _parse_outputs(_mapping(data.get("outputs", {}), f"{where}.outputs"), root, f"{where}.outputs")
    doc.variables = _mapping(data.get("variables", {}), f"{where}.variables")
    doc.conditions = _mapping(data.get("conditions", {}), f"{where}.conditions")
    return doc


def _site_path(entry: dict, place: str) -> str | None:
    """A page path below the document's folder, such as cloud/kafka: relative, with / separators and no .md."""
    value = _typed(entry, "site_path", str, place)
    if value is None:
        return None
    path = value.strip().replace("\\", "/").removesuffix(".md").strip("/")
    if not path or value.startswith("/") or any(part in ("", ".", "..") for part in path.split("/")):
        raise ConfigError(f"{place}.site_path must be a path below the document's folder, such as cloud/kafka")
    return path


def _parse_structurizr(entry: dict, place: str) -> StructurizrSpec:
    from .c4.generate import LEVELS

    spec = StructurizrSpec()
    levels = _typed(entry, "levels", list, place, [])
    for level in levels:
        if level not in LEVELS:
            raise ConfigError(f"{place}.levels has unknown level '{level}'. Levels: {', '.join(LEVELS)}")
    spec.levels = [str(level) for level in levels]
    spec.systems = [str(name) for name in _typed(entry, "systems", list, place, [])]
    diagrams = _mapping(entry.get("diagrams", {}), f"{place}.diagrams")
    _only(diagrams, ("engine", "format"), f"{place}.diagrams")
    spec.engine = _typed(diagrams, "engine", str, f"{place}.diagrams", "browser")
    if spec.engine not in ("browser", "source"):
        raise ConfigError(f"{place}.diagrams.engine must be browser or source, not {spec.engine!r}")
    default = "png" if spec.engine == "browser" else "mermaid"
    spec.format = _typed(diagrams, "format", str, f"{place}.diagrams", default)
    allowed = ("png", "svg") if spec.engine == "browser" else ("plantuml", "mermaid")
    if spec.format not in allowed:
        raise ConfigError(f"{place}.diagrams.format must be one of {', '.join(allowed)} for the {spec.engine} engine")
    return spec


def _parse_markdownlint(data: dict, root: Path) -> MarkdownlintSettings:
    _only(data, ("config", "severity"), "lint.markdownlint")
    settings = MarkdownlintSettings()
    raw = data.get("config")
    if isinstance(raw, str):
        settings.config = _path(root, raw, "lint.markdownlint.config")
    elif isinstance(raw, dict):
        settings.inline = raw
    elif raw is not None:
        raise ConfigError("lint.markdownlint.config must be a file name or a mapping of markdownlint settings")
    settings.severity = data.get("severity", "warning")
    if settings.severity not in SEVERITIES:
        raise ConfigError(f"lint.markdownlint.severity must be one of {', '.join(SEVERITIES)}")
    return settings


def _parse_lint(data: dict, root: Path) -> LintConfig:
    _only(data, ("exclude", "rules", "glossary", "phrases", "acronyms", "structure", "markdownlint", "vale"), "lint")
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

    if "structure" in data:
        raw = data["structure"]
        try:
            config.structure = load_rules(_path(root, raw, "lint.structure")) if isinstance(raw, str) else parse_rules(raw)
        except StructureRuleError as exc:
            raise ConfigError(str(exc)) from None
    config.root = root
    if "vale" in data:
        try:
            config.vale = parse_vale(data["vale"], root)
        except ValeConfigError as exc:
            raise ConfigError(str(exc)) from None
    if "markdownlint" in data:
        config.markdownlint = _parse_markdownlint(_mapping(data["markdownlint"], "lint.markdownlint"), root)

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
