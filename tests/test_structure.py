"""Structure rules: the engine, the configuration and the createdocs mapping."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from py_doc.config import ConfigError, load_config
from py_doc.lint import DocLinter
from py_doc.lint.structure import (
    StructureRuleError, anchor, check_document, check_file, load_rules, parse_rules,
)  # fmt: skip

EXAMPLE = Path(__file__).parent.parent / "src" / "py_doc" / "lint" / "examples" / "structure-rules.yaml"


def rules(*entries):
    return parse_rules(list(entries))


def found(text, *entries, name="a.md"):
    return [(i.line, i.rule, i.severity) for i in check_file(Path(name), text, rules(*entries))]


class TestRegexLine:
    RULE = {"id": "r/hr", "type": "regex-line", "severity": "warning", "pattern": r"^---\s*$", "message": "no rules"}

    def test_flags_a_line(self):
        assert found("a\n---\nb\n", self.RULE) == [(2, "r/hr", "warning")]

    def test_code_and_inline_code_are_not_searched(self):
        rule = {**self.RULE, "pattern": r"\[\[X\]\]"}
        assert found("```\n[[X]]\n```\n\nuse `[[X]]` here\n\n[[X]]\n", rule) == [(7, "r/hr", "warning")]

    def test_scope_prefix_and_exclude(self):
        rule = {"id": "r/q", "type": "regex-line", "pattern": r"\*\*Note\*\*", "scope_prefix": ">", "exclude_pattern": "ok"}
        assert found("> **Note** x\n**Note** y\n> **Note** ok\n", rule) == [(1, "r/q", "warning")]

    def test_disabled_rules_do_nothing(self):
        assert found("---\n", {**self.RULE, "enabled": False}) == []


class TestOtherTypes:
    def test_loose_list(self):
        rule = {"id": "r/loose", "type": "blank-line-between", "pattern": r"^\s*[-*]\s+\S", "message": "tight"}
        assert found("- a\n\n- b\n- c\n", rule) == [(2, "r/loose", "warning")]

    def test_broken_link_path_include_and_anchor_skipping(self, tmp_path):
        (tmp_path / "there.md").write_text("x", encoding="utf-8")
        rule = {"id": "r/link", "type": "path-exists", "severity": "error", "pattern": r"\[[^\]]*\]\(([^)\s]+)\)", "message": "{target}"}
        text = "[a](there.md) [b](gone.md#x) [c](https://x.org/a) [d](#top) [e](the%20re.md)\n"
        issues = check_file(tmp_path / "a.md", text, rules(rule))
        assert [i.message for i in issues] == ["gone.md", "the re.md"]

    def test_balanced_markers(self):
        rule = {
            "id": "r/if", "type": "balanced-markers", "severity": "error", "open_pattern": r"\[\[IF:[^\]]*\]\]",
            "close_pattern": r"\[\[ENDIF\]\]", "unmatched_open_message": "open {marker}", "unmatched_close_message": "close",
        }  # fmt: skip
        assert found("[[IF: a]]\n[[ENDIF]]\n[[ENDIF]]\n[[IF: b]]\n", rule) == [(3, "r/if", "error"), (4, "r/if", "error")]

    CAPTION = {"id": "r/cap", "type": "requires-caption", "block": "table", "required_pattern": r"\[\[CAPTION:Table\]\]", "message": "caption"}

    def test_table_needs_a_caption_on_the_next_line(self):
        table = "| a |\n|---|\n| 1 |\n"
        assert found(table + "\n[[CAPTION:Table]] x\n", self.CAPTION) == []
        assert found(table + "\ntext\n", self.CAPTION) == [(3, "r/cap", "warning")]

    def test_a_caption_before_the_block_counts(self):
        image = {**self.CAPTION, "id": "r/img", "block": "image", "required_pattern": r"\[\[CAPTION:Figure\]\]"}
        assert found("[[CAPTION:Figure]] a\n![x](a.png)\n", image) == []
        assert found("[[CAPTION:Table]] a\n| a |\n|---|\n| 1 |\n", self.CAPTION) == []
        assert found("text\n\n![x](a.png)\n", image) == [(3, "r/img", "warning")]

    def test_front_matter_is_not_checked_as_text(self):
        rule = {"id": "r/rule", "type": "regex-line", "severity": "warning", "pattern": r"^---\s*$", "message": "m"}
        assert found("---\ntitle: x\n---\n\ntext\n\n---\n", rule) == [(7, "r/rule", "warning")]

    def test_image_fence_div_and_trigger_captions(self):
        image = {**self.CAPTION, "id": "r/img", "block": "image", "required_pattern": r"\[\[CAPTION:Figure\]\]"}
        fence = {**image, "id": "r/fence", "block": "fence", "div_languages": ["mermaid"]}
        trigger = {**image, "id": "r/inc", "block": "line", "trigger_pattern": r"\[\[INCLUDE-CODE:"}
        text = "![x](a.png)\n\n```python\nx\n```\n\n::: mermaid\ng\n:::\n\n::: {.pagebreak}\n:::\n\n[[INCLUDE-CODE: a.py]]\n"
        assert found(text, image, fence, trigger) == [
            (1, "r/img", "warning"), (5, "r/fence", "warning"), (9, "r/fence", "warning"), (14, "r/inc", "warning")
        ]  # fmt: skip
        ok = "![x](a.png)\n[[CAPTION:Figure]] a\n"
        assert found(ok, image) == []

    def test_a_table_inside_code_is_not_a_table(self):
        assert found("```\n| a |\n```\n", self.CAPTION) == []


class TestAnchors:
    def test_pandoc_identifiers(self):
        assert anchor("Daily Volume Profile (R6029)") == "daily-volume-profile-r6029"
        assert anchor("11000/0 - Daily") == "daily"  # up to the first letter is dropped
        assert anchor("`Code` and *emphasis*") == "code-and-emphasis"
        assert anchor("[Link](x.md) text") == "link-text"
        assert anchor("123") == "section"
        assert anchor("a.b_c-d") == "a.b_c-d"

    @pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is not installed")
    @pytest.mark.parametrize(
        "heading", ["Daily Volume Profile (R6029)", "11000/0 - Daily", "`Code` and *emphasis*", "[Link](x.md) text", "123", "Über uns", "a.b_c-d", "Q&A: what?"]
    )
    def test_agrees_with_pandoc(self, heading):
        html = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html"], input=f"# {heading}\n", capture_output=True, text=True, check=True
        ).stdout
        assert f'id="{anchor(heading)}"' in html

    RULE = {
        "id": "r/anchor", "type": "cross-file-anchors", "severity": "error", "message": "no #{target}",
        "collision_severity": "warning", "collision_message": "{target} also in {other_file}",
    }  # fmt: skip

    def test_links_resolve_across_files_with_pandoc_suffixes(self, tmp_path):
        one = tmp_path / "one.md"
        two = tmp_path / "two.md"
        one.write_text("# Setup\n\nSee [x](#setup-1) and [y](#nowhere).\n", encoding="utf-8")
        two.write_text("# Setup\n\nBack to [z](#setup).\n\n```\n[w](#in-code)\n```\n", encoding="utf-8")
        issues = check_document([one, two], rules(self.RULE))
        assert [(i.file.name, i.line, i.severity) for i in issues] == [("one.md", 3, "error"), ("two.md", 1, "warning")]
        assert "#nowhere" in issues[0].message and "one.md" in issues[1].message

    def test_headings_of_included_files_count(self, tmp_path):
        main = tmp_path / "main.md"
        part = tmp_path / "part.md"
        part.write_text("# Included\n", encoding="utf-8")
        main.write_text("[[INCLUDE: part.md]]\n\n[go](#included)\n", encoding="utf-8")
        assert check_document([main], rules(self.RULE)) == []

    def test_missing_sources(self, tmp_path):
        rule = {"id": "r/missing", "type": "manifest-file-exists", "severity": "error", "message": "gone"}
        issues = check_document([tmp_path / "no.md"], rules(rule))
        assert [(i.file.name, i.rule) for i in issues] == [("no.md", "r/missing")]


class TestConfiguration:
    @pytest.mark.parametrize(
        ("entry", "message"),
        [
            ({"type": "regex-line", "pattern": "x"}, "needs an 'id'"),
            ({"id": "a", "type": "nope"}, "has type 'nope'"),
            ({"id": "a", "type": "regex-line"}, "needs 'pattern'"),
            ({"id": "a", "type": "regex-line", "pattern": "("}, "not a valid regular expression"),
            ({"id": "a", "type": "regex-line", "pattern": "x", "colour": 1}, "unknown key 'colour'"),
            ({"id": "a", "type": "regex-line", "pattern": "x", "severity": "loud"}, "severity must be one of"),
            ({"id": "a", "type": "path-exists", "pattern": "x"}, "needs a group"),
            ({"id": "a", "type": "requires-caption", "block": "box", "required_pattern": "x"}, "block must be one of"),
            ({"id": "a", "type": "requires-caption", "block": "line", "required_pattern": "x"}, "needs 'trigger_pattern'"),
        ],
    )
    def test_mistakes_name_the_rule(self, entry, message):
        with pytest.raises(StructureRuleError, match=message):
            parse_rules([entry])

    def test_a_duplicate_id_is_refused(self):
        entry = {"id": "a", "type": "regex-line", "pattern": "x"}
        with pytest.raises(StructureRuleError, match="defined twice"):
            parse_rules([entry, entry])

    def write(self, tmp_path, body):
        (tmp_path / "a.md").write_text("# A\n\n---\n", encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text(body, encoding="utf-8")
        return tmp_path / "py-doc.yml"

    def test_rules_inline_in_py_doc_yml(self, tmp_path):
        path = self.write(
            tmp_path,
            "lint:\n  structure:\n    - {id: s/hr, type: regex-line, severity: error, pattern: '^---$', message: m}\n"
            "documents:\n  d: {sources: [a.md]}\n",
        )
        config = load_config(path).lint
        assert [r.id for r in config.structure] == ["s/hr"]
        report = DocLinter(config=config).lint_path(tmp_path / "a.md")
        assert [(i.rule, i.severity) for i in report.issues] == [("s/hr", "error")]

    def test_rules_from_a_file_and_errors_are_config_errors(self, tmp_path):
        (tmp_path / "rules.yaml").write_text(yaml.safe_dump({"rules": [{"id": "x", "type": "regex-line", "pattern": "a"}]}), encoding="utf-8")
        assert [r.id for r in load_config(self.write(tmp_path, "lint: {structure: rules.yaml}\n")).lint.structure] == ["x"]
        with pytest.raises(ConfigError, match="not found"):
            load_config(self.write(tmp_path, "lint: {structure: gone.yaml}\n"))
        with pytest.raises(ConfigError, match="has type 'bad'"):
            load_config(self.write(tmp_path, "lint:\n  structure: [{id: x, type: bad}]\n"))

    def test_documents_are_taken_from_the_configuration(self, tmp_path):
        config = load_config(self.write(tmp_path, "documents:\n  d: {sources: [a.md, {file: b.md, include: false}]}\n")).lint
        assert config.documents == {"d": [tmp_path / "a.md"]}


class TestBundleMapping:
    """The structure-rules.yaml of the createdocs bundle loads, minus the rule py-doc replaces."""

    def test_the_example_loads_with_every_rule_type(self):
        loaded = load_rules(EXAMPLE)
        assert {r.type for r in loaded} == {
            "manifest-file-exists", "regex-line", "blank-line-between", "path-exists", "balanced-markers",
            "requires-caption", "cross-file-anchors",
        }  # fmt: skip
        assert "structure/admonition-legacy-format" not in {r.id for r in loaded}

    def test_the_legacy_callout_rule_is_dropped_from_a_createdocs_file(self, tmp_path, caplog):
        import logging

        original = {"rules": [
            {"id": "structure/admonition-legacy-format", "type": "regex-line", "pattern": "x"},
            {"id": "structure/horizontal-rule", "type": "regex-line", "pattern": "^---$"},
        ]}  # fmt: skip
        path = tmp_path / "structure-rules.yaml"
        path.write_text(yaml.safe_dump(original), encoding="utf-8")
        with caplog.at_level(logging.INFO):
            assert [r.id for r in load_rules(path)] == ["structure/horizontal-rule"]
        assert "both callout spellings are accepted" in caplog.text

    def test_sample_project_findings(self, tmp_path):
        """One sample project, one expected list: the same findings the script's rule set would give."""
        (tmp_path / "img.png").write_bytes(b"x")
        a = tmp_path / "a.md"
        a.write_text(
            "# Intro\n\n---\n\n> [!NOTE]\n> fine\n\n> **Note:** also fine\n\n> [!INFO]\n> bad kind\n\n"
            "[[CAPTION:Diagram]] x\n\nValue {{bad name}}\n\n- a\n\n- b\n\n[gone](missing.md) [ok](img.png)\n\n"
            "[[IF: x]]\ntext\n\n![pic](img.png)\n\n| a |\n|---|\n| 1 |\n\n[l](#intro) [m](#nope)\n",
            encoding="utf-8",
        )
        config = load_config_text(tmp_path, "lint: {structure: %s}\ndocuments:\n  d: {sources: [a.md]}\n" % EXAMPLE.as_posix())
        report = DocLinter(config=config).lint_path(a)
        got = sorted({(i.line, i.rule) for i in report.issues if i.rule.startswith("structure/")})
        assert got == [
            (3, "structure/horizontal-rule"),
            (10, "structure/admonition-unsupported-type"),
            (13, "structure/caption-unsupported-kind"),
            (15, "structure/variable-name-format"),
            (18, "structure/loose-list"),
            (21, "structure/broken-link"),
            (23, "structure/if-endif-unbalanced"),
            (26, "structure/image-missing-caption"),
            (30, "structure/table-missing-caption"),
            (32, "structure/cross-file-anchor"),
        ]  # fmt: skip


def load_config_text(tmp_path, body):
    (tmp_path / "py-doc.yml").write_text(body, encoding="utf-8")
    return load_config(tmp_path / "py-doc.yml").lint
