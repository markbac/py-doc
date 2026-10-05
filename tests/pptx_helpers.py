"""Helpers for inspecting generated PPTX files semantically."""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER, MSO_SHAPE_TYPE

_TITLES = (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)


def slides_of(path: Path):
    return list(Presentation(str(path)).slides)


def title_of(slide) -> str | None:
    for shape in slide.placeholders:
        if shape.placeholder_format.type in _TITLES:
            return shape.text_frame.text
    return None


def body_of(slide) -> list[tuple[int, str]]:
    """(level, text) of every paragraph in the slide's non-title, non-table text."""
    items = []
    for shape in slide.placeholders:
        if shape.placeholder_format.type in _TITLES or not shape.has_text_frame:
            continue
        items += [(p.level, p.text) for p in shape.text_frame.paragraphs]
    return items


def body_texts(slide) -> list[str]:
    return [text for _, text in body_of(slide)]


def titles(path: Path) -> list[str | None]:
    return [title_of(slide) for slide in slides_of(path)]


def notes_of(slide) -> str | None:
    return slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else None


def tables_of(slide) -> list[list[list[str]]]:
    result = []
    for shape in slide.shapes:
        if shape.has_table:
            result.append([[cell.text for cell in row.cells] for row in shape.table.rows])
    return result


def pictures_of(slide):
    return [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]


def runs_of(slide):
    """Every run in the slide, including table cells."""
    runs = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                runs += paragraph.runs
        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    for paragraph in cell.text_frame.paragraphs:
                        runs += paragraph.runs
    return runs


def all_text(path: Path) -> str:
    """Everything a viewer could read or follow: slides, tables, notes and link addresses."""
    parts = []
    for slide in slides_of(path):
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
        parts += [cell for table in tables_of(slide) for row in table for cell in row]
        parts += [run.hyperlink.address for run in runs_of(slide) if run.hyperlink.address]
        if slide.has_notes_slide:
            parts.append(slide.notes_slide.notes_text_frame.text)
    return "\n".join(parts)
