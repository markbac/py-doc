"""Tests for the shared Markdown document model (#2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from py_doc.markdown import ParseError, dump, parse, plain_text, walk
from py_doc.markdown import nodes as n

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_NAMES = sorted(p.stem for p in FIXTURE_DIR.glob("*.md"))


def blocks(markdown: str) -> list:
    return parse(markdown).children


def kinds(markdown: str) -> list[str]:
    return [type(b).__name__ for b in blocks(markdown)]


class TestBlocks:
    def test_headings_carry_level_and_text(self):
        doc = parse("# One\n\n### Three\n\n###### Six\n")
        assert [(h.level, plain_text(h.children)) for h in doc.children] == [
            (1, "One"), (3, "Three"), (6, "Six"),
        ]  # fmt: skip

    def test_setext_headings_are_headings(self):
        doc = parse("Title\n=====\n\nSub\n---\n")
        assert [(h.level, plain_text(h.children)) for h in doc.children] == [(1, "Title"), (2, "Sub")]

    @pytest.mark.parametrize("line", ["#NoSpace", "#123", "####### seven"])
    def test_hash_without_space_or_beyond_six_levels_is_a_paragraph(self, line):
        assert kinds(f"{line}\n") == ["Paragraph"]

    def test_empty_input_has_no_blocks(self):
        assert parse("").children == []
        assert parse("\n\n  \n").children == []

    def test_thematic_breaks(self):
        assert kinds("a\n\n---\n\n***\n\n____\n\nb\n") == [
            "Paragraph", "ThematicBreak", "ThematicBreak", "ThematicBreak", "Paragraph",
        ]  # fmt: skip

    def test_html_block_and_comment_are_kept(self):
        doc = parse("<!-- note -->\n\n<div>\nraw\n</div>\n")
        assert [b.text for b in doc.children] == ["<!-- note -->", "<div>\nraw\n</div>"]

    def test_block_quote_contains_blocks(self):
        (quote,) = blocks("> Quote\n>\n> - item\n")
        assert isinstance(quote, n.BlockQuote)
        assert [type(c).__name__ for c in quote.children] == ["Paragraph", "List"]


class TestLists:
    def test_bullet_and_ordered_lists(self):
        bullet, ordered = blocks("- a\n- b\n\n1. x\n2. y\n")
        assert (bullet.ordered, bullet.start) == (False, None)
        assert (ordered.ordered, ordered.start) == (True, 1)
        assert [plain_text(i.children[0].children) for i in ordered.children] == ["x", "y"]

    def test_ordered_list_remembers_its_start_number(self):
        (ordered,) = blocks("5. five\n6. six\n")
        assert ordered.start == 5

    def test_tight_and_loose_lists(self):
        tight, loose = blocks("- a\n- b\n\ntext\n\n- a\n\n- b\n")[0::2]
        assert tight.tight is True
        assert loose.tight is False

    def test_nested_lists_are_children_of_their_item(self):
        (outer,) = blocks("- parent\n  - child\n    - grandchild\n- sibling\n")
        first, second = outer.children
        assert [type(c).__name__ for c in first.children] == ["Paragraph", "List"]
        (middle,) = [c for c in first.children if isinstance(c, n.List)]
        (grandchild_list,) = [c for c in middle.children[0].children if isinstance(c, n.List)]
        assert plain_text(grandchild_list.children[0].children[0].children) == "grandchild"
        assert plain_text(second.children[0].children) == "sibling"

    def test_numbered_lines_that_are_not_list_items_stay_paragraphs(self):
        assert kinds("10.5 is a number\n\n2.4.1 fixes it\n\n1.foo\n") == ["Paragraph"] * 3


class TestCodeBlocks:
    def test_fenced_block_has_language_text_and_closed_flag(self):
        (code,) = blocks("```python title=x\nprint(1)\n\nprint(2)\n```\n")
        assert (code.language, code.info) == ("python", "python title=x")
        assert code.text == "print(1)\n\nprint(2)"
        assert (code.fenced, code.closed) == (True, True)
        assert (code.line, code.end_line) == (1, 5)

    def test_fence_without_info_has_no_language(self):
        (code,) = blocks("```\nplain\n```\n")
        assert (code.language, code.info) == (None, "")

    def test_markdown_inside_a_fence_is_not_parsed(self):
        (code,) = blocks("```\n# not a heading\n- not a list\n---\n```\n")
        assert code.text == "# not a heading\n- not a list\n---"

    def test_tilde_fence_and_longer_outer_fence(self):
        tilde, nested = blocks("~~~\ncode\n~~~\n\n````\n```\ninner\n```\n````\n")
        assert tilde.text == "code"
        assert nested.text == "```\ninner\n```"
        assert nested.closed

    def test_unclosed_fence_keeps_its_content_and_is_flagged(self):
        before, code = blocks("Before\n\n```python\nprint('kept')\nmore = 1\n")
        assert code.text == "print('kept')\nmore = 1"
        assert code.closed is False

    def test_empty_unclosed_fence_is_flagged(self):
        (code,) = blocks("```\n")
        assert (code.text, code.closed) == ("", False)

    def test_unclosed_fence_whose_last_line_looks_like_another_fence(self):
        (code,) = blocks("```\ncode\n~~~\n")
        assert code.closed is False

    def test_fence_inside_a_block_quote_is_closed_correctly(self):
        (quote,) = blocks("> ```\n> inside\n> ```\n")
        assert quote.children[0].closed is True

    def test_indented_code_block(self):
        (code,) = blocks("    one\n    two\n")
        assert (code.text, code.fenced, code.language) == ("one\ntwo", False, None)


class TestTables:
    def test_header_rows_cells_and_alignment(self):
        (table,) = blocks("| A | B | C |\n|:--|:-:|--:|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n")
        header, *body = table.children
        assert header.header and not any(r.header for r in body)
        assert [plain_text(c.children) for c in header.children] == ["A", "B", "C"]
        assert [c.align for c in header.children] == ["left", "center", "right"]
        assert [[plain_text(c.children) for c in r.children] for r in body] == [["1", "2", "3"], ["4", "5", "6"]]

    def test_columns_without_alignment_have_none(self):
        (table,) = blocks("| A | B |\n| - | - |\n| 1 | 2 |\n")
        assert [c.align for c in table.children[0].children] == [None, None]

    def test_inline_formatting_in_cells(self):
        (table,) = blocks("| h |\n|---|\n| **bold** `code` |\n")
        cell = table.children[1].children[0]
        assert [type(c).__name__ for c in cell.children] == ["Strong", "Text", "CodeSpan"]


class TestInline:
    def test_emphasis_strong_and_code_span(self):
        (para,) = blocks("A **strong**, *emphasised* and `code` word.\n")
        assert [type(c).__name__ for c in para.children] == [
            "Text", "Strong", "Text", "Emphasis", "Text", "CodeSpan", "Text",
        ]  # fmt: skip
        assert plain_text(para.children) == "A strong, emphasised and code word."

    def test_nested_formatting(self):
        (para,) = blocks("***both*** and **bold with *inner* word**\n")
        assert [type(c).__name__ for c in para.children] == ["Emphasis", "Text", "Strong"]
        assert [type(c).__name__ for c in para.children[0].children] == ["Strong"]
        assert [type(c).__name__ for c in para.children[2].children] == ["Text", "Emphasis", "Text"]

    def test_no_empty_text_nodes(self):
        for markdown in ["**a**", "*a*`b`", "[**a**](u)", "| h |\n|---|\n| **a** |\n"]:
            assert [x for x in walk(parse(markdown)) if isinstance(x, n.Text) and not x.text] == []

    def test_inline_link_with_title(self):
        (para,) = blocks('See [the *site*](https://example.com "Title").\n')
        link = para.children[1]
        assert (link.url, link.title) == ("https://example.com", "Title")
        assert plain_text(link.children) == "the site"

    def test_reference_link_is_resolved_and_definition_disappears(self):
        doc = parse("A [guide][g] here.\n\n[g]: https://example.com/guide\n")
        (para,) = doc.children
        assert para.children[1].url == "https://example.com/guide"

    def test_autolink(self):
        (para,) = blocks("<https://example.com/auto>\n")
        assert para.children[0].url == "https://example.com/auto"

    def test_image_alt_is_plain_text(self):
        (para,) = blocks('![An *architecture* `view`](img/a.png "Title")\n')
        image = para.children[0]
        assert (image.url, image.title, image.alt) == ("img/a.png", "Title", "An architecture view")

    def test_breaks(self):
        (para,) = blocks("soft\nwrapped  \nhard\n")
        assert [type(c).__name__ for c in para.children] == ["Text", "SoftBreak", "Text", "HardBreak", "Text"]
        assert plain_text(para.children) == "soft wrapped hard"

    def test_inline_html_is_kept(self):
        (para,) = blocks("a <span>b</span> c\n")
        assert [c.text for c in para.children if isinstance(c, n.HtmlInline)] == ["<span>", "</span>"]

    def test_escapes_and_entities_become_text(self):
        (para,) = blocks("\\*not emphasis\\* &amp; more\n")
        assert plain_text(para.children) == "*not emphasis* & more"

    def test_unsupported_syntax_stays_literal_text(self):
        (para,) = blocks("~~struck~~ and [ ] box\n")
        assert plain_text(para.children) == "~~struck~~ and [ ] box"


class TestFrontMatter:
    def test_front_matter_is_separate_from_the_content(self):
        doc = parse("---\ntitle: X\ntags: [a]\n---\n\n# Heading\n")
        assert doc.front_matter.text == "title: X\ntags: [a]"
        assert (doc.front_matter.line, doc.front_matter.end_line) == (1, 4)
        assert kinds("---\ntitle: X\n---\n\n# Heading\n") == ["Heading"]

    def test_document_without_front_matter(self):
        assert parse("# Heading\n").front_matter is None

    def test_leading_rule_without_a_closing_rule_is_a_thematic_break(self):
        doc = parse("---\n\nText\n")
        assert doc.front_matter is None
        assert [type(b).__name__ for b in doc.children] == ["ThematicBreak", "Paragraph"]


class TestPositions:
    def test_block_lines_are_one_based_and_inclusive(self):
        doc = parse("# H\n\npara one\npara two\n\n- a\n- b\n\n```\ncode\n```\n")
        assert [(type(b).__name__, b.line, b.end_line) for b in doc.children] == [
            ("Heading", 1, 1), ("Paragraph", 3, 4), ("List", 6, 7), ("CodeBlock", 9, 11),
        ]  # fmt: skip

    def test_trailing_blank_lines_are_not_part_of_a_list(self):
        (lst,) = blocks("- a\n- b\n\n\n")
        assert (lst.line, lst.end_line) == (1, 2)
        assert [(i.line, i.end_line) for i in lst.children] == [(1, 1), (2, 2)]

    def test_inline_nodes_know_their_own_line(self):
        (para,) = blocks("one *two\nthree* four\nfive\n")
        assert [(type(c).__name__, c.line) for c in para.children] == [
            ("Text", 1), ("Emphasis", 1), ("Text", 2), ("SoftBreak", 2), ("Text", 3),
        ]  # fmt: skip
        emphasis = para.children[1]
        assert [(type(c).__name__, c.line) for c in emphasis.children] == [
            ("Text", 1), ("SoftBreak", 1), ("Text", 2),
        ]  # fmt: skip

    def test_lines_after_a_front_matter_block_are_counted_from_the_top(self):
        doc = parse("---\na: 1\n---\n# Heading\n")
        assert doc.children[0].line == 4

    def test_crlf_and_cr_line_endings_give_the_same_lines(self):
        lf = dump(parse("# H\n\ntext\nmore\n"))
        assert dump(parse("# H\r\n\r\ntext\r\nmore\r\n")) == lf
        assert dump(parse("# H\r\rtext\rmore\r")) == lf


class TestWalk:
    def test_walk_visits_every_node_in_source_order(self):
        doc = parse("---\na: 1\n---\n# H *e*\n\n- item\n")
        assert [type(x).__name__ for x in walk(doc)] == [
            "Document", "FrontMatter", "Heading", "Text", "Emphasis", "Text", "List", "ListItem", "Paragraph", "Text",
        ]  # fmt: skip


ODD_INPUTS = [
    "", "\n", "   \n\t\n", "```", "~~~\n", "<!-- unclosed", "<div>", "> > > deep", "\\", "&amp; &unknown;",
    "[a]: /u\n\n[a] [b] [c]", "![](x)", "[](x)", "- [ ] task\n- [x] done", "1. \n2.\n", "-\n-\n", "* * *",
    "| a |\n|---|\n", "| a | b |\n|---|\n| 1 |", "[^1]: note\n\ntext[^1]", "Term\n: Definition",
    "- a\n\n      code in list\n- b", "# \n#\n## ##", "***\n---\n___", "a  \n  \nb", "<a href='x'>y</a>",
    "`` ` ``", "``` ` ```", "text with\u0085separators", "$$ math $$", " 　 spaces",
]  # fmt: skip


@pytest.mark.parametrize("markdown", ODD_INPUTS, ids=[repr(m)[:30] for m in ODD_INPUTS])
def test_odd_input_never_raises_and_has_sane_positions(markdown):
    doc = parse(markdown)
    last_line = markdown.count("\n") + 1
    for node in walk(doc):
        line = getattr(node, "line", None)
        if line is not None:
            assert 1 <= line <= last_line, (type(node).__name__, line)
        end_line = getattr(node, "end_line", None)
        if end_line is not None:
            assert line <= end_line <= last_line, (type(node).__name__, line, end_line)


def test_unknown_tokens_raise_instead_of_being_skipped(monkeypatch):
    from py_doc.markdown import parser

    monkeypatch.setattr(parser, "_MARKDOWN", parser.MarkdownIt("commonmark").enable("table").enable("strikethrough"))
    with pytest.raises(ParseError, match="Unsupported inline Markdown 's_open' at line 1"):
        parse("~~struck~~\n")


# --- the fixture corpus ----------------------------------------------------------------------

WORD = re.compile(r"[^\W\d_]{2,}")


def _content_words(markdown: str) -> set[str]:
    """Words found in the text of every node that carries text, including URLs and info strings."""
    parts: list[str] = []
    for node in walk(parse(markdown)):
        for attribute in ("text", "url", "title", "alt", "info"):
            value = getattr(node, attribute, None)
            if isinstance(value, str):
                parts.append(value)
    return {w.lower() for w in WORD.findall(" ".join(parts))}


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_parses_and_keeps_every_word(name):
    source = (FIXTURE_DIR / name).with_suffix(".md").read_text(encoding="utf-8")
    source_words = {w.lower() for w in WORD.findall(source)}
    assert source_words - _content_words(source) == set()


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_golden_outline(name, check_ast_golden):
    """Change detector for the document model.

    A failure means the model of a fixture changed. If that is intended, regenerate with
    UPDATE_GOLDEN=1 and review the diff.
    """
    source = (FIXTURE_DIR / f"{name}.md").read_text(encoding="utf-8")
    check_ast_golden(name, dump(parse(source)))
