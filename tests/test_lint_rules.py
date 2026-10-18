"""Tests for the structure, link and limit rules (DOC005 to DOC009) and the acronym options."""

from __future__ import annotations

from py_doc.config import load_config
from py_doc.lint import DocLinter, LintConfig


def rules(text: str, file=None, config: LintConfig | None = None) -> list[tuple[int, str]]:
    found = DocLinter(config=config or LintConfig()).lint_text(text, file or "<text>")
    return [(i.line, i.rule) for i in found if i.rule >= "DOC005"]


class TestHeadingJumps:
    def test_a_skipped_level_is_reported(self):
        assert rules("# A\n\n### C\n\n## B\n\n#### D\n") == [(3, "DOC005"), (7, "DOC005")]

    def test_going_back_up_any_number_of_levels_is_fine(self):
        assert rules("## A\n\n### B\n\n#### C\n\n## D\n") == []


class TestLinks:
    def test_missing_files_and_pictures_are_reported(self, tmp_path):
        (tmp_path / "there.md").write_text("# There\n", encoding="utf-8")
        page = tmp_path / "page.md"
        text = "[ok](there.md#a) [gone](gone.md) ![pic](media/x.png)\n\n[web](https://x.org) [top](#a) [v]({{url}})\n"
        page.write_text(text, encoding="utf-8")
        found = DocLinter().lint_text(text, page)
        assert [i.message for i in found if i.rule == "DOC006"] == [
            "Link target 'gone.md' is not found.",
            "Picture target 'media/x.png' is not found.",
        ]

    def test_text_not_from_a_file_is_not_checked(self):
        assert [r for r in rules("[gone](gone.md)\n") if r[1] == "DOC006"] == []

    def test_a_picture_without_alt_text(self):
        assert [r for r in rules("![](a.png) ![A chart](b.png)\n") if r[1] == "DOC007"] == [(1, "DOC007")]


class TestLimits:
    def test_long_sentences_and_headings(self):
        config = LintConfig(sentence_words=5, heading_length=10)
        text = "# A rather long heading\n\nOne two three four. One two three four five six.\n"
        assert rules(text, config=config) == [(1, "DOC009"), (3, "DOC008")]

    def test_the_limits_come_from_py_doc_yml(self, tmp_path):
        (tmp_path / "py-doc.yml").write_text("lint:\n  limits: {sentence_words: 12, heading_length: 30}\n", encoding="utf-8")
        lint = load_config(tmp_path / "py-doc.yml").lint
        assert (lint.sentence_words, lint.heading_length) == (12, 30)

    def test_a_rule_can_be_turned_off(self):
        config = LintConfig(sentence_words=1, disabled_rules=frozenset({"DOC008"}))
        assert rules("One two three.\n", config=config) == []


class TestAcronymOptions:
    def acronyms(self, text: str, config: LintConfig) -> list[str]:
        return [i.message for i in DocLinter(config=config).lint_text(text) if i.rule == "DOC003"]

    def test_require_definition_off_reports_only_a_use_before_a_later_definition(self):
        config = LintConfig(acronym_require_definition=False)
        text = "The XYZ is used. Use ABC early. Later: Alpha Beta Charlie (ABC).\n"
        assert self.acronyms(text, config) == ["Acronym 'ABC' is used before it is defined on line 1."]

    def test_the_suggestion_is_configurable(self):
        config = LintConfig(acronym_suggestion="Add {acronym} to the glossary")
        found = DocLinter(config=config).lint_text("The XYZ is new.\n")
        assert [i.suggestion for i in found if i.rule == "DOC003"] == ["Add XYZ to the glossary"]

    def test_document_scope_counts_a_definition_in_an_earlier_file(self, tmp_path):
        (tmp_path / "a.md").write_text("# A\n\nThe Message Queue Broker (MQB) starts.\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B\n\nThe MQB stops. The QRS too.\n", encoding="utf-8")
        (tmp_path / "py-doc.yml").write_text(
            "documents:\n  guide: {sources: [a.md, b.md]}\nlint:\n  acronyms: {scope: document}\n", encoding="utf-8"
        )
        config = load_config(tmp_path / "py-doc.yml")
        report = DocLinter(config=config.lint, engine="builtin").lint_paths([tmp_path])
        assert [(i.file.name, i.message) for i in report.issues if i.rule == "DOC003"] == [
            ("b.md", "Acronym 'QRS' is used without being defined.")
        ]
        config.lint.acronym_scope = "file"
        report = DocLinter(config=config.lint, engine="builtin").lint_paths([tmp_path])
        assert sorted(i.message for i in report.issues if i.rule == "DOC003") == [
            "Acronym 'MQB' is used without being defined.",
            "Acronym 'QRS' is used without being defined.",
        ]

    def test_the_options_come_from_py_doc_yml(self, tmp_path):
        (tmp_path / "py-doc.yml").write_text(
            "lint:\n  acronyms: {require_definition: false, scope: document, suggestion: Spell it out}\n", encoding="utf-8"
        )
        lint = load_config(tmp_path / "py-doc.yml").lint
        assert (lint.acronym_require_definition, lint.acronym_scope, lint.acronym_suggestion) == (False, "document", "Spell it out")
