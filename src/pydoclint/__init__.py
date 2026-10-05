"""Compatibility alias for the old import name. Use `py_doc.lint` in new code."""

from py_doc import __version__

from .linter import DocLinter, LintIssue

__all__ = ["DocLinter", "LintIssue", "__version__"]
