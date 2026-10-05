"""The old `pydoclint` interface on top of `py_doc.lint`.

The old methods returned plain lists and dictionaries, and could not report a file that was
missing or unreadable. The new linter reports that, so here it is logged and the file has no issues,
as before. New code should use `py_doc.lint.DocLinter`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from py_doc.lint import DocLinter as _DocLinter

logger = logging.getLogger(__name__)


class LintIssue:
    def __init__(self, file: Path, line_no: int, category: str, message: str, severity: str = "warning"):
        self.file = Path(file)
        self.line_no = line_no
        self.category = category
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"[{self.severity.upper()}] {self.file.name}:{self.line_no} [{self.category}] {self.message}"


class DocLinter:
    def __init__(self, glossary: Optional[Dict[str, List[str]]] = None):
        self._linter = _DocLinter(glossary=glossary)

    def lint_file(self, file_path: Path) -> List[LintIssue]:
        result = self._linter.lint_file(Path(file_path).resolve())
        if result.error:
            logger.error(f"Could not lint {file_path}: {result.error}")
            return []
        return [LintIssue(i.file, i.line, i.category, i.message, i.severity) for i in result.issues]

    def lint_directory(self, search_dir: Path) -> Dict[str, List[LintIssue]]:
        search_dir = Path(search_dir).resolve()
        results: Dict[str, List[LintIssue]] = {}
        if not search_dir.is_dir():
            return results
        for path in self._linter.find_files(search_dir):
            issues = self.lint_file(path)
            if issues:
                results[str(path)] = issues
        return results
