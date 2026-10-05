"""
py-doc: Markdown technical documentation tools.

Currently provides the Markdown to Word (.docx) converter.
"""

__version__ = "0.1.0"

from .render.docx import ConversionError, DocxConverter

__all__ = ["ConversionError", "DocxConverter"]
