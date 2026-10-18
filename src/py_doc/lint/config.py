"""Built-in lint policy. Projects override it by building their own :class:`LintConfig`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from py_doc.files import DEFAULT_EXCLUDE_DIRS

from .vale_config import ValeSettings

DEFAULT_GLOSSARY: dict[str, list[str]] = {
    "LwM2M": ["lwm2m", "LWM2M", "Lw2m"],
    "DTLS": ["dtls", "Dtls"],
    "UART": ["uart", "Uart"],
    "MQTT": ["mqtt", "Mqtt"],
    "IPv6": ["ipv6", "Ipv6"],
    "API": ["api", "Api"],
    "JSON": ["json", "Json"],
    "YAML": ["yaml", "Yaml"],
    "HTTP": ["http", "Http"],
    "HTTPS": ["https", "Https"],
}

# Redundant phrase and the shorter wording to use instead (empty: just delete it).
DEFAULT_PHRASES: dict[str, str] = {
    "in order to": "to",
    "at this point in time": "now",
    "due to the fact that": "because",
    "for the purpose of": "for",
    "has the ability to": "can",
    "it is important to note that": "",
}

# All-capitals words that are common enough not to need a definition.
DEFAULT_ALLOWED_ACRONYMS = frozenset(
    {"TOC", "URL", "CLI", "HTML", "CSS", "SVG", "PNG", "CPU", "RAM", "ROM", "OK"}
    | {"NOTE", "TODO", "FIXME", "WARNING", "IMPORTANT", "TIP", "README", "LICENSE", "FAQ", "PDF", "USB"}
)

RULE_GLOSSARY = "DOC001"
RULE_REDUNDANT = "DOC002"
RULE_ACRONYM = "DOC003"
RULE_DIRECTIVE = "DOC004"
RULE_HEADING_JUMP = "DOC005"
RULE_BROKEN_LINK = "DOC006"
RULE_IMAGE_ALT = "DOC007"
RULE_SENTENCE_LENGTH = "DOC008"
RULE_HEADING_LENGTH = "DOC009"
RULE_DUPLICATE_HEADING = "DOC010"
RULE_UNCLOSED_FENCE = "DOC011"
RULE_REQUIRED_SECTION = "DOC012"
RULE_TERMINOLOGY = "DOC013"
ACRONYM_SCOPES = ("file", "document")
DEFAULT_ACRONYM_SUGGESTION = "Define it on first use, for example 'Full Name ({acronym})'."
C4_RULES = {"C4001": "warning", "C4002": "warning", "C4003": "warning", "C4004": "info"}  # see py_doc.c4.check


@dataclass
class MarkdownlintSettings:
    """markdownlint, run in the container: a config file or an inline mapping, and how serious a finding is."""

    config: Path | None = None
    inline: dict[str, Any] | None = None
    severity: str = "warning"


@dataclass
class LintConfig:
    glossary: dict[str, list[str]] = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_GLOSSARY.items()})
    redundant_phrases: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PHRASES))
    acronym_min_length: int = 3
    allowed_acronyms: frozenset[str] = DEFAULT_ALLOWED_ACRONYMS
    acronym_require_definition: bool = True  # False: report only a use before a later definition
    acronym_scope: str = "file"  # document: a definition in an earlier file of the same document counts
    acronym_suggestion: str = DEFAULT_ACRONYM_SUGGESTION  # {acronym} is replaced
    sentence_words: int = 40  # DOC008: a sentence with more words than this
    heading_length: int = 80  # DOC009: a heading with more characters than this
    required_sections: dict[str, list[str]] = field(default_factory=dict)  # DOC012: document id (or *) -> headings
    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS
    disabled_rules: frozenset[str] = frozenset()
    severities: dict[str, str] = field(
        default_factory=lambda: {
            RULE_GLOSSARY: "warning", RULE_REDUNDANT: "warning", RULE_ACRONYM: "info", RULE_DIRECTIVE: "error",
            RULE_HEADING_JUMP: "warning", RULE_BROKEN_LINK: "warning", RULE_IMAGE_ALT: "warning",
            RULE_SENTENCE_LENGTH: "info", RULE_HEADING_LENGTH: "info", RULE_DUPLICATE_HEADING: "info",
            RULE_UNCLOSED_FENCE: "error", RULE_REQUIRED_SECTION: "warning", RULE_TERMINOLOGY: "info", **C4_RULES,
        }  # fmt: skip
    )
    structure: list = field(default_factory=list)  # StructureRule entries, see lint.structure
    markdownlint: MarkdownlintSettings | None = None
    vale: ValeSettings = field(default_factory=ValeSettings)
    root: Path = field(default_factory=Path.cwd)  # the project folder: where the managed Vale folder lives
    documents: dict[str, list[Path]] = field(default_factory=dict)  # document id -> its source files, in order
