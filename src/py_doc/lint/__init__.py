"""Technical writing style and glossary checks for Markdown, built on the shared document model."""

from .config import LintConfig
from .linter import DocLinter, LintTargetError
from .model import FileResult, LintIssue, LintReport

__all__ = ["DocLinter", "FileResult", "LintConfig", "LintIssue", "LintReport", "LintTargetError"]
