"""Diagram fences in Markdown become pictures, drawn by tools in the container and cached between builds."""

from .registry import BY_FENCE, RENDERERS
from .render import DiagramError, Rendered, cache_dir, copy_pictures, render_parts

__all__ = ["BY_FENCE", "RENDERERS", "DiagramError", "Rendered", "cache_dir", "copy_pictures", "render_parts"]
