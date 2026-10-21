"""The ``lint.vale`` section of py-doc.yml: settings, and the checks that catch a bad definition before Vale runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

LEVELS = ("error", "warning", "suggestion")
INFO_LEVELS = {"error": "error", "warning": "warning", "suggestion": "info", "info": "info"}
ENABLED = ("auto", True, False)
# The rules that ship in the PyDoc style, and the options each takes besides `level`.
BUNDLED_RULES = {
    "SentenceLength": ("max",),
    "ParagraphLength": ("max",),
    "PassiveVoice": (),
    "WeaselWords": (),
    "Repeated": (),
    "DoubleSpace": (),
    "HeadingPunctuation": (),
    "HeadingCase": (),
    "Placeholders": (),
    "Spelling": (),
    "Terms": (),
    "Wordy": (),
    "Redundant": (),
    "Acronyms": (),
}
_KEYS = (
    "enabled", "binary", "min_alert_level", "packages", "spelling", "rules", "terms", "avoid", "ignore", "config", "rules_file",
)  # fmt: skip
_RULE_ID = re.compile(r"^[A-Za-z][\w-]*\.[A-Za-z][\w-]*$")


class ValeConfigError(ValueError):
    """A bad ``lint.vale`` value. The message names its place."""


@dataclass
class AvoidPattern:
    pattern: str
    message: str
    level: str = "warning"


@dataclass
class ValeRule:
    """A rule setting: ``level`` (None keeps the rule's own), ``off``, and options such as ``max``."""

    level: str | None = None
    off: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValeSettings:
    enabled: str | bool = "auto"
    binary: str | None = None
    min_alert_level: str = "suggestion"
    packages: list[str] = field(default_factory=list)
    spelling: str = "en-GB"
    rules: dict[str, ValeRule] = field(default_factory=dict)
    terms: dict[str, list[str]] = field(default_factory=dict)
    avoid: list[AvoidPattern] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    config: Path | None = None  # the user's own .vale.ini, used as it is
    managed_dir: Path | None = None  # where the generated files and downloaded packages live


def _level(value: Any, where: str, allowed: tuple[str, ...] = LEVELS) -> str:
    if value == "info":
        value = "suggestion"
    if value not in allowed:
        raise ValeConfigError(f"{where} must be one of {', '.join(allowed)}, not {value!r}")
    return value


def _regex(pattern: Any, where: str) -> str:
    if not isinstance(pattern, str) or not pattern:
        raise ValeConfigError(f"{where} must be a regular expression")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValeConfigError(f"{where} is not a valid regular expression: {exc}") from None
    return pattern


def _rule(rule_id: str, raw: Any, where: str) -> ValeRule:
    if not _RULE_ID.match(rule_id):
        raise ValeConfigError(f"{where} is not a rule id such as PyDoc.SentenceLength")
    style, _, name = rule_id.partition(".")
    if style == "PyDoc" and name not in BUNDLED_RULES:
        raise ValeConfigError(f"{where}: PyDoc has no rule '{name}'. Rules: {', '.join(sorted(BUNDLED_RULES))}")
    if raw is False or raw in ("off", "none"):  # YAML reads a bare `off` as false
        return ValeRule(off=True)
    if isinstance(raw, str):
        return ValeRule(level=_level(raw, where))
    if not isinstance(raw, dict):
        raise ValeConfigError(f"{where} must be a level, off, or a mapping with level and options")
    options = dict(raw)
    rule = ValeRule()
    if "level" in options:
        rule.level = _level(options.pop("level"), f"{where}.level")
    if options and style != "PyDoc":
        raise ValeConfigError(f"{where}: options can only be set on PyDoc rules, and only a level on {style}")
    allowed = BUNDLED_RULES.get(name, ())
    for key, value in options.items():
        if key not in allowed:
            raise ValeConfigError(f"{where} has unknown key '{key}'. Keys: {', '.join(('level', *allowed))}")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValeConfigError(f"{where}.{key} must be a whole number of 1 or more")
        rule.options[key] = value
    return rule


def _merge(settings: ValeSettings, data: dict, where: str, root: Path, depth: int = 0) -> None:
    unknown = [k for k in data if k not in _KEYS]
    if unknown:
        raise ValeConfigError(f"{where} has unknown key '{unknown[0]}'. Keys: {', '.join(_KEYS)}")
    if depth and "rules_file" in data:
        raise ValeConfigError(f"{where}.rules_file: a rules file cannot name another rules file")
    files = data.get("rules_file", [])
    for number, name in enumerate([files] if isinstance(files, str) else files):
        if not isinstance(name, str):
            raise ValeConfigError(f"{where}.rules_file must be a file name or a list of them")
        path = root / name
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ValeConfigError(f"{where}.rules_file: cannot read '{path}': {exc}") from None
        if not isinstance(loaded, dict):
            raise ValeConfigError(f"{path} must hold a mapping")
        _merge(settings, loaded, str(path), path.parent, depth + 1)

    if "enabled" in data:
        value = data["enabled"]
        if value not in ENABLED or (isinstance(value, int) and not isinstance(value, bool)):
            raise ValeConfigError(f"{where}.enabled must be auto, true or false, not {value!r}")
        settings.enabled = value
    if "binary" in data:
        if not isinstance(data["binary"], str) or not data["binary"]:
            raise ValeConfigError(f"{where}.binary must be a path or a command name")
        settings.binary = data["binary"]
    if "min_alert_level" in data:
        settings.min_alert_level = _level(data["min_alert_level"], f"{where}.min_alert_level")
    if "packages" in data:
        packages = data["packages"]
        if not isinstance(packages, list) or not all(
            isinstance(p, str) and re.fullmatch(r"[\w.-]+", p) for p in packages
        ):
            raise ValeConfigError(f"{where}.packages must be a list of package names")
        settings.packages = list(dict.fromkeys([*settings.packages, *packages]))
    if "spelling" in data:
        if data["spelling"] not in ("en-GB", "en-US", False, "off"):
            raise ValeConfigError(f"{where}.spelling must be en-GB, en-US or off")
        settings.spelling = "off" if data["spelling"] in (False, "off") else data["spelling"]
    for rule_id, raw in (data.get("rules") or {}).items():
        settings.rules[str(rule_id)] = _rule(str(rule_id), raw, f"{where}.rules.{rule_id}")
    for term, variants in (data.get("terms") or {}).items():
        if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
            raise ValeConfigError(f"{where}.terms.{term} must be a list of wrong spellings")
        settings.terms[str(term)] = list(variants)
    for number, item in enumerate(data.get("avoid") or []):
        place = f"{where}.avoid[{number}]"
        if not isinstance(item, dict) or not set(item) <= {"pattern", "message", "level"} or "pattern" not in item:
            raise ValeConfigError(f"{place} must be a mapping with pattern, message and level")
        settings.avoid.append(
            AvoidPattern(
                _regex(item["pattern"], f"{place}.pattern"),
                str(item.get("message") or "Do not use '%s'."),
                _level(item.get("level", "warning"), f"{place}.level"),
            )
        )
    if "ignore" in data:
        if not isinstance(data["ignore"], list) or not all(isinstance(p, str) for p in data["ignore"]):
            raise ValeConfigError(f"{where}.ignore must be a list of file patterns")
        settings.ignore.extend(data["ignore"])
    if "config" in data:
        if not isinstance(data["config"], str):
            raise ValeConfigError(f"{where}.config must be a file name")
        settings.config = root / data["config"]


def parse_vale(data: Any, root: Path) -> ValeSettings:
    """Settings from the ``lint.vale`` mapping. Paths are relative to ``root``. Raises :class:`ValeConfigError`."""
    if not isinstance(data, dict):
        raise ValeConfigError("lint.vale must be a mapping")
    settings = ValeSettings()
    # Rules files come first, so the inline keys override them
    _merge(settings, data, "lint.vale", root)
    if settings.config is not None and not settings.config.is_file():
        raise ValeConfigError(f"lint.vale.config: '{settings.config}' does not exist")
    return settings
