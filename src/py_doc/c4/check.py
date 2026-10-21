"""Rules for the model itself: elements, containers and relationships that lack the text a document needs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from py_doc.lint.config import LintConfig

from .model import Container, Person, SoftwareSystem, Workspace

RULES = {
    "C4001": ("warning", "Element without a description"),
    "C4002": ("warning", "Container without a technology"),
    "C4003": ("warning", "Relationship without a description"),
    "C4004": ("info", "Element with no relationships"),
}  # fmt: skip


@dataclass(frozen=True)
class ModelIssue:
    file: Path
    rule: str
    severity: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}: {self.severity} {self.rule} {self.message}"


def check_model(ws: Workspace, file: Path, config: LintConfig | None = None) -> list[ModelIssue]:
    """Issues in the model, with the severities of ``lint.rules`` (a rule set to ``off`` is skipped)."""
    config = config or LintConfig()

    def issue(rule: str, message: str) -> ModelIssue | None:
        if rule in config.disabled_rules:
            return None
        return ModelIssue(file, rule, config.severities.get(rule, RULES[rule][0]), message)

    found: list[ModelIssue | None] = []
    used = {r.source_id for r in ws.relationships} | {r.destination_id for r in ws.relationships}
    for element in ws.elements.values():
        if element.kind.endswith("Instance") or element.kind in ("deploymentNode", "infrastructureNode"):
            continue
        if not element.description:
            found.append(issue("C4001", f"{element.kind} '{element.name}' has no description"))
        if isinstance(element, Container) and not element.technology:
            found.append(issue("C4002", f"container '{element.name}' has no technology"))
        top_level = isinstance(element, (Person, SoftwareSystem))
        if top_level and element.id not in used and not any(c.id in used for c in element.children):
            found.append(issue("C4004", f"{element.kind} '{element.name}' has no relationships"))
    for rel in ws.relationships:
        if rel.linked_id is None and not rel.description:
            found.append(
                issue(
                    "C4003",
                    f"the relationship from '{ws.name_of(rel.source_id)}' to '{ws.name_of(rel.destination_id)}' has no description",
                )
            )
    return sorted((i for i in found if i), key=lambda i: (i.rule, i.message))
