"""Compatibility alias for the old import name. Use `py_doc` in new code."""

from py_doc import ConversionError, SlidesConverter, __version__

__all__ = ["ConversionError", "SlidesConverter", "__version__"]
