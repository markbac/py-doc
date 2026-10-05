"""
py-doc: Markdown technical documentation tools.

Provides Markdown to Word (.docx) and PowerPoint (.pptx) conversion and Markdown style linting.
"""

__version__ = "0.1.0"

from .errors import ConversionError
from .render.docx import DocxConverter
from .render.pptx import SlidesConverter

__all__ = ["ConversionError", "DocxConverter", "SlidesConverter"]
