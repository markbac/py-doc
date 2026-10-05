"""Built-in lint policy. Projects override it by building their own :class:`LintConfig`."""

from __future__ import annotations

from dataclasses import dataclass, field

from py_doc.files import DEFAULT_EXCLUDE_DIRS

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


@dataclass
class LintConfig:
    glossary: dict[str, list[str]] = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_GLOSSARY.items()})
    redundant_phrases: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PHRASES))
    acronym_min_length: int = 3
    allowed_acronyms: frozenset[str] = DEFAULT_ALLOWED_ACRONYMS
    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS
    disabled_rules: frozenset[str] = frozenset()
    severities: dict[str, str] = field(
        default_factory=lambda: {RULE_GLOSSARY: "warning", RULE_REDUNDANT: "warning", RULE_ACRONYM: "info"}
    )
