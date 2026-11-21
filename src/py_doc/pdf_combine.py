"""Join the PDFs of a project's documents into one, for ``py-doc build --combine``.

Each document becomes a bookmark with its own bookmarks (its headings) below it, so the joined file can be
read like one book. The pages are copied as they are: each document keeps its own title page, contents and
numbering.
"""

from __future__ import annotations

import os
from pathlib import Path


def pdf_title(path: Path) -> str | None:
    """The title a PDF's properties give, as pandoc writes it from the document's title."""
    from pypdf import PdfReader

    try:
        title = (PdfReader(path).metadata or {}).get("/Title")
    except Exception:  # noqa: BLE001 - an unreadable title is only a missing bookmark name
        return None
    return str(title).strip() or None if title else None


def combine(parts: list[tuple[str | None, Path]], output: Path, title: str | None = None) -> int:
    """Write ``output`` from ``parts``, each (bookmark name, PDF). Returns the number of pages.

    A name that is None is taken from the PDF's own title, else its file name.
    """
    from pypdf import PdfWriter

    if not parts:
        raise ValueError("no document was built as a PDF")
    writer = PdfWriter()
    for name, path in parts:
        label = pdf_title(path) or name or path.stem
        writer.append(str(path), outline_item=label, import_outline=True)
    if title:
        writer.add_metadata({"/Title": title})
    writer.page_mode = "/UseOutlines"  # open with the bookmarks showing
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + f".{os.getpid()}.part")
    with open(partial, "wb") as handle:
        writer.write(handle)
    os.replace(partial, output)
    return len(writer.pages)
