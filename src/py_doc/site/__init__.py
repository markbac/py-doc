"""Web sites made of a project's documents: ``py-doc site``, with MkDocs or Astro + Starlight.

py-doc writes the pages and the navigation and runs the site's own tool. It never replaces the site's
configuration: a new site is scaffolded once (``py-doc site init``), and an existing one keeps its own.
"""

from .engines import ENGINES, Engine, engine_for
from .pages import Page, generate_site

__all__ = ["ENGINES", "Engine", "Page", "engine_for", "generate_site"]
