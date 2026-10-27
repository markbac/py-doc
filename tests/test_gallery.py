"""The diagram gallery in docs/gallery: one example of every type, each shown as its Markdown and then drawn."""

from __future__ import annotations

import re
from pathlib import Path

from py_doc.config import load_config
from py_doc.diagrams.registry import BY_FENCE
from py_doc.poster_blocks import BLOCKS

ROOT = Path(__file__).resolve().parent.parent
GALLERY = ROOT / "docs" / "gallery"
CHAPTERS = sorted(GALLERY.glob("[0-9][0-9]_*.md"))[1:]  # after the introduction, which only shows the syntax
# A source block, then the same fence drawn
PAIR = re.compile(r"^````markdown\n(```.*?^```)\n````\n\n(```.*?^```)$", re.M | re.S)
FENCE = re.compile(r"^```([\w-]+)", re.M)
ALIASES = {"graphviz": "dot", "puml": "plantuml", "abc": "music"}


def _drawn() -> list[str]:
    """Every diagram fence the gallery draws, as written."""
    out = []
    for md in CHAPTERS:
        text = md.read_text(encoding="utf-8")
        out += [drawn for _, drawn in PAIR.findall(text)]
    return out


def test_each_example_shows_the_markdown_that_draws_it():
    for md in CHAPTERS:
        text = md.read_text(encoding="utf-8")
        pairs = PAIR.findall(text)
        assert pairs, md.name
        for source, drawn in pairs:
            assert source == drawn, f"{md.name}: the source block and the diagram after it differ:\n{source[:200]}"
        # every diagram is in a pair: none is drawn without its Markdown shown
        outside = PAIR.sub("", text)
        assert not [kind for kind in FENCE.findall(outside) if kind in BY_FENCE or kind in BLOCKS or kind == "plot"], (
            md.name
        )


def test_every_diagram_type_and_block_has_an_example():
    kinds = {FENCE.match(drawn)[1] for drawn in _drawn()}
    wanted = {ALIASES.get(name, name) for name in [*BY_FENCE, *BLOCKS, "plot"]}
    assert wanted <= kinds, f"no example of {sorted(wanted - kinds)}"


def test_every_kind_of_mermaid_diagram_has_an_example():
    first_words = set()
    for drawn in _drawn():
        if drawn.startswith("```mermaid"):
            body = re.sub(r"^---\n.*?\n---\n", "", drawn.split("\n", 1)[1], flags=re.S)
            first_words.add(body.split()[0])
    # the diagram types of Mermaid 12.1, as their first word (C4 has five)
    assert first_words >= {
        "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram-v2", "erDiagram", "journey", "gantt", "pie",
        "quadrantChart", "xychart", "requirementDiagram", "gitGraph", "C4Context", "C4Container", "C4Component",
        "C4Dynamic", "C4Deployment", "mindmap", "timeline", "sankey", "block", "packet", "kanban", "architecture-beta",
        "radar-beta", "treemap-beta", "ishikawa-beta", "venn-beta", "treeView-beta", "usecase-beta", "swimlane-beta",
        "eventmodeling", "wardley-beta", "cynefin-beta", "railroad-beta", "railroad-ebnf-beta", "railroad-abnf-beta",
        "railroad-peg-beta", "agentflow-beta",
    }  # fmt: skip


def test_the_gallery_is_a_document_of_the_project_and_its_site():
    config = load_config(ROOT / "py-doc.yml")
    sources = [Path(s.file).resolve() for s in config.documents["gallery"].sources]
    assert sources == [md.resolve() for md in sorted(GALLERY.glob("[0-9][0-9]_*.md"))]
    assert "gallery" in config.site.documents
