"""Document metadata read from the YAML front matter at the top of a Markdown file."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

import yaml

from . import nodes as n


class FrontMatterError(Exception):
    """The front matter is not valid YAML, or is not a mapping of keys to values."""


@dataclass
class Metadata:
    """The standard keys, as text. Anything else in the front matter is kept in ``extra``."""

    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None
    version: str | None = None
    status: str | None = None
    document_id: str | None = None
    keywords: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


_ALIASES = {"id": "document_id", "document-id": "document_id", "tags": "keywords"}
_STANDARD = {"title", "subtitle", "author", "date", "version", "status", "document_id", "keywords"}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) or None
    return str(value).strip() or None


def read_metadata(document: n.Document) -> Metadata:
    """The metadata of ``document``, or an empty :class:`Metadata` if it has no front matter.

    Raises :class:`FrontMatterError` for YAML that cannot be read.
    """
    front = document.front_matter
    if front is None:
        return Metadata()
    try:
        data = yaml.safe_load(front.text)
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"Invalid front matter at line {front.line}: {exc}") from exc
    if data is None:
        return Metadata()
    if not isinstance(data, dict):
        raise FrontMatterError(f"Front matter at line {front.line} must be a mapping of keys to values")

    metadata = Metadata()
    for key, value in data.items():
        name = str(key).strip().lower()
        name = _ALIASES.get(name, name)
        if name in _STANDARD:
            setattr(metadata, name, _text(value))
        else:
            metadata.extra[str(key)] = value
    return metadata
