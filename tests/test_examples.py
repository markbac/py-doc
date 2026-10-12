"""The examples folder works: the config loads, the templates pass, the documents build and the Word sample imports."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from docx import Document
from pptx import Presentation

from py_doc.app import main
from py_doc.config import load_config

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
# The host has Graphviz and pandoc, but not the other diagram tools, so those blocks are taken out
NO_TOOLS = re.compile(
    r"```(?:mermaid|plantuml|puml|ditaa|blockdiag|seqdiag|actdiag|nwdiag|packetdiag|wavedrom|bytefield-svg|pikchr|railroad|wireviz|vega-lite|vega)\b[^\n]*\n.*?```\n",
    re.S,
)


def _tex_packages_found() -> bool:
    """xelatex with the packages the PDF template loads (ulem and tcolorbox come with texlive-latex-extra and -plain-generic)."""
    if shutil.which("xelatex") is None or shutil.which("kpsewhich") is None:
        return False
    found = subprocess.run(["kpsewhich", "ulem.sty", "tcolorbox.sty"], capture_output=True, text=True).stdout.split()
    return len(found) == 2


needs_xelatex = pytest.mark.skipif(not _tex_packages_found(), reason="xelatex or one of its packages is not installed")


@pytest.fixture
def examples(tmp_path, monkeypatch):
    """A copy of the examples without the diagrams that need tools the host does not have."""
    target = tmp_path / "examples"
    shutil.copytree(EXAMPLES, target)
    for path in (target / "docs").rglob("*.md"):
        path.write_text(NO_TOOLS.sub("", path.read_text(encoding="utf-8")), encoding="utf-8")
    monkeypatch.chdir(target)
    return target


def test_the_config_loads_and_names_every_part():
    config = load_config(EXAMPLES / "py-doc.yml")
    assert sorted(config.documents) == ["architecture", "datasheet", "deck", "guide"]
    assert config.documents["architecture"].sources[1].structurizr is not None
    assert config.lint.vale.rules["PyDoc.SentenceLength"].options == {"max": 35}
    assert config.lint.structure
    assert config.report is not None


@pytest.mark.parametrize("name", ["sensor.docx", "sensor_Draft.docx", "sensor.pptx"])
def test_the_templates_pass_the_check(name, capsys):
    assert main(["template", "check", str(EXAMPLES / "templates" / name), "--strict"]) == 0


def test_the_draft_template_differs_from_the_base_one(capsys):
    assert main(["template", "diff", str(EXAMPLES / "templates" / "sensor.docx"), str(EXAMPLES / "templates" / "sensor_Draft.docx")]) == 0


def test_the_documents_lint_clean(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLES)
    assert main(["lint", "docs", "--engine", "builtin", "--strict"]) == 0
    assert "0 issue(s) reported" in capsys.readouterr().out


def test_the_model_checks_without_java(examples, capsys):
    assert main(["c4", "check", "architecture/workspace.json", "--strict"]) == 0
    assert "16 element(s), 10 relationship(s), 5 view(s), 0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_the_dsl_and_the_json_describe_the_same_model():
    dsl = (EXAMPLES / "architecture" / "workspace.dsl").read_text(encoding="utf-8")
    from_dsl = set(re.findall(r'=\s*(?:person|softwareSystem|container|component)\s+"([^"]+)"', dsl))
    data = json.loads((EXAMPLES / "architecture" / "workspace.json").read_text(encoding="utf-8"))
    from_json: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            if "name" in node and "tags" in node:
                from_json.add(node["name"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data["model"])
    assert from_dsl == from_json


def test_the_guide_builds_as_word_and_html(examples, pandoc_runtime):
    assert main(["build", "guide", "-f", "docx", "-f", "html", "--condition", "internal=true"]) == 0
    docx = next((examples / "build").glob("*.docx"))
    assert docx.name == "guide-v1.0.docx"
    document = Document(docx)
    text = "\n".join(p.text for p in document.paragraphs)
    assert "Sensor Node Guide" in text and "version 1.0" in text and "internal use" in text
    assert "Customers see only the public build." not in text
    assert [p.text for p in document.paragraphs if p.style.name == "Title"] == ["Sensor Node Guide"], "the title page is not repeated"
    assert any(p.style.name == "Lead Paragraph" and p.text.startswith("The SN-100") for p in document.paragraphs)
    assert "DRAFT" in document.sections[0].header.paragraphs[0].text, "status: Draft chooses sensor_Draft.docx"
    assert "TOC" in document.element.xml, "toc: true adds a contents list"
    assert "[[" not in text, "no marker is left in the text"
    html = (examples / "build" / "guide.html").read_text(encoding="utf-8")
    assert "#0b4f8a" in html, "the stylesheet from templates/doc.css is used"
    assert "<figcaption" in html and "<caption>Node requirements</caption>" in html
    assert "[[" not in html, "no marker is printed in HTML"
    assert 'src="data:image/png' in html and 'src="images/logo.png"' not in html, "the logo is embedded"
    assert "<figcaption>Data flow through the node</figcaption>" in html


def test_the_conditions_choose_the_text(examples, pandoc_runtime):
    assert main(["build", "guide", "-f", "html", "--condition", "audience=staff"]) == 0
    html = (examples / "build" / "guide.html").read_text(encoding="utf-8")
    assert "Staff notes" in html and "Customers see only the public build." in html


@needs_xelatex
def test_the_guide_builds_as_pdf_with_task_lists_and_captions(examples, pandoc_runtime):
    assert main(["build", "guide", "-f", "pdf"]) == 0
    pdf = examples / "build" / "guide.pdf"
    assert pdf.read_bytes().startswith(b"%PDF")
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        assert "[[" not in text, "no marker is printed in the PDF"
        assert "Data flow through the node" in text and "Figure 1" in text


def test_the_datasheet_builds_with_a_version_in_the_name(examples, pandoc_runtime):
    assert main(["build", "datasheet", "-f", "docx"]) == 0
    assert (examples / "build" / "datasheet-1_0.docx").is_file()


def test_the_deck_builds_one_slide_per_second_level_heading(examples, pandoc_runtime):
    assert main(["build", "deck"]) == 0
    slides = Presentation(next((examples / "build").glob("*.pptx"))).slides
    assert len(slides) >= 4
    xml = "".join(slide.part.blob.decode("utf-8") for slide in slides)
    assert "CAPTION" not in xml


def test_the_word_sample_imports_and_builds_again(examples, pandoc_runtime, tmp_path):
    out = tmp_path / "imported"
    assert main(["import", "word/design_review.docx", "-o", str(out)]) == 0
    text = (out / "design_review.md").read_text(encoding="utf-8")
    assert "title: Design review" in text and "- Confirm the sampling interval" in text and "| Sampling interval | Firmware |" in text
    assert "[[CAPTION:Figure]] The agreed layout" in text
    assert main(["docx", str(out / "design_review.md")]) == 0
    with zipfile.ZipFile(out / "design_review.docx") as archive:
        assert any(n.startswith("word/media/") for n in archive.namelist())
