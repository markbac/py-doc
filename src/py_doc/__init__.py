"""
py-doc: Markdown technical documentation tools.

Provides Markdown to Word (.docx) and PowerPoint (.pptx) conversion and Markdown style linting.
"""

__version__ = "0.1.0"

from .errors import ConversionError
from .convert import DocxConverter, SlidesConverter

__all__ = ["ConversionError", "DocxConverter", "Picture", "SlidesConverter", "render_diagram"]


def __getattr__(name):
    """``render_diagram`` and ``Picture`` (py_doc.diagram_api), imported when first asked for."""
    if name in ("render_diagram", "Picture"):
        from . import diagram_api

        return getattr(diagram_api, name)
    raise AttributeError(f"module 'py_doc' has no attribute {name!r}")
