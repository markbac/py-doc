"""Machine-readable lint output: JSON for scripts and SARIF 2.1.0 for code-scanning tools.

Both carry the canonical issue: rule, severity, file, line, column, message and suggestion. Files that could
not be linted are listed too, so a broken run never reads as a clean one.
"""

from __future__ import annotations

import json
from pathlib import Path

from py_doc import __version__

from .model import FileResult, LintIssue, LintReport

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_SARIF_LEVEL = {"error": "error", "warning": "warning", "info": "note"}


def _path(path: Path) -> str:
    return path.as_posix()


def issue_dict(issue: LintIssue) -> dict:
    return {
        "file": _path(issue.file),
        "line": issue.line,
        "column": issue.column,
        "severity": issue.severity,
        "rule": issue.rule,
        "category": issue.category,
        "message": issue.message,
        "suggestion": issue.suggestion,
    }


def summary(report: LintReport) -> dict:
    counts = {severity: 0 for severity in ("error", "warning", "info")}
    for issue in report.issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return {"files_scanned": report.files_scanned, "issues": len(report.issues), **counts, "files_failed": len(report.errors)}


def to_json(report: LintReport, issues: list[LintIssue], errors: list[FileResult]) -> str:
    """The report as JSON: a summary, every issue and every file that could not be linted."""
    data = {
        "tool": {"name": "py-doc", "version": __version__},
        "summary": summary(report),
        "issues": [issue_dict(issue) for issue in issues],
        "errors": [{"file": _path(result.file), "message": result.error} for result in errors],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def to_sarif(issues: list[LintIssue], errors: list[FileResult]) -> str:
    """The report as one SARIF 2.1.0 run. Paths are kept as given, relative ones relative to the working folder."""
    rules: dict[str, dict] = {}
    results = []
    for issue in issues:
        rules.setdefault(
            issue.rule,
            {"id": issue.rule, "name": issue.category, "defaultConfiguration": {"level": _SARIF_LEVEL[issue.severity]}},
        )
        region = {"startLine": max(issue.line, 1)}
        if issue.column:
            region["startColumn"] = issue.column
        message = issue.message + (f" Suggestion: {issue.suggestion}" if issue.suggestion else "")
        results.append(
            {
                "ruleId": issue.rule,
                "ruleIndex": list(rules).index(issue.rule),
                "level": _SARIF_LEVEL[issue.severity],
                "message": {"text": message},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": _path(issue.file)}, "region": region}}],
            }
        )
    run = {
        "tool": {"driver": {"name": "py-doc", "version": __version__, "informationUri": "https://github.com/markbac/py-doc", "rules": list(rules.values())}},
        "results": results,
        "invocations": [
            {
                "executionSuccessful": not errors,
                "toolExecutionNotifications": [
                    {"level": "error", "message": {"text": result.error}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": _path(result.file)}}}]}
                    for result in errors
                ],
            }
        ],
    }
    return json.dumps({"$schema": SARIF_SCHEMA, "version": "2.1.0", "runs": [run]}, indent=2, ensure_ascii=False) + "\n"
