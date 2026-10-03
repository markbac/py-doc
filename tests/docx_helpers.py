"""Helpers for inspecting generated DOCX files semantically."""

from __future__ import annotations

from pathlib import Path

from docx import Document


def outline(docx_path: Path) -> list[dict]:
    """Return a stable, comparable description of the body paragraphs."""
    items = []
    for p in Document(str(docx_path)).paragraphs:
        runs = p.runs
        items.append(
            {
                "style": p.style.name,
                "text": p.text,
                "font": runs[0].font.name if runs else None,
                "size_pt": runs[0].font.size.pt if runs and runs[0].font.size else None,
                "left_indent_in": (
                    round(p.paragraph_format.left_indent.inches, 2)
                    if p.paragraph_format.left_indent is not None
                    else None
                ),
            }
        )
    return items


def texts(docx_path: Path) -> list[str]:
    return [i["text"] for i in outline(docx_path)]


def styles(docx_path: Path) -> list[str]:
    return [i["style"] for i in outline(docx_path)]
