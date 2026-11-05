"""The VS Code extension highlights every fence py-doc draws: its grammar lists them all."""

from __future__ import annotations

import json
import re
from pathlib import Path

from py_doc.diagrams.registry import RENDERERS
from py_doc.poster_blocks import BLOCKS

SYNTAXES = Path(__file__).parent.parent / "editors" / "vscode" / "syntaxes"


def fences_in_grammar() -> set[str]:
    grammar = json.loads((SYNTAXES / "pydoc-fences.markdown.tmLanguage.json").read_text(encoding="utf-8"))
    names: set[str] = set()
    for rule in grammar["repository"].values():
        if "begin" in rule:
            names |= set(re.search(r"\(\?i:\((.*?)\)\(", rule["begin"])[1].replace("\\-", "-").split("|"))
    return names | {"bpmnt"}  # bpmn-text has its own grammar, bpmnt.markdown.tmLanguage.json


def test_every_diagram_fence_and_poster_block_is_highlighted():
    drawn = {fence for renderer in RENDERERS for fence in renderer.fences} | set(BLOCKS) | {"plot"}
    assert drawn - fences_in_grammar() == set()


def test_the_grammar_names_no_fence_py_doc_does_not_draw():
    drawn = {fence for renderer in RENDERERS for fence in renderer.fences} | set(BLOCKS) | {"plot"}
    assert fences_in_grammar() - drawn == set()
