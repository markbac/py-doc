"""Tests for the documentation linter: exact issue lists, not counts."""

from __future__ import annotations

from pathlib import Path

import pytest
from py_doc.lint import DocLinter, LintConfig
from py_doc.lint.rules import _definitions

FIXTURES = Path(__file__).parent / "fixtures"


def lint(text: str, **kwargs):
    return DocLinter(**kwargs).lint_text(text)


def where(text: str, **kwargs) -> list[tuple[int, str]]:
    """(line, rule) of every issue."""
    return [(i.line, i.rule) for i in lint(text, **kwargs)]


class TestGlossary:
    def test_reports_each_wrongly_written_term_with_its_line(self):
        issues = lint("We use lwm2m over dtls for communications.\n")
        assert [(i.line, i.rule, i.category) for i in issues] == [(1, "DOC001", "Glossary")] * 2
        assert [i.message for i in issues] == [
            "Incorrect term capitalization 'lwm2m'. Preferred: 'LwM2M'.",
            "Incorrect term capitalization 'dtls'. Preferred: 'DTLS'.",
        ]
        assert {i.suggestion for i in issues} == {"LwM2M", "DTLS"}

    def test_correct_spelling_is_clean(self):
        assert lint("LwM2M runs over DTLS with MQTT, IPv6, JSON, YAML, HTTP, HTTPS, UART and an API.\n") == []

    def test_any_capitalisation_is_reported_not_only_listed_variants(self):
        issues = lint("The mQTT broker and mqTT client.\n")
        assert [i.message for i in issues] == [
            "Incorrect term capitalization 'mQTT'. Preferred: 'MQTT'.",
            "Incorrect term capitalization 'mqTT'. Preferred: 'MQTT'.",
        ]

    def test_listed_misspellings_that_differ_by_more_than_case_are_reported(self):
        (issue,) = lint("Support for Lw2m is planned.\n")
        assert issue.message == "Incorrect term 'Lw2m'. Preferred: 'LwM2M'."

    @pytest.mark.parametrize("text", ["The apiary is busy.", "Use jsonify here.", "call my_api now", "https_proxy"])
    def test_a_term_inside_a_longer_word_is_not_reported(self, text):
        assert lint(text + "\n") == []

    def test_every_occurrence_on_a_line_is_reported(self):
        assert where("json and json and JSON and json\n") == [(1, "DOC001")] * 3

    def test_headings_lists_quotes_and_tables_are_checked_on_their_own_lines(self):
        text = "# The dtls guide\n\n- one\n- uart item\n\n> quoted mqtt\n\n| a |\n| - |\n| yaml |\n"
        assert where(text) == [(1, "DOC001"), (4, "DOC001"), (6, "DOC001"), (10, "DOC001")]

    def test_link_text_is_checked_but_not_its_destination(self):
        assert where("[the json guide](https://example.com/json.html)\n") == [(1, "DOC001")]

    def test_custom_glossary_replaces_the_default_one(self):
        linter = DocLinter(glossary={"CoAP": ["coap"]})
        assert [i.message for i in linter.lint_text("coap and lwm2m\n")] == [
            "Incorrect term capitalization 'coap'. Preferred: 'CoAP'."
        ]


class TestCodeAndMarkupAreNotProse:
    def test_fenced_code_is_skipped(self):
        assert lint("```python\nimport json\nresp = api.get()\n```\n") == []

    def test_tilde_and_nested_fences_are_skipped(self):
        assert lint("~~~\njson\n~~~\n\n````\n```\napi\n```\n````\n") == []

    def test_indented_code_is_skipped(self):
        assert lint("Text.\n\n    import json\n") == []

    def test_text_after_a_fence_is_checked_again(self):
        assert where("```\njson\n```\n\nBut json here\n") == [(5, "DOC001")]

    def test_inline_code_is_skipped(self):
        assert lint("Call `api` and `json.loads` here.\n") == []

    def test_a_line_starting_with_inline_code_is_still_checked_for_prose(self):
        assert where("`code` then a dtls typo\n") == [(1, "DOC001")]

    def test_urls_and_file_names_are_skipped(self):
        text = "See https://example.com/api/v1 and www.example.com/json, edit config.json or docs/api.md.\n"
        assert lint(text) == []

    def test_autolinks_link_destinations_and_image_paths_are_skipped(self):
        text = "<https://example.com/api>\n\n[text](https://example.com/json)\n\n![diagram](images/json.png)\n"
        assert lint(text) == []

    def test_email_addresses_are_skipped(self):
        assert lint("Write to api@example.com.\n") == []

    def test_html_and_comments_are_skipped(self):
        assert lint('<!-- a dtls comment -->\n\n<div class="json">\napi\n</div>\n\nInline <span class="api">ok</span>\n') == []

    def test_front_matter_is_skipped(self):
        assert lint("---\ntitle: api and json notes\n---\n\n# Notes\n") == []

    def test_document_that_only_mentions_terms_in_code_and_urls_is_clean(self):
        text = (FIXTURES / "lint_targets.md").read_text(encoding="utf-8")
        flagged = {(i.line, i.rule) for i in lint(text)}
        assert (5, "DOC001") not in flagged  # `api` and `json` in inline code
        assert not any(line in (7, 8, 9, 10) for line, _ in flagged)  # the fenced block
        assert (12, "DOC001") in flagged  # only the link text, not the URLs
        assert (14, "DOC001") not in flagged  # the HTML comment

    def test_masking_keeps_line_numbers_right(self):
        text = "Line one.\n\nSee https://example.com/api for details.\nThen a dtls typo.\n"
        assert where(text) == [(4, "DOC001")]


class TestRedundantPhrases:
    def test_phrase_is_reported_with_a_suggestion(self):
        (issue,) = lint("We run it in order to save power.\n")
        assert (issue.line, issue.rule, issue.category) == (1, "DOC002", "Style")
        assert issue.message == "Redundant phrase found: 'in order to'. Consider simplifying."
        assert issue.suggestion == "to"

    def test_phrase_without_a_replacement_suggests_removing_it(self):
        (issue,) = lint("It is important to note that this works.\n")
        assert issue.suggestion == "remove it"

    def test_matching_ignores_case(self):
        assert where("In Order To save power.\n") == [(1, "DOC002")]

    def test_a_phrase_must_match_whole_words(self):
        assert lint("The queue is in order tomorrow and in orderto be.\n") == []

    def test_a_phrase_wrapped_across_lines_is_found_on_the_line_it_starts(self):
        assert where("We wrap it in order\nto save space.\n") == [(1, "DOC002")]

    def test_every_occurrence_is_reported(self):
        assert where("in order to a and in order to b\n") == [(1, "DOC002")] * 2

    def test_phrases_in_code_are_ignored(self):
        assert lint("`in order to`\n\n```\nin order to\n```\n") == []

    def test_a_phrase_does_not_join_across_paragraphs_or_inline_code(self):
        assert lint("end in order\n\nto start\n\nIn order `x` to go\n") == []


class TestAcronyms:
    def test_an_undefined_acronym_is_reported_once_at_first_use(self):
        issues = lint("The PSK is used.\n\nLater the PSK again.\n")
        assert [(i.line, i.rule, i.severity) for i in issues] == [(1, "DOC003", "info")]
        assert issues[0].message == "Acronym 'PSK' is used without being defined."

    def test_defined_before_use_is_clean(self):
        assert lint("Pre-Shared Key (PSK) is defined.\n\nThe PSK is used.\n") == []

    def test_same_line_definition_then_use_is_clean(self):
        assert lint("The Pre-Shared Key (PSK) is shared, so the PSK is safe.\n") == []

    def test_use_before_the_definition_is_reported_with_the_definition_line(self):
        issues = lint("The PSK is used.\n\nPre-Shared Key (PSK) comes later.\n")
        assert [(i.line, i.message) for i in issues] == [
            (1, "Acronym 'PSK' is used before it is defined on line 3.")
        ]

    def test_reverse_form_defines_the_acronym(self):
        assert lint("PSK (Pre-Shared Key) is defined.\n\nThe PSK is used.\n") == []

    @pytest.mark.parametrize("text", ["URL", "TOC", "README", "NOTE", "API", "HTTPS"])
    def test_allowed_and_glossary_terms_need_no_definition(self, text):
        assert lint(f"Mention {text} here.\n") == []

    def test_two_letter_acronyms_are_not_checked_by_default(self):
        assert lint("Made in the UK.\n") == []

    def test_minimum_length_is_configurable(self):
        assert where("Made in the UK.\n", config=LintConfig(acronym_min_length=2)) == [(1, "DOC003")]

    def test_allowed_acronyms_are_configurable(self):
        config = LintConfig(allowed_acronyms=frozenset({"PSK"}))
        assert lint("The PSK is used.\n", config=config) == []

    @pytest.mark.parametrize(
        "text", ["`PSK`", "```\nPSK\n```", "https://example.com/PSK", "[x](https://example.com/PSK)", "docs/PSK.md"]
    )
    def test_acronyms_in_code_and_addresses_are_ignored(self, text):
        assert lint(text + "\n") == []

    def test_mixed_case_words_and_single_capitals_are_not_acronym_uses(self):
        assert lint("Word Iot CoAP A1 B I\n") == []

    def test_acronym_in_a_heading_is_checked(self):
        assert where("# About PSK\n") == [(1, "DOC003")]

    def test_the_rule_can_be_disabled_and_its_severity_changed(self):
        assert lint("The PSK.\n", config=LintConfig(disabled_rules=frozenset({"DOC003"}))) == []
        config = LintConfig(severities={"DOC003": "error"})
        assert [i.severity for i in lint("The PSK.\n", config=config)] == ["error"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Pre-Shared Key (PSK)", ["PSK"]),
        ("Pre-Shared Key(PSK)", ["PSK"]),
        ("Constrained Application Protocol (CoAP)", ["CoAP"]),
        ("Lightweight M2M (LwM2M)", ["LwM2M"]),
        ("Internet of Things (IoT)", ["IoT"]),
        ("over-the-air (OTA)", ["OTA"]),
        ("Software as a Service (SaaS)", ["SaaS"]),
        ("Peer to Peer (P2P)", ["P2P"]),
        ("Network Interface Card (NIC) and Vendor Management Information (VMI)", ["NIC", "VMI"]),
        ("The Lightweight M2M (LwM2M) protocol", ["LwM2M"]),
        ("PSK (Pre-Shared Key)", ["PSK"]),
        ("a plain sentence (NOTE)", []),
        ("see the table (ABC) below", []),
        ("API (see below)", []),
        ("Fine (OK)", []),
    ],
)
def test_acronym_definitions_are_recognised(text, expected):
    assert [name for name, _ in _definitions(text)] == expected


class TestResultsAndOrdering:
    def test_issues_are_ordered_by_line_then_rule(self):
        text = "Use in order to dtls.\n\nThe PSK and json.\n"
        assert [(i.line, i.rule) for i in lint(text)] == [(1, "DOC001"), (1, "DOC002"), (3, "DOC001"), (3, "DOC003")]

    def test_issue_text_form_has_file_line_severity_rule_and_message(self):
        (issue,) = DocLinter().lint_text("a dtls b\n", file="docs/a.md")
        assert str(issue).startswith(str(Path("docs/a.md")) + ":1: warning DOC001 [Glossary] Incorrect term capitalization 'dtls'.")

    def test_crlf_and_byte_order_mark_do_not_change_line_numbers(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_bytes(b"\xef\xbb\xbfOne.\r\n\r\nTwo dtls.\r\n")
        (issue,) = DocLinter().lint_file(path).issues
        assert issue.line == 3

    def test_the_fixture_gives_exactly_these_issues(self):
        result = DocLinter().lint_file(FIXTURES / "lint_targets.md")
        assert [(i.line, i.rule) for i in result.issues] == [
            (3, "DOC001"),
            (3, "DOC001"),
            (12, "DOC001"),
            (18, "DOC002"),
            (18, "DOC002"),
        ]
