"""Errors shared by the renderers."""


class ConversionError(Exception):
    """The input cannot be converted (for example, it is not valid UTF-8)."""
