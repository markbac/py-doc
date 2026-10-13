"""Vale, the prose linter, as a second engine of ``py-doc lint``.

py-doc writes the Vale configuration, the PyDoc style and the vocabulary from ``lint.vale`` (and from
``lint.glossary`` and ``lint.phrases``, so terms are defined once) into a managed folder, runs Vale with
JSON output, and turns the alerts into the same issues the built-in rules give.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Protocol

import yaml

from py_doc.errors import ConversionError, EnvironmentProblem, ToolFailed
from py_doc.runtime import Mount, Runtime

from .config import RULE_ACRONYM, RULE_GLOSSARY, RULE_REDUNDANT, LintConfig
from .model import LintIssue
from .vale_config import BUNDLED_RULES, INFO_LEVELS, ValeSettings

logger = logging.getLogger(__name__)

MIN_VERSION = (3, 0, 0)
TIMEOUT = 600
INSTALL_HELP = (
    "Install Vale: `brew install vale` (macOS), `winget install errata-ai.Vale` or `scoop install vale` (Windows), "
    "or download it from https://github.com/errata-ai/vale/releases. "
    "Or set lint.vale.enabled to false, or run with --engine builtin."
)
# Spellings that differ between British and American English. British on the left.
PLACEHOLDER_WORDS = frozenset({"TODO", "FIXME", "TBD", "TBC", "XXX"})  # the tokens of PyDoc.Placeholders
SPELLINGS = {
    "colour": "color", "behaviour": "behavior", "favour": "favor", "honour": "honor", "neighbour": "neighbor",
    "centre": "center", "metre": "meter", "litre": "liter", "fibre": "fiber", "theatre": "theater",
    "organise": "organize", "organisation": "organization", "recognise": "recognize", "realise": "realize",
    "optimise": "optimize", "optimisation": "optimization", "initialise": "initialize", "initialisation": "initialization",
    "customise": "customize", "customisation": "customization", "synchronise": "synchronize", "serialise": "serialize",
    "normalise": "normalize", "normalisation": "normalization", "standardise": "standardize", "utilise": "utilize",
    "minimise": "minimize", "maximise": "maximize", "summarise": "summarize", "authorise": "authorize",
    "authorisation": "authorization", "categorise": "categorize", "analyse": "analyze", "catalogue": "catalog",
    "dialogue": "dialog", "licence": "license", "defence": "defense", "offence": "offense", "grey": "gray",
    "cancelled": "canceled", "labelled": "labeled", "modelling": "modeling", "travelling": "traveling",
    "programme": "program", "judgement": "judgment", "ageing": "aging", "artefact": "artifact", "sceptical": "skeptical",
}  # fmt: skip


class ValeError(ConversionError):
    """Vale ran and failed, or printed something that is not its JSON."""


class Runner(Protocol):
    def run(self, argv: list, *, writable: bool = False, network: bool = False) -> tuple[int, str, str]: ...


class HostRunner:
    """Vale installed on this machine."""

    def __init__(self, binary: str, folder: Path, base: Path) -> None:
        self.binary, self.folder, self.base = binary, folder, base

    def run(self, argv, *, writable=False, network=False):
        command = [self.binary, *[str(a) for a in argv]]
        try:
            done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT, check=False)
        except FileNotFoundError as exc:
            raise EnvironmentProblem(f"Vale was not found at '{self.binary}'. {INSTALL_HELP}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ValeError(f"Vale did not finish within {TIMEOUT} seconds") from exc
        return done.returncode, done.stdout, done.stderr


class ContainerRunner:
    """Vale from the tool image."""

    def __init__(self, runtime: Callable[[], Runtime], folder: Path, base: Path) -> None:
        self._runtime, self.folder, self.base = runtime, folder, base

    def run(self, argv, *, writable=False, network=False):
        mounts = [Mount(self.folder, writable=writable), Mount(self.base)]
        try:
            result = self._runtime().run(
                ["vale", *argv], mounts=mounts, workdir=self.base, timeout=TIMEOUT, network=network, check=False
            )
        except ToolFailed as exc:
            raise ValeError(str(exc)) from exc
        return result.returncode, result.stdout, result.stderr


# --- the managed folder ---------------------------------------------------------------------------


def _bundled() -> list[tuple[str, str]]:
    root = resources.files("py_doc.lint").joinpath("vale_styles", "PyDoc")
    return [(item.name, item.read_text(encoding="utf-8")) for item in root.iterdir() if item.is_file()]


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)


@dataclass
class Workspace:
    folder: Path
    ini: Path
    files: list[str]  # the rules written, for --show-vale-config


def _rule_levels(settings: ValeSettings) -> dict[str, str]:
    return {rule_id: ("NO" if rule.off else rule.level) for rule_id, rule in settings.rules.items() if rule.off or rule.level}


def build_workspace(settings: ValeSettings, config: LintConfig, folder: Path) -> Workspace:
    """Write ``.vale.ini``, the PyDoc style and the vocabulary into ``folder``. Packages already in it are kept."""
    styles = folder / "styles"
    style = styles / "PyDoc"
    if style.exists():
        shutil.rmtree(style)
    style.mkdir(parents=True)
    (folder / ".gitignore").write_text("*\n", encoding="utf-8")
    written: list[str] = []

    def put(name: str, data: dict | str) -> None:
        text = data if isinstance(data, str) else _dump(data)
        (style / name).write_text(text, encoding="utf-8")
        written.append(f"PyDoc.{Path(name).stem}")

    # DOC001 to DOC003 turned off in py-doc.yml also turn off their Vale rules.
    off = {
        stem
        for stem, rule in (("Terms", RULE_GLOSSARY), ("Wordy", RULE_REDUNDANT), ("Redundant", RULE_REDUNDANT), ("Acronyms", RULE_ACRONYM))
        if rule in config.disabled_rules
    }
    for name, text in _bundled():
        if name == "meta.json":
            (style / name).write_text(text, encoding="utf-8")
            continue
        if Path(name).stem in off:
            continue
        rule = settings.rules.get(f"PyDoc.{Path(name).stem}")
        data = yaml.safe_load(text)
        if rule is not None:
            data.update(rule.options)
        if "max" in data:  # the length rules name their limit, which py-doc.yml can change
            data["message"] = data["message"].replace("{max}", str(data["max"]))
        put(name, data)

    terms = {**{t: list(v) for t, v in config.glossary.items()}, **settings.terms}
    swap = {wrong: right for right, wrongs in terms.items() for wrong in wrongs}
    if swap and "Terms" not in off:
        put("Terms.yml", {"extends": "substitution", "message": "Use '%s' instead of '%s'.", "level": "warning",
                          "ignorecase": False, "swap": swap})  # fmt: skip
    wordy = {p: s for p, s in config.redundant_phrases.items() if s}
    if wordy and "Wordy" not in off:
        put("Wordy.yml", {"extends": "substitution", "message": "Use '%s' instead of '%s'.", "level": "warning",
                          "ignorecase": True, "swap": wordy})  # fmt: skip
    empty = [p for p, s in config.redundant_phrases.items() if not s]
    if empty and "Redundant" not in off:
        put("Redundant.yml", {"extends": "existence", "message": "Delete '%s'.", "level": "warning",
                              "ignorecase": True, "tokens": empty})  # fmt: skip
    if settings.spelling != "off":
        pairs = SPELLINGS if settings.spelling == "en-US" else {us: gb for gb, us in SPELLINGS.items()}
        put("Spelling.yml", {"extends": "substitution", "message": f"Use the {settings.spelling} spelling '%s' instead of '%s'.",
                             "level": "warning", "ignorecase": True, "swap": pairs})  # fmt: skip
    allowed = sorted(config.allowed_acronyms)
    if "Acronyms" not in off:
        put("Acronyms.yml", {
            "extends": "conditional", "message": "Spell out '%s' the first time it is used.", "level": "suggestion",
            "first": rf"\b([A-Z]{{{config.acronym_min_length},}})\b", "second": rf"(?:\b[A-Z][a-z]+ )+\(([A-Z]{{{config.acronym_min_length},}})\)",
            "exceptions": allowed,
        })  # fmt: skip
    for number, item in enumerate(settings.avoid, 1):
        put(f"Avoid{number}.yml", {"extends": "existence", "message": item.message, "level": item.level,
                                   "nonword": True, "tokens": [item.pattern]})  # fmt: skip

    vocab = folder / "styles" / "config" / "vocabularies" / "PyDoc"
    vocab.mkdir(parents=True, exist_ok=True)
    # Vale exempts accepted words from every rule, so the words PyDoc.Placeholders reports must not be in the list.
    accepted = sorted({*terms, *config.allowed_acronyms} - PLACEHOLDER_WORDS)
    (vocab / "accept.txt").write_text("\n".join(accepted) + "\n", encoding="utf-8")

    ini = folder / ".vale.ini"
    packages = ", ".join(settings.packages)
    styles_used = ", ".join(["PyDoc", *settings.packages])
    lines = ["StylesPath = styles", f"MinAlertLevel = {settings.min_alert_level}", "Vocab = PyDoc"]
    if packages:
        lines.append(f"Packages = {packages}")
    lines += [
        "",
        "[*.{md,markdown}]",
        f"BasedOnStyles = {styles_used}",
        # Directives and variables are not prose
        r"TokenIgnores = (\[\[[^\]]*\]\]), (\{\{[^}]*\}\})",
    ]
    lines += [f"{rule_id} = {level}" for rule_id, level in sorted(_rule_levels(settings).items())]
    ini.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return Workspace(folder, ini, sorted(written))


# --- finding Vale and running it --------------------------------------------------------------------


def parse_version(text: str) -> tuple[int, ...] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return tuple(int(x) for x in match.groups()) if match else None


def find_binary(settings: ValeSettings) -> str | None:
    """The configured Vale, or the one on the PATH. None if there is none."""
    if settings.binary:
        found = shutil.which(settings.binary)
        return found or (settings.binary if Path(settings.binary).is_file() else None)
    return shutil.which("vale")


def make_runner(
    settings: ValeSettings, engine: str, folder: Path, base: Path, runtime: Callable[[], Runtime] | None
) -> Runner | None:
    """The runner to use, or None when Vale is not wanted (or is wanted only if present, and is not)."""
    wanted = settings.enabled is True or engine == "vale"
    if engine == "builtin" or settings.enabled is False:
        return None
    binary = find_binary(settings)
    if binary:
        return HostRunner(binary, folder, base)
    if settings.binary:
        raise EnvironmentProblem(f"lint.vale.binary '{settings.binary}' was not found. {INSTALL_HELP}")
    if wanted and runtime is not None:
        return ContainerRunner(runtime, folder, base)
    if wanted:
        raise EnvironmentProblem(f"Vale is not installed. {INSTALL_HELP}")
    logger.warning("Vale is not installed, so only the built-in rules ran. %s", INSTALL_HELP)
    return None


def check_version(runner: Runner) -> tuple[int, ...]:
    code, out, err = runner.run(["--version"])
    version = parse_version(out + err)
    if code != 0 or version is None:
        raise ValeError(f"Vale did not report its version: {(out + err).strip() or 'no output'}")
    if version < MIN_VERSION:
        needed = ".".join(map(str, MIN_VERSION))
        raise EnvironmentProblem(f"Vale {'.'.join(map(str, version))} is too old. py-doc needs {needed} or newer. {INSTALL_HELP}")
    return version


def selected(files: list[Path], settings: ValeSettings, base: Path) -> list[Path]:
    """The files that are not in ``lint.vale.ignore``. Patterns match the path from the working folder or the file name."""
    keep = []
    for path in files:
        try:
            shown = path.relative_to(base).as_posix()
        except ValueError:
            shown = path.as_posix()
        if not any(fnmatch.fnmatch(shown, p) or fnmatch.fnmatch(path.name, p) for p in settings.ignore):
            keep.append(path)
    return keep


def parse_output(text: str, files: list[Path]) -> list[LintIssue]:
    """Issues from Vale's JSON, which maps each file to its alerts. Raises :class:`ValeError` for anything else."""
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValeError(f"Vale printed output that is not JSON ({exc.msg}): {text.strip()[:200]}") from exc
    if not isinstance(data, dict) or "Code" in data and "Text" in data:
        raise ValeError(f"Vale reported an error: {data.get('Text', data) if isinstance(data, dict) else data}")
    by_name = {f.as_posix(): f for f in files}
    issues = []
    for name, alerts in data.items():
        path = by_name.get(Path(name).as_posix()) or Path(name).resolve()
        for alert in alerts:
            try:
                check = alert["Check"]
                line = int(alert["Line"])
                severity = INFO_LEVELS[alert.get("Severity", "warning")]
                message = alert["Message"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValeError(f"Vale printed an alert that py-doc cannot read ({exc!r}): {alert!r}") from exc
            action = alert.get("Action") or {}
            params = action.get("Params") or []
            suggestion = str(params[0]) if action.get("Name") == "replace" and params else None
            span = alert.get("Span") or []
            column = int(span[0]) if span else None
            issues.append(
                LintIssue(path, line, check, check.split(".")[0], message, severity, suggestion, column)
            )
    return issues


def run_vale(
    files: list[Path], runner: Runner, ini: Path, settings: ValeSettings, base: Path
) -> list[LintIssue]:
    """Run Vale on ``files``. Raises :class:`ValeError` when it fails, so a broken run is never a clean one."""
    files = selected([f.resolve() for f in files], settings, base)
    if not files:
        return []
    check_version(runner)
    argv = ["--output=JSON", "--no-exit", f"--config={ini}", *files]
    code, out, err = runner.run(argv)
    if code != 0:
        raise ValeError(f"Vale failed with exit status {code}: {(err or out).strip()}")
    return parse_output(out, files)


def drop_duplicates(vale: list[LintIssue], builtin: list[LintIssue]) -> list[LintIssue]:
    """Vale's term and wordy rules are the built-in DOC001 and DOC002 again. One problem, one line."""
    same = {("PyDoc.Terms", "DOC001"), ("PyDoc.Wordy", "DOC002"), ("PyDoc.Redundant", "DOC002")}
    seen = {(i.file, i.line, i.rule) for i in builtin}
    return [i for i in vale if not any(i.rule == v and (i.file, i.line, b) in seen for v, b in same)]


def sync(runner: Runner, ini: Path) -> str:
    """``vale sync``: download the configured packages into the managed folder."""
    code, out, err = runner.run([f"--config={ini}", "sync"], writable=True, network=True)
    if code != 0:
        raise ValeError(f"vale sync failed with exit status {code}: {(err or out).strip()}")
    return (out + err).strip()


def missing_packages(settings: ValeSettings, folder: Path) -> list[str]:
    return [p for p in settings.packages if not (folder / "styles" / p).is_dir()]


__all__ = [
    "BUNDLED_RULES", "ContainerRunner", "HostRunner", "ValeError", "build_workspace", "check_version", "drop_duplicates",
    "find_binary", "make_runner", "missing_packages", "parse_output", "run_vale", "sync",
]  # fmt: skip
