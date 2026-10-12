"""Pandoc as the document engine: Word, PowerPoint, PDF (XeLaTeX) and HTML from joined Markdown.

Pandoc and TeX run in the tool container, so nothing but Python and the container engine has to be
installed. The Lua filters, highlight theme, LaTeX template and default CSS in ``resources`` are part
of the package and are mounted read-only.
"""

from .engine import RESOURCES, PandocJob, convert

__all__ = ["RESOURCES", "PandocJob", "convert"]
