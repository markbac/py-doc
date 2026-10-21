"""What controls the name and look of a document: its status, its version and its file name."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from .errors import ConversionError

logger = logging.getLogger(__name__)

_FIELD = re.compile(r"\{(\w+)\}")
FIELDS = ("name", "version", "version_safe")


def git_version(start: Path) -> str:
    """``git describe --tags --always`` for the repository that holds ``start``.

    Raises ConversionError outside a repository, without git, or with no commit: a version that is
    quietly something else would end up on a controlled document.
    """
    folder = start if start.is_dir() else start.parent
    try:
        done = subprocess.run(
            ["git", "-C", str(folder), "describe", "--tags", "--always"],
            capture_output=True, text=True, encoding="utf-8", check=False, timeout=30,
        )  # fmt: skip
    except FileNotFoundError as exc:
        raise ConversionError("version: git needs git on the PATH, and it was not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(f"git did not answer within 30 seconds in '{folder}'") from exc
    version = done.stdout.strip()
    if done.returncode != 0 or not version:
        reason = done.stderr.strip() or "the repository has no commit"
        raise ConversionError(f"version: git needs a git repository with a commit at '{folder}': {reason}")
    return version


def status_template(base: Path | None, status: str | None) -> Path | None:
    """``Template_draft.docx`` for ``Template.docx`` and status ``Draft``, when that file exists.

    The status is used as written first, then in lower case. A status without a matching file falls
    back to the base template, and says so.
    """
    if base is None or not status:
        return base
    candidates = dict.fromkeys(
        base.with_name(f"{base.stem}_{name}{base.suffix}") for name in (status.strip(), status.strip().lower())
    )
    for candidate in candidates:
        if candidate.is_file():
            logger.info(f"Using the template for status '{status}': {candidate}")
            return candidate
    logger.info(
        f"No template for status '{status}' (looked for {', '.join(c.name for c in candidates)}), so {base} is used"
    )
    return base


def safe_version(version: str | None) -> str:
    """A version fit for a file name: dots and other separators become underscores, none becomes x_x_x."""
    if not version or not version.strip():
        return "x_x_x"
    return re.sub(r"[^\w-]+", "_", version.strip())


def check_name_pattern(pattern: str, where: str) -> None:
    """Raise ValueError for a pattern with an unknown field or a stray brace."""
    unknown = [field for field in _FIELD.findall(pattern) if field not in FIELDS]
    if unknown:
        raise ValueError(
            f"{where} uses unknown field {{{unknown[0]}}}. Fields: {', '.join('{' + f + '}' for f in FIELDS)}"
        )
    if "{" in _FIELD.sub("", pattern) or "}" in _FIELD.sub("", pattern):
        raise ValueError(f"{where} has a brace that is not part of a field")


def expand_name(pattern: str, name: str, version: str | None) -> str:
    """The file name stem for ``pattern``. ``{version}`` needs a version, ``{version_safe}`` does not."""
    if "{version}" in pattern and not (version and version.strip()):
        raise ConversionError(f"The output name '{pattern}' uses {{version}}, but the document has no version")
    values = {"name": name, "version": (version or "").strip(), "version_safe": safe_version(version)}
    return _FIELD.sub(lambda match: values[match[1]], pattern)
