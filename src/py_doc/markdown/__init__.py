"""Markdown parsing into one document model shared by the renderers and the linter."""

from .dump import dump
from .nodes import Document, plain_text, walk
from .parser import ParseError, parse

__all__ = ["Document", "ParseError", "dump", "parse", "plain_text", "walk"]
