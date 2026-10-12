"""The examples folder works: the config loads, the templates pass, the documents build and the Word sample imports."""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import pytest
from docx import Document
from pptx import Presentation

from py_doc.app import main
from py_doc.config import load_config

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
NO_BROWSER = re.compile(r"```(?:mermaid|plantuml)\n.*?```\n", re.S)


@pytest.fixture
def examples(tmp_path, monkeypatch):
    """A copy of the examples. The host has neither Mermaid nor PlantUML, so those two blocks are taken out."""
    target = tmp_path / "examples"
    shutil.copytree(EXAMPLES, target)
    design = target / "docs" / "02_design.md"
    design.write_text(NO_BROWSER.sub("", design.read_text(encoding="utf-8")), encoding="utf-8")
    monkeypatch.chdir(target)
    return target


def test_the_config_loads_and_names_every_part():
    config = load_config(EXAMPLES / "py-doc.yml")
    assert sorted(config.documents) == ["architecture", "deck", "guide"]
    assert config.documents["architecture"].sources[1].structurizr is not None
    assert config.lint.vale.rules["PyDoc.SentenceLength"].options == {"max": 35}
    assert config.lint.structure


@pytest.mark.parametrize("name", ["company.docx", "company.pptx"])
def test_the_templates_pass_the_check(name, capsys):
    assert main(["template", "check", str(EXAMPLES / "templates" / name), "--strict"]) == 0


def test_the_documents_lint_clean(examples, capsys):
    assert main(["lint", "docs", "--engine", "builtin", "--strict"]) == 0


def test_the_model_checks_without_java(examples, capsys):
    assert main(["c4", "check", "architecture/workspace.json"]) == 0
    assert "11 element(s), 5 relationship(s), 5 view(s), 0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_the_guide_builds_as_word_and_html(examples, pandoc_runtime):
    assert main(["build", "guide", "-f", "docx", "-f", "html", "--condition", "internal=true"]) == 0
    docx = next((examples / "build").glob("*.docx"))
    assert docx.name == "guide-v1.0.docx"
    text = "\n".join(p.text for p in Document(docx).paragraphs)
    assert "Meter Gateway Guide" in text and "version 1.0" in text and "internal use" in text
    assert "Customers see only the public build." not in text
    titles = [p.text for p in Document(docx).paragraphs if p.style.name == "Title"]
    assert titles == ["Meter Gateway Guide"], "the template's title page is not repeated by pandoc's title block"
    html = (examples / "build" / "guide.html").read_text(encoding="utf-8")
    assert "Requirements" in html and "<svg" in html or "<img" in html


def test_the_conditions_choose_the_text(examples, pandoc_runtime):
    assert main(["build", "guide", "-f", "html", "--condition", "audience=staff"]) == 0
    html = (examples / "build" / "guide.html").read_text(encoding="utf-8")
    assert "Staff notes" in html and "Customers see only the public build." in html


def test_the_deck_builds_one_slide_per_second_level_heading(examples, pandoc_runtime):
    assert main(["build", "deck"]) == 0
    slides = Presentation(next((examples / "build").glob("*.pptx"))).slides
    assert len(slides) >= 4


def test_the_word_sample_imports_and_builds_again(examples, pandoc_runtime, tmp_path):
    out = tmp_path / "imported"
    assert main(["import", "word/design_meeting.docx", "-o", str(out)]) == 0
    text = (out / "design_meeting.md").read_text(encoding="utf-8")
    assert "title: Design meeting" in text and "- Confirm the buffer size" in text and "| Buffer size | Firmware |" in text
    assert "[[CAPTION:Figure]] The agreed layout" in text
    assert main(["docx", str(out / "design_meeting.md")]) == 0
    with zipfile.ZipFile(out / "design_meeting.docx") as archive:
        assert any(n.startswith("word/media/") for n in archive.namelist())
