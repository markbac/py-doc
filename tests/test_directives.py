"""Includes, conditions and variables: applied outside code, loud about mistakes."""

from __future__ import annotations

import logging

import pytest
from py_doc import directives
from py_doc.pandoc.source import join_sources
from py_doc.config import load_config
from py_doc.directives import DirectiveError, expand
from py_doc.errors import ConversionError
from py_doc.lint.linter import DocLinter


def doc(tmp_path, text, files=None):
    for name, content in (files or {}).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    main = tmp_path / "main.md"
    main.write_text(text, encoding="utf-8")
    return main


def run(tmp_path, text, variables=None, conditions=None, files=None):
    main = doc(tmp_path, text, files)
    return expand(main.read_text(encoding="utf-8"), main, variables, conditions)


def test_text_without_directives_is_unchanged(tmp_path):
    text = "# Title\n\nSome text.\n"
    assert run(tmp_path, text) == text


class TestVariables:
    def test_replaced_in_text(self, tmp_path):
        assert run(tmp_path, "Version {{ v }} of {{name}}.\n", {"v": 2, "name": "X"}) == "Version 2 of X.\n"

    def test_left_alone_in_code(self, tmp_path):
        text = "Use `{{v}}` here.\n\n```\n{{v}}\n```\n\n~~~\n{{v}}\n~~~\n"
        assert run(tmp_path, text, {"v": "1"}) == text

    def test_text_around_an_inline_code_span_is_still_replaced(self, tmp_path):
        assert run(tmp_path, "{{v}} `{{v}}` {{v}}\n", {"v": "1"}) == "1 `{{v}}` 1\n"

    def test_undefined_is_kept_and_warned_about(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING):
            assert run(tmp_path, "a {{nope}} b\n") == "a {{nope}} b\n"
        assert "main.md:1: variable 'nope' is not defined" in caplog.text


class TestConditions:
    @pytest.mark.parametrize(
        ("block", "conditions", "kept"),
        [
            ("[[IF: a]]", {"a": True}, True),
            ("[[IF: a]]", {"a": False}, False),
            ("[[IF: a]]", {"a": "false"}, False),
            ("[[NOT: a]]", {"a": False}, True),
            ("[[IF: a == b]]", {"a": "b"}, True),
            ("[[IF: a == 'b c']]", {"a": "b c"}, True),
            ("[[IF: a != b]]", {"a": "b"}, False),
            ("[[IF: n == 3]]", {"n": 3}, True),
        ],
    )
    def test_evaluation(self, tmp_path, block, conditions, kept):
        out = run(tmp_path, f"x\n{block}\ninside\n[[ENDIF]]\ny\n", conditions=conditions)
        assert out == ("x\ninside\ny\n" if kept else "x\ny\n")

    def test_nested(self, tmp_path):
        text = "[[IF: a]]\n1\n[[IF: b]]\n2\n[[ENDIF]]\n3\n[[ENDIF]]\n"
        assert run(tmp_path, text, conditions={"a": True, "b": False}) == "1\n3\n"
        assert run(tmp_path, text, conditions={"a": False, "b": True}) == ""

    def test_directives_in_dropped_blocks_are_not_followed(self, tmp_path):
        text = "[[IF: a]]\n[[INCLUDE: missing.md]]\n{{x}}\n[[ENDIF]]\n"
        assert run(tmp_path, text, conditions={"a": False}) == ""

    def test_endif_inside_a_code_block_is_not_one(self, tmp_path):
        text = "[[IF: a]]\n```\n[[ENDIF]]\n```\n[[ENDIF]]\n"
        assert run(tmp_path, text, conditions={"a": True}) == "```\n[[ENDIF]]\n```\n"

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("[[IF: nope]]\n[[ENDIF]]\n", r"main.md:1: condition 'nope' is not defined"),
            ("[[ENDIF]]\n", r"main.md:1: \[\[ENDIF\]\] has no"),
            ("a\n[[IF: a]]\nb\n", r"main.md:2: \[\[IF:\]\] or \[\[NOT:\]\] is never closed"),
        ],
    )
    def test_mistakes_are_errors(self, tmp_path, text, message):
        with pytest.raises(DirectiveError, match=message):
            run(tmp_path, text, conditions={"a": True})

    def test_an_unclosed_block_in_an_include_does_not_swallow_the_parent(self, tmp_path):
        with pytest.raises(DirectiveError, match=r"part.md:1: .*never closed"):
            run(tmp_path, "[[INCLUDE: part.md]]\n[[ENDIF]]\n", conditions={"a": True}, files={"part.md": "[[IF: a]]\n"})


class TestPageBreak:
    def test_becomes_a_page_break_block(self, tmp_path):
        assert run(tmp_path, "a\n[[PAGEBREAK]]\nb\n") == "a\n\n::: {.pagebreak}\n:::\n\nb\n"

    def test_left_alone_in_code(self, tmp_path):
        text = "```\n[[PAGEBREAK]]\n```\n"
        assert run(tmp_path, text) == text


class TestIncludes:
    def test_file_is_inserted_and_expanded(self, tmp_path):
        out = run(tmp_path, "a\n[[INCLUDE: part.md]]\nb\n", {"v": "1"}, files={"part.md": "part {{v}}\n"})
        assert out == "a\npart 1\nb\n"

    def test_paths_start_at_the_including_file(self, tmp_path):
        files = {"sub/one.md": "[[INCLUDE: two.md]]\n", "sub/two.md": "deep\n"}
        assert run(tmp_path, "[[INCLUDE: sub/one.md]]\n", files=files) == "deep\n"

    def test_missing_file_is_an_error_naming_the_line(self, tmp_path):
        with pytest.raises(DirectiveError, match=r"main.md:2: included file not found: .*gone.md"):
            run(tmp_path, "a\n[[INCLUDE: gone.md]]\n")

    def test_circular_include_is_an_error(self, tmp_path):
        with pytest.raises(DirectiveError, match="a.md includes itself"):
            run(tmp_path, "[[INCLUDE: a.md]]\n", files={"a.md": "[[INCLUDE: b.md]]\n", "b.md": "[[INCLUDE: a.md]]\n"})

    def test_the_same_file_twice_is_not_circular(self, tmp_path):
        assert run(tmp_path, "[[INCLUDE: p.md]]\n[[INCLUDE: p.md]]\n", files={"p.md": "x\n"}) == "x\nx\n"

    def test_include_inside_a_code_block_is_shown_not_followed(self, tmp_path):
        text = "```markdown\n[[INCLUDE: gone.md]]\n```\n"
        assert run(tmp_path, text) == text

    def test_code_include_is_verbatim_and_not_expanded(self, tmp_path):
        out = run(tmp_path, "[[INCLUDE-CODE: s.py]]\n", {"v": "1"}, files={"s.py": "x = '{{v}}'\n[[IF: a]]\n"})
        assert out == "```python\nx = '{{v}}'\n[[IF: a]]\n```\n"

    def test_code_include_fence_outgrows_backticks_in_the_file(self, tmp_path):
        out = run(tmp_path, "[[INCLUDE-CODE: n.md]]\n", files={"n.md": "```\ninner\n```\n"})
        assert out.splitlines()[0] == "````markdown" and out.splitlines()[-1] == "````"

    def test_depth_limit(self, tmp_path):
        files = {f"f{i}.md": f"[[INCLUDE: f{i + 1}.md]]\n" for i in range(directives.MAX_DEPTH + 2)}
        files[f"f{directives.MAX_DEPTH + 2}.md"] = "end\n"
        with pytest.raises(DirectiveError, match="nested more than"):
            run(tmp_path, "[[INCLUDE: f0.md]]\n", files=files)


def test_errors_are_conversion_errors():
    assert issubclass(DirectiveError, ConversionError)


class TestBuild:
    def config(self, tmp_path, extra=""):
        (tmp_path / "py-doc.yml").write_text(
            "documents:\n  g:\n    sources: [main.md]\n    variables: {v: from-file}\n    conditions: {a: true}\n"
            + extra,
            encoding="utf-8",
        )
        return load_config(tmp_path / "py-doc.yml").documents["g"]

    def merge_document(self, doc, variables=None, conditions=None):
        return join_sources(
            doc.sources, {**doc.variables, **(variables or {})}, {**doc.conditions, **(conditions or {})}, doc.id
        )

    def text_of(self, joined):
        return " ".join(line for line in joined.markdown.splitlines() if line and not line.startswith("#"))

    def test_configured_values_are_applied(self, tmp_path):
        doc(tmp_path, "# T\n\n[[IF: a]]\nshown {{v}}\n[[ENDIF]]\n")
        assert self.text_of(self.merge_document(self.config(tmp_path))) == "shown from-file"

    def test_overrides_win(self, tmp_path):
        doc(tmp_path, "# T\n\n[[IF: a]]\nshown {{v}}\n[[ENDIF]]\n\nother\n")
        merged = self.merge_document(self.config(tmp_path), {"v": "cli"}, {"a": False})
        assert self.text_of(merged) == "other"

    def test_a_directive_error_stops_the_build(self, tmp_path):
        doc(tmp_path, "[[INCLUDE: gone.md]]\n")
        with pytest.raises(ConversionError, match="included file not found"):
            self.merge_document(self.config(tmp_path))


class TestLint:
    def issues(self, tmp_path, text):
        return [(i.line, i.rule, i.severity) for i in DocLinter().lint_text(text, tmp_path / "main.md")]

    def test_unbalanced_blocks_are_reported(self, tmp_path):
        assert (3, "DOC004", "error") in self.issues(tmp_path, "# T\n\n[[ENDIF]]\n")
        assert (3, "DOC004", "error") in self.issues(tmp_path, "# T\n\n[[IF: a]]\ntext\n")

    def test_missing_include_is_reported(self, tmp_path):
        assert (3, "DOC004", "error") in self.issues(tmp_path, "# T\n\n[[INCLUDE: gone.md]]\n")

    def test_a_valid_document_and_code_examples_are_clean(self, tmp_path):
        (tmp_path / "p.md").write_text("x\n", encoding="utf-8")
        text = "# T\n\n[[INCLUDE: p.md]]\n\n[[IF: a]]\nok\n[[ENDIF]]\n\n```\n[[ENDIF]]\n```\n"
        assert not [i for i in self.issues(tmp_path, text) if i[1] == "DOC004"]
