"""Maths on posters: ``$...$`` and ``$$...$$`` in the Markdown, compiled to MathML when the page is built.

MathML is drawn by the browser itself, so the page needs no script and no maths font, and a PDF keeps the
equations as vector text. A dollar followed by a space or a digit is not maths, so prices such as $5 stay text.
"""

from __future__ import annotations

import html
import logging
from functools import lru_cache

from latex2mathml.converter import convert
from mdit_py_plugins.dollarmath import dollarmath_plugin

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def mathml(latex: str, display: bool = False) -> str:
    """``latex`` as a MathML ``<math>`` element. A formula that cannot be read is shown as its source, with a
    warning, so one mistake does not stop the poster."""
    latex = latex.strip()
    try:
        return convert(latex, display="block" if display else "inline")
    except Exception as exc:  # latex2mathml raises its own error for each kind of mistake
        logger.warning(f"maths not rendered: ${latex}$ ({type(exc).__name__})")
        return f'<code class="math-error">{html.escape(latex)}</code>'


def enable(md) -> None:
    """Add ``$...$`` (inline) and ``$$...$$`` (display) maths to the markdown-it parser ``md``."""
    dollarmath_plugin(md, allow_labels=False, allow_space=False, allow_digits=False, double_inline=True)

    def inline(renderer, tokens, idx, options, env):
        return f'<span class="math">{mathml(tokens[idx].content)}</span>'

    def display_inline(renderer, tokens, idx, options, env):  # $$...$$ inside a paragraph: displayed, as pandoc does
        return f'<span class="math display">{mathml(tokens[idx].content, True)}</span>'

    def block(renderer, tokens, idx, options, env):
        return f'<div class="math display">{mathml(tokens[idx].content, True)}</div>\n'

    md.add_render_rule("math_inline", inline)
    md.add_render_rule("math_inline_double", display_inline)
    md.add_render_rule("math_block", block)
