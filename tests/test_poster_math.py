"""Maths on posters ($...$ and $$...$$ as MathML), and the equation and terminal blocks."""

from __future__ import annotations

import html
import logging
from pathlib import Path

import pytest

from py_doc import poster_math
from py_doc.lint.text import _mask
from py_doc.poster_blocks import MD, Ctx, PosterError, block_html, inline, parse_opts
from py_doc.poster_themes import Theme, load_theme


def ctx():
    return Ctx(Path("."), lambda: None, Theme(), render=lambda text, c: text, where="test.md")


def block(lang, code, info=""):
    return block_html(lang, parse_opts(info), code, ctx())


# --- $...$ and $$...$$ ---


def test_inline_maths_becomes_mathml():
    out = MD.render("Energy $E = mc^2$ is mass.")
    assert '<span class="math"><math xmlns="http://www.w3.org/1998/Math/MathML" display="inline">' in out
    assert "<msup><mi>c</mi><mn>2</mn></msup>" in out
    assert "$" not in out


def test_display_maths_is_a_block_of_its_own():
    out = MD.render("$$\nR_s = \\frac{2GM}{c^2}\n$$")
    assert out.startswith('<div class="math display"><math') and 'display="block"' in out and "<mfrac>" in out


def test_double_dollars_in_a_paragraph_are_displayed_and_stay_in_it():
    out = MD.render("So $$x^2$$ here.")
    assert out.startswith("<p>So <span") and 'display="block"' in out


def test_maths_works_in_inline_text_and_table_cells():
    assert "<math" in inline("speed $v$ in m/s")
    assert "<math" in MD.render("| a | $\\alpha$ |\n|---|---|\n| 1 | 2 |")


@pytest.mark.parametrize("text", ["Costs $5 and $10 today.", "A price $ 5 $ with spaces.", "£2.00 credit"])
def test_money_is_not_maths(text):
    assert "<math" not in MD.render(text)


def test_a_formula_that_cannot_be_read_shows_its_source_with_a_warning(caplog):
    poster_math.mathml.cache_clear()
    with caplog.at_level(logging.WARNING):
        out = MD.render("Broken $\\frac{$ here.")
    assert '<code class="math-error">\\frac{</code>' in out
    assert "maths not rendered" in caplog.text


# --- equation ---

SCHWARZSCHILD = """title: Schwarzschild radius
R_s = \\frac{2GM}{c^2}
R_s | Event horizon radius | m
G | Gravitational constant | 6.674 × 10⁻¹¹ m³ kg⁻¹ s⁻²
The radius of the **event horizon**."""


def test_an_equation_card_has_its_title_formula_legend_and_notes():
    out = block("equation", SCHWARZSCHILD)
    assert out.startswith('<div class="eqs" style="grid-template-columns:repeat(1,')
    assert '<div class="ch">Schwarzschild radius</div>' in out
    assert '<div class="f"><math' in out and 'display="block"' in out
    assert out.count("<tr>") == 2 and "<td>Event horizon radius</td><td>m</td>" in out
    assert '<div class="notes">The radius of the <strong>event horizon</strong>.</div>' in out


def test_equation_cards_are_split_by_dashes_and_laid_out_in_columns():
    out = block("equation", "E = mc^2\n---\nF = ma\n---\np = mv", "cols=2")
    assert out.count('<div class="eq">') == 3 and "repeat(2," in out


def test_a_formula_over_several_lines_is_one_formula():
    out = block("equation", "a = b\n+ c\nx | a symbol | m")
    assert out.count("<math") == 2  # the formula and the one legend symbol


def test_an_equation_without_a_formula_is_an_error():
    with pytest.raises(PosterError, match="has no formula"):
        block("equation", "title: Nothing here")
    with pytest.raises(PosterError, match="needs a formula"):
        block("equation", "\n---\n")


# --- terminal ---


def test_a_terminal_shows_prompts_comments_output_and_its_caption():
    out = block(
        "terminal", "$ git status -sb\n## main\n M src/main.c\n# staged nothing\n-- One file modified", 'title="git"'
    )
    assert '<div class="cmd"><span class="p">$</span><b>git status -sb</b></div>' in out
    assert '<div class="cmt">## main</div>' in out  # a line starting with # is dimmed
    assert "<div> M src/main.c</div>" in out
    assert '<div class="bar"><i></i><i></i><i></i><span>git</span></div>' in out
    assert '<div class="cap">One file modified</div>' in out


@pytest.mark.parametrize(
    "line, prompt",
    [("> dir", ">"), ("PS> ls", "PS>"), ("PS C:\\work> ls", "PS C:\\work>"), ("pi@node:~$ uptime", "pi@node:~$")],
)
def test_terminal_prompts(line, prompt):
    assert f'<span class="p">{html.escape(prompt)}</span>' in block("terminal", line)


def test_terminal_screens_split_on_blank_lines_and_text_is_escaped():
    out = block("terminal", "$ echo '<b>'\n<b>\n\n$ ls")
    assert out.count('<div class="term">') == 2 and "repeat(2," in out
    assert "&lt;b&gt;" in out and "<b>'" not in out


def test_an_empty_terminal_is_an_error():
    with pytest.raises(PosterError, match="at least one line"):
        block("terminal", "\n\n")


def test_the_print_theme_has_a_light_terminal():
    assert Theme().colours["terminal"] != load_theme("print", Path(".")).colours["terminal"]


# --- lint ---


def test_the_linter_does_not_read_maths_as_prose():
    assert _mask("Energy $E = mc^2$ here.") == "Energy " + " " * len("$E = mc^2$") + " here."
    assert _mask("A $$x^2$$ b") == "A " + " " * 7 + " b"
    assert _mask("Costs $5 and $10.") == "Costs $5 and $10."
