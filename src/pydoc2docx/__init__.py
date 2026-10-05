"""Compatibility alias for the old import name. Use `py_doc` in new code."""

from py_doc import ConversionError, DocxConverter, __version__

__all__ = ["ConversionError", "DocxConverter", "__version__"]
