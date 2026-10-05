"""
py-doc: Markdown technical documentation tools.

Provides Markdown to Word (.docx) conversion and Markdown style linting.
"""

__version__ = "0.1.0"

from .errors import ConversionError
from .render.docx import DocxConverter

__all__ = ["ConversionError", "DocxConverter"]
