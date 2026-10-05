"""Parse Markdown text into the document model in :mod:`py_doc.markdown.nodes`.

Parsing is done by markdown-it-py (CommonMark, plus tables and front matter). This module only
turns its token stream into typed nodes. A token it does not know raises :class:`ParseError`
instead of being skipped, so content can never disappear silently.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.front_matter import front_matter_plugin

from . import nodes as n


class ParseError(Exception):
    """The Markdown contains a construct the document model does not cover."""


_MARKDOWN = MarkdownIt("commonmark").enable("table").use(front_matter_plugin)

_ALIGNMENTS = {"text-align:left": "left", "text-align:right": "right", "text-align:center": "center"}


def parse(text: str) -> n.Document:
    """Parse Markdown ``text`` into a :class:`~py_doc.markdown.nodes.Document`."""
    source = text.replace("\r\n", "\n").replace("\r", "\n")
    return _Builder(_MARKDOWN.parse(source), source.split("\n")).document()


class _Builder:
    def __init__(self, tokens: list[Token], lines: list[str]) -> None:
        self.tokens = tokens
        self.lines = lines
        self.front_matter: n.FrontMatter | None = None

    def document(self) -> n.Document:
        children, _ = self._blocks(0, None)
        return n.Document(front_matter=self.front_matter, children=children)

    def _span(self, token: Token) -> tuple[int, int]:
        """First and last source line (1-based, inclusive) of a block token.

        markdown-it ends some ranges (lists, list items) after the blank lines that follow them,
        so trailing blank lines, and lines holding only block quote markers, are trimmed here.
        """
        assert token.map is not None
        start, end = token.map[0] + 1, token.map[1]
        while end > start and not self.lines[end - 1].strip(" \t>"):
            end -= 1
        return start, end

    # --- blocks ---------------------------------------------------------------------------------

    def _blocks(self, i: int, end_type: str | None) -> tuple[list[n.Block], int]:
        """Build blocks from ``i`` up to the token ``end_type``. Returns them and the next index."""
        tokens = self.tokens
        blocks: list[n.Block] = []
        while i < len(tokens):
            token = tokens[i]
            kind = token.type
            if kind == end_type:
                return blocks, i + 1

            if kind == "front_matter":
                line, end_line = self._span(token)
                self.front_matter = n.FrontMatter(line, end_line, token.content)
                i += 1
            elif kind == "heading_open":
                line, end_line = self._span(token)
                children = self._inlines(tokens[i + 1], line)
                blocks.append(n.Heading(line, end_line, int(token.tag[1]), children))
                i += 3
            elif kind == "paragraph_open":
                line, end_line = self._span(token)
                blocks.append(n.Paragraph(line, end_line, self._inlines(tokens[i + 1], line)))
                i += 3
            elif kind in ("fence", "code_block"):
                blocks.append(self._code_block(token))
                i += 1
            elif kind == "hr":
                blocks.append(n.ThematicBreak(*self._span(token)))
                i += 1
            elif kind == "html_block":
                blocks.append(n.HtmlBlock(*self._span(token), token.content.removesuffix("\n")))
                i += 1
            elif kind == "blockquote_open":
                children, i = self._blocks(i + 1, "blockquote_close")
                blocks.append(n.BlockQuote(*self._span(token), children))
            elif kind in ("bullet_list_open", "ordered_list_open"):
                list_node, i = self._list(i)
                blocks.append(list_node)
            elif kind == "table_open":
                table, i = self._table(i)
                blocks.append(table)
            else:
                where = f" at line {token.map[0] + 1}" if token.map else ""
                raise ParseError(f"Unsupported Markdown block '{kind}'{where}")
        if end_type is not None:
            raise ParseError(f"Missing closing token '{end_type}'")
        return blocks, i

    def _code_block(self, token: Token) -> n.CodeBlock:
        line, end_line = self._span(token)
        text = token.content.removesuffix("\n")
        if token.type == "code_block":
            return n.CodeBlock(line, end_line, text, None, "", False, True)
        info = token.info.strip()
        language = info.split()[0] if info else None
        return n.CodeBlock(line, end_line, text, language, info, True, self._fence_closed(token))

    def _fence_closed(self, token: Token) -> bool:
        """Whether the last line of a fenced block is a closing fence (it is not for a fence that
        runs to the end of the document or its container)."""
        assert token.map is not None
        start, end = token.map
        if end - start < 2:
            return False
        last = self.lines[end - 1].lstrip(" \t>").rstrip()
        return len(last) >= len(token.markup) and set(last) == {token.markup[0]}

    def _list(self, i: int) -> tuple[n.List, int]:
        tokens = self.tokens
        open_token = tokens[i]
        ordered = open_token.type == "ordered_list_open"
        close_type = "ordered_list_close" if ordered else "bullet_list_close"
        start = int(open_token.attrs.get("start", 1)) if ordered else None

        items: list[n.ListItem] = []
        tight = True
        i += 1
        while tokens[i].type != close_type:
            item_token = tokens[i]
            children, next_i = self._blocks(i + 1, "list_item_close")
            for t in tokens[i + 1 : next_i]:
                if t.type == "paragraph_open" and t.level == item_token.level + 1 and not t.hidden:
                    tight = False
            items.append(n.ListItem(*self._span(item_token), children))
            i = next_i
        return n.List(*self._span(open_token), ordered, start, tight, items), i + 1

    def _table(self, i: int) -> tuple[n.Table, int]:
        tokens = self.tokens
        open_token = tokens[i]
        rows: list[n.TableRow] = []
        in_header = False
        i += 1
        while tokens[i].type != "table_close":
            kind = tokens[i].type
            if kind == "thead_open":
                in_header = True
                i += 1
            elif kind == "thead_close":
                in_header = False
                i += 1
            elif kind in ("tbody_open", "tbody_close"):
                i += 1
            elif kind == "tr_open":
                line, end_line = self._span(tokens[i])
                cells: list[n.TableCell] = []
                i += 1
                while tokens[i].type != "tr_close":
                    style = tokens[i].attrs.get("style")
                    align = _ALIGNMENTS.get(str(style)) if style else None
                    cells.append(n.TableCell(line, align, self._inlines(tokens[i + 1], line)))
                    i += 3  # th_open or td_open, inline, th_close or td_close
                rows.append(n.TableRow(line, end_line, in_header, cells))
                i += 1
            else:
                raise ParseError(f"Unsupported table token '{kind}'")
        return n.Table(*self._span(open_token), rows), i + 1

    # --- inline ---------------------------------------------------------------------------------

    def _inlines(self, inline_token: Token, line: int) -> list[n.Inline]:
        """Convert the children of an ``inline`` token. ``line`` is the first source line."""
        current = [line]  # advanced by every line break, so each node knows its own line
        nodes, _ = self._inline_run(inline_token.children or [], 0, None, current)
        return nodes

    def _inline_run(
        self, tokens: list[Token], i: int, end_type: str | None, current: list[int]
    ) -> tuple[list[n.Inline], int]:
        nodes: list[n.Inline] = []
        while i < len(tokens):
            token = tokens[i]
            kind = token.type
            if kind == end_type:
                return nodes, i + 1

            line = current[0]
            if kind in ("text", "text_special"):
                if token.content:  # markdown-it leaves empty text tokens around emphasis markers
                    nodes.append(n.Text(line, token.content))
            elif kind == "code_inline":
                nodes.append(n.CodeSpan(line, token.content))
            elif kind == "softbreak":
                nodes.append(n.SoftBreak(line))
                current[0] += 1
            elif kind == "hardbreak":
                nodes.append(n.HardBreak(line))
                current[0] += 1
            elif kind == "html_inline":
                nodes.append(n.HtmlInline(line, token.content))
                current[0] += token.content.count("\n")
            elif kind in ("em_open", "strong_open"):
                close = "em_close" if kind == "em_open" else "strong_close"
                children, i = self._inline_run(tokens, i + 1, close, current)
                nodes.append((n.Emphasis if kind == "em_open" else n.Strong)(line, children))
                continue
            elif kind == "link_open":
                title = token.attrs.get("title")
                children, i = self._inline_run(tokens, i + 1, "link_close", current)
                nodes.append(n.Link(line, str(token.attrs.get("href", "")), str(title) if title else None, children))
                continue
            elif kind == "image":
                alt_nodes, _ = self._inline_run(token.children or [], 0, None, [line])
                title = token.attrs.get("title")
                nodes.append(
                    n.Image(line, str(token.attrs.get("src", "")), str(title) if title else None, n.plain_text(alt_nodes))
                )
            else:
                raise ParseError(f"Unsupported inline Markdown '{kind}' at line {line}")
            i += 1
        if end_type is not None:
            raise ParseError(f"Missing closing token '{end_type}'")
        return nodes, i
