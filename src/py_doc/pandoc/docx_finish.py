"""Finish a Word file written by pandoc: merge it into the template, fill placeholders, tidy the layout."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

from docx import Document

from py_doc.markdown import Metadata

from . import docx_post as post

logger = logging.getLogger(__name__)


def _composer():
    # docxcompose imports pkg_resources, which warns on every import and is gone from setuptools 81.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from docxcompose.composer import Composer
    return Composer


DEFAULT_PREFIX = "Replace-with-"
DEFAULT_MARKER = "[[INSERTCONTENT]]"
_FIELDS = (  # placeholder name, and how the metadata is read
    ("Title", lambda m: m.title),
    ("Author", lambda m: m.author),
    ("Version", lambda m: m.version),
    ("Document-Number", lambda m: m.document_id),
    ("Date", lambda m: m.date),
    ("Description", lambda m: m.extra.get("description")),
    ("Classification", lambda m: m.extra.get("classification")),
)  # fmt: skip


def finish_docx(body_path: Path, template: Path | None, metadata: Metadata, options: dict[str, Any]) -> None:
    """Rewrite ``body_path`` in place. Without a template pandoc's own output is only tidied.

    A template gets its ``Replace-with-*`` placeholders filled (the prefix is the ``placeholder_prefix``
    option) and the body inserted at the marker paragraph (``marker``), or at the end without one.
    """
    extra = metadata.extra
    text = lambda value: str(value) if value else ""  # noqa: E731
    prefix = options.get("placeholder_prefix", DEFAULT_PREFIX)
    if template is not None:
        base = Document(str(template))
        composer = _composer()(base)
        present = post.find_placeholders(base, prefix)
        replacements = {}
        for name, read in _FIELDS:
            value = text(read(metadata))
            replacements[prefix + name] = value
            if not value and prefix + name in present:
                logger.warning(f"The template has {prefix + name}, but the document has no {name.lower().replace('-', ' ')}")
        post.replace_placeholders(base, replacements)
        index = post.find_and_remove_marker(base, options.get("marker", DEFAULT_MARKER))
        body = Document(str(body_path))
        if index is not None:
            composer.insert(index, body)
        else:
            logger.info(f"The template has no {options.get('marker', DEFAULT_MARKER)} line, so the document goes at the end")
            composer.append(body)
        post.mark_for_toc_update(base)
        composer.save(str(body_path))

    document = Document(str(body_path))
    left = post.find_placeholders(document, prefix) if template is not None else set()
    if left:
        logger.warning(f"The document still contains {', '.join(sorted(left))}. No metadata fills them")
    post.clean_trailing_pagebreak(document)
    post.apply_orientation_markers(document)
    post.apply_layout_fixes(document)
    post.rescale_landscape_images(document)
    post.normalize_body_bold(document)
    post.apply_explicit_styles(document)
    post.format_all_tables(document)
    post.update_core_properties(
        document,
        title=text(metadata.title),
        author=text(metadata.author),
        description=text(extra.get("description")),
        version=text(metadata.version),
        document_number=text(metadata.document_id),
        subject=text(extra.get("subject")),
        keywords=text(metadata.keywords),
        category=text(extra.get("category")),
    )
    post.mark_for_toc_update(document)
    document.save(str(body_path))
