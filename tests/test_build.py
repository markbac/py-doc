"""Building documents from py-doc.yml: joining sources, offsets, titles, page breaks and outputs."""

from __future__ import annotations

import pytest
from docx import Document
from docx.oxml.ns import qn
from docx_helpers import outline, texts
from py_doc.build import build_document, merge_document
from py_doc.config import load_config
from py_doc.errors import ConversionError
from py_doc.markdown import nodes as n
from pptx_helpers import titles


@pytest.fixture
def project(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("---\ntitle: From front matter\nauthor: Ann\n---\n# Intro\n\nHello.\n", encoding="utf-8")
    (tmp_path / "docs" / "part.md").write_text("# Part\n\n## Detail\n\ntext\n", encoding="utf-8")

    def make(yaml_text: str):
        (tmp_path / "py-doc.yml").write_text(yaml_text, encoding="utf-8")
        return load_config(tmp_path / "py-doc.yml")

    return make


def page_breaks(path) -> int:
    return sum(
        1 for br in Document(str(path)).element.body.iter(qn("w:br")) if br.get(qn("w:type")) == "page"
    )


def test_sources_are_joined_in_order_with_a_page_break_before_marked_ones(project, tmp_path):
    config = project("documents:\n  g:\n    sources:\n      - docs/index.md\n      - {file: docs/part.md, page_break: true}\n")
    [out] = build_document(config, config.documents["g"])
    assert out == tmp_path / "build" / "g.docx"
    assert texts(out) == ["Intro", "Hello.", "", "Part", "Detail", "text"]
    assert [i["text"] for i in outline(out) if i["style"].startswith("Heading")] == ["Intro", "Part", "Detail"]
    assert page_breaks(out) == 1


def test_page_break_on_the_first_source_adds_nothing(project):
    config = project("documents:\n  g:\n    sources:\n      - {file: docs/index.md, page_break: true}\n")
    [out] = build_document(config, config.documents["g"])
    assert page_breaks(out) == 0


def test_heading_offset_shifts_levels_and_clamps_with_a_warning(project, caplog):
    config = project("documents:\n  g:\n    sources:\n      - {file: docs/part.md, heading_offset: 5}\n")
    merged = merge_document(config.documents["g"])
    assert [b.level for b in merged.document.children if isinstance(b, n.Heading)] == [6, 6]
    assert "would be level 7" in caplog.text


def test_negative_offset_cannot_go_above_level_one(project, caplog):
    config = project("documents:\n  g:\n    sources:\n      - {file: docs/part.md, heading_offset: -1}\n")
    merged = merge_document(config.documents["g"])
    assert [b.level for b in merged.document.children if isinstance(b, n.Heading)] == [1, 1]
    assert "would be level 0" in caplog.text


def test_title_replaces_the_first_heading_or_adds_one(project, tmp_path):
    (tmp_path / "docs" / "bare.md").write_text("Just text.\n", encoding="utf-8")
    config = project(
        "documents:\n  g:\n    sources:\n"
        "      - {file: docs/part.md, title: Renamed}\n"
        "      - {file: docs/bare.md, title: Added, heading_offset: 1}\n"
    )
    merged = merge_document(config.documents["g"])
    headings = [(b.level, n.plain_text(b.children)) for b in merged.document.children if isinstance(b, n.Heading)]
    assert headings == [(1, "Renamed"), (2, "Detail"), (2, "Added")]


def test_excluded_sources_are_skipped_and_all_excluded_is_an_error(project):
    config = project("documents:\n  g:\n    sources:\n      - docs/index.md\n      - {file: docs/missing.md, include: false}\n")
    merge_document(config.documents["g"])
    config = project("documents:\n  g:\n    sources:\n      - {file: docs/index.md, include: false}\n")
    with pytest.raises(ConversionError, match="no sources"):
        merge_document(config.documents["g"])


def test_missing_source_names_the_document(project):
    config = project("documents:\n  g:\n    sources: [docs/nope.md]\n")
    with pytest.raises(FileNotFoundError, match="document 'g' not found"):
        merge_document(config.documents["g"])


def test_front_matter_is_dropped_but_the_first_files_properties_are_used(project):
    config = project("documents:\n  g:\n    version: '2'\n    sources: [docs/index.md, docs/part.md]\n")
    metadata = merge_document(config.documents["g"]).metadata
    assert (metadata.title, metadata.author, metadata.version) == ("From front matter", "Ann", "2")


def test_configuration_overrides_front_matter(project):
    config = project("documents:\n  g:\n    title: Configured\n    sources: [docs/index.md]\n")
    [out] = build_document(config, config.documents["g"])
    props = Document(str(out)).core_properties
    assert (props.title, props.author) == ("Configured", "Ann")


def test_title_falls_back_to_first_heading_then_document_id(project):
    config = project("documents:\n  g:\n    sources: [docs/part.md]\n")
    assert merge_document(config.documents["g"]).metadata.title == "Part"


def test_images_resolve_against_their_own_source_folder(project, tmp_path):
    from PIL import Image

    (tmp_path / "docs" / "sub").mkdir()
    Image.new("RGB", (4, 4)).save(tmp_path / "docs" / "sub" / "pic.png")
    (tmp_path / "docs" / "sub" / "doc.md").write_text("![pic](pic.png)\n", encoding="utf-8")
    config = project("documents:\n  g:\n    sources: [docs/index.md, docs/sub/doc.md]\n")
    [out] = build_document(config, config.documents["g"])
    assert len(Document(str(out)).inline_shapes) == 1


def test_formats_listed_by_the_document_are_all_built(project, tmp_path):
    config = project("documents:\n  g:\n    sources: [docs/index.md, docs/part.md]\n    outputs: {docx: {}, pptx: {path: deck/g.pptx}}\n")
    written = build_document(config, config.documents["g"])
    assert [p.name for p in written] == ["g.docx", "g.pptx"]
    assert titles(tmp_path / "deck" / "g.pptx")[0] == "Intro"


def test_formats_can_be_chosen_at_build_time(project, tmp_path):
    config = project("documents:\n  g:\n    sources: [docs/index.md]\n    outputs: {docx: {}}\n")
    [out] = build_document(config, config.documents["g"], ["pptx"])
    assert out == tmp_path / "build" / "g.pptx"


def test_template_and_options_from_defaults_with_document_override(project, tmp_path):
    template = tmp_path / "t.docx"
    doc = Document()
    doc.add_paragraph("boilerplate")
    doc.save(str(template))
    config = project(
        "outputs:\n  docx: {template: t.docx, keep_template_body: true}\n"
        "documents:\n  a:\n    sources: [docs/part.md]\n"
        "  b:\n    sources: [docs/part.md]\n    outputs: {docx: {keep_template_body: false}}\n"
    )
    [a] = build_document(config, config.documents["a"])
    [b] = build_document(config, config.documents["b"])
    assert texts(a)[0] == "boilerplate"
    assert "boilerplate" not in texts(b)


def test_page_break_starts_a_new_slide(project, tmp_path):
    (tmp_path / "docs" / "bare.md").write_text("Just text.\n", encoding="utf-8")
    counts = []
    for flag in ("false", "true"):
        config = project(
            "documents:\n  g:\n    sources:\n      - docs/part.md\n"
            f"      - {{file: docs/bare.md, page_break: {flag}}}\n"
        )
        [out] = build_document(config, config.documents["g"], ["pptx"])
        counts.append(titles(out))
    assert counts == [["Part", "Detail"], ["Part", "Detail", "Slide 3"]]
