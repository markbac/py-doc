"""Content generators: Markdown made from other sources before anything is parsed, linted, built or published.

Each generator in ``content.generators`` of ``py-doc.yml`` writes one Markdown file, its ``output``, which a
document can then list as a source like any other. A file is only rewritten when its text changes.

Built-in types: ``glossary``, ``documents`` (an index of the documents), ``toc`` (a document's contents),
``adr-index``, ``requirements`` (a traceability table), ``openapi``, ``asyncapi``, ``python-api``, ``diagram``
(a Mermaid, PlantUML or other diagram file as a fenced block that the build draws), ``command`` (any program
whose output is Markdown) and ``python`` (a function of your own). Packages can add types through the
``py_doc.generators`` entry point group, so the core depends on none of their tools.
"""

from .registry import GeneratorError, available, run_generators

__all__ = ["GeneratorError", "available", "run_generators"]
