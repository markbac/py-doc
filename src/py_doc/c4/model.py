"""A Structurizr workspace as typed Python objects, read from the JSON that ``structurizr-cli export`` writes.

Only the fields py-doc uses are read, and a missing one is named in the error, because the format changes
between Structurizr releases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from py_doc.errors import ConversionError


class WorkspaceError(ConversionError):
    """The workspace JSON is not one py-doc can read."""


@dataclass
class Perspective:
    name: str
    description: str = ""
    value: str = ""


@dataclass
class Relationship:
    id: str
    source_id: str
    destination_id: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    linked_id: str | None = None  # the relationship an implied one comes from


@dataclass
class Element:
    id: str
    name: str
    kind: str = "element"
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    url: str = ""
    parent_id: str | None = None
    children: list["Element"] = field(default_factory=list)
    documentation: list["Section"] = field(default_factory=list)


class Person(Element):
    pass


class SoftwareSystem(Element):
    pass


class Container(Element):
    pass


class Component(Element):
    pass


class DeploymentNode(Element):
    environment: str = ""


class InfrastructureNode(Element):
    pass


class ContainerInstance(Element):
    element_id: str | None = None  # the container or system it is an instance of


KINDS = {
    "person": Person, "softwareSystem": SoftwareSystem, "container": Container, "component": Component,
    "deploymentNode": DeploymentNode, "infrastructureNode": InfrastructureNode, "containerInstance": ContainerInstance,
    "softwareSystemInstance": ContainerInstance,
}  # fmt: skip


@dataclass
class Step:
    order: str
    relationship_id: str
    description: str = ""


@dataclass
class View:
    key: str
    kind: str  # systemLandscape, systemContext, container, component, dynamic, deployment, filtered, image or custom
    title: str = ""
    description: str = ""
    scope_id: str | None = None
    environment: str = ""
    element_ids: list[str] = field(default_factory=list)
    relationship_ids: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)

    @property
    def heading(self) -> str:
        return self.title or self.key


@dataclass
class Section:
    title: str
    content: str
    format: str = "Markdown"
    order: int = 0


@dataclass
class Workspace:
    name: str
    description: str = ""
    elements: dict[str, Element] = field(default_factory=dict)
    roots: list[Element] = field(default_factory=list)  # people, software systems and deployment nodes, in file order
    relationships: list[Relationship] = field(default_factory=list)
    views: list[View] = field(default_factory=list)
    documentation: list[Section] = field(default_factory=list)
    decisions: list[Section] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    def of_kind(self, kind: type) -> list[Element]:
        return sorted((e for e in self.elements.values() if isinstance(e, kind)), key=lambda e: (e.name.lower(), e.id))

    def element(self, element_id: str) -> Element | None:
        return self.elements.get(element_id)

    def name_of(self, element_id: str) -> str:
        found = self.elements.get(element_id)
        return found.name if found else f"(unknown {element_id})"


_VIEW_KINDS = {
    "systemLandscapeViews": "systemLandscape", "systemContextViews": "systemContext", "containerViews": "container",
    "componentViews": "component", "dynamicViews": "dynamic", "deploymentViews": "deployment", "filteredViews": "filtered",
    "imageViews": "image", "customViews": "custom",
}  # fmt: skip


def _need(data: Any, key: str, where: str) -> Any:
    if not isinstance(data, dict) or key not in data:
        raise WorkspaceError(f"workspace JSON: {where} has no field '{key}'. The Structurizr format may have changed")
    return data[key]


def _tags(value: Any) -> list[str]:
    return sorted(t.strip() for t in str(value or "").split(",") if t.strip())


def _props(value: Any) -> dict[str, str]:
    """User properties. Structurizr's own bookkeeping (``structurizr.dsl.identifier`` and the like) is not for readers."""
    return {str(k): str(v) for k, v in sorted((value or {}).items()) if not str(k).startswith("structurizr.")}


def _sections(items: Any) -> list[Section]:
    return [
        Section(
            str(s.get("title") or ""),
            str(s.get("content") or ""),
            str(s.get("format") or "Markdown"),
            int(s.get("order") or 0),
        )
        for s in sorted(items or [], key=lambda s: int(s.get("order") or 0))
    ]


def _relationships(data: dict, where: str) -> list[Relationship]:
    found = []
    for number, raw in enumerate(data.get("relationships") or []):
        place = f"{where}.relationships[{number}]"
        found.append(
            Relationship(
                str(_need(raw, "id", place)), str(_need(raw, "sourceId", place)), str(_need(raw, "destinationId", place)),
                str(raw.get("description") or ""), str(raw.get("technology") or ""), _tags(raw.get("tags")),
                _props(raw.get("properties")), str(raw["linkedRelationshipId"]) if raw.get("linkedRelationshipId") else None,
            )
        )  # fmt: skip
    return found


def _element(raw: dict, kind: str, where: str, parent: Element | None, ws: Workspace) -> Element:
    instance = kind in ("containerInstance", "softwareSystemInstance")
    target = str(raw.get("containerId") or raw.get("softwareSystemId") or "")
    element = KINDS[kind](
        id=str(_need(raw, "id", where)),
        name=str(raw.get("name") or ws.name_of(target)) if instance else str(_need(raw, "name", where)),
        kind=kind,
        description=str(raw.get("description") or ""),
        technology=str(raw.get("technology") or ""),
        tags=_tags(raw.get("tags")),
        properties=_props(raw.get("properties")),
        perspectives=[
            Perspective(str(p.get("name") or ""), str(p.get("description") or ""), str(p.get("value") or ""))
            for p in raw.get("perspectives") or []
        ],
        url=str(raw.get("url") or ""),
        parent_id=parent.id if parent else None,
    )
    if isinstance(element, DeploymentNode):
        element.environment = str(raw.get("environment") or "")
    if isinstance(element, ContainerInstance):
        element.element_id = target or None
    element.documentation = _sections((raw.get("documentation") or {}).get("sections"))
    ws.elements[element.id] = element
    ws.relationships.extend(_relationships(raw, where))
    if parent:
        parent.children.append(element)
    return element


def workspace_from_dict(data: dict) -> Workspace:
    """Build a :class:`Workspace`. Raises :class:`WorkspaceError`, naming the missing field."""
    if not isinstance(data, dict):
        raise WorkspaceError("workspace JSON must be an object")
    model = _need(data, "model", "workspace")
    ws = Workspace(
        name=str(data.get("name") or "Workspace"), description=str(data.get("description") or ""),
        properties=_props(data.get("properties")),
    )  # fmt: skip

    for n, raw in enumerate(model.get("people") or []):
        ws.roots.append(_element(raw, "person", f"model.people[{n}]", None, ws))
    for n, raw in enumerate(model.get("softwareSystems") or []):
        system = _element(raw, "softwareSystem", f"model.softwareSystems[{n}]", None, ws)
        ws.roots.append(system)
        for m, c in enumerate(raw.get("containers") or []):
            container = _element(c, "container", f"model.softwareSystems[{n}].containers[{m}]", system, ws)
            for k, comp in enumerate(c.get("components") or []):
                _element(
                    comp, "component", f"model.softwareSystems[{n}].containers[{m}].components[{k}]", container, ws
                )

    def deployment(raw: dict, where: str, parent: Element | None) -> None:
        node = _element(raw, "deploymentNode", where, parent, ws)
        if parent is None:
            ws.roots.append(node)
        for k, infra in enumerate(raw.get("infrastructureNodes") or []):
            _element(infra, "infrastructureNode", f"{where}.infrastructureNodes[{k}]", node, ws)
        for k, inst in enumerate(raw.get("containerInstances") or []):
            _element(inst, "containerInstance", f"{where}.containerInstances[{k}]", node, ws)
        for k, inst in enumerate(raw.get("softwareSystemInstances") or []):
            _element(inst, "softwareSystemInstance", f"{where}.softwareSystemInstances[{k}]", node, ws)
        for k, child in enumerate(raw.get("children") or []):
            deployment(child, f"{where}.children[{k}]", node)

    for n, raw in enumerate(model.get("deploymentNodes") or []):
        deployment(raw, f"model.deploymentNodes[{n}]", None)

    for group, kind in _VIEW_KINDS.items():
        for n, raw in enumerate((data.get("views") or {}).get(group) or []):
            where = f"views.{group}[{n}]"
            view = View(
                key=str(_need(raw, "key", where)), kind=kind, title=str(raw.get("title") or ""),
                description=str(raw.get("description") or ""),
                scope_id=str(raw.get("softwareSystemId") or raw.get("containerId") or "") or None,
                environment=str(raw.get("environment") or ""),
                element_ids=[str(e["id"]) for e in raw.get("elements") or [] if "id" in e],
                relationship_ids=[str(r["id"]) for r in raw.get("relationships") or [] if "id" in r],
            )  # fmt: skip
            if kind == "dynamic":
                view.steps = [
                    Step(str(r.get("order") or ""), str(r["id"]), str(r.get("description") or ""))
                    for r in raw.get("relationships") or []
                    if "id" in r
                ]
            ws.views.append(view)
    ws.views.sort(key=lambda v: v.key)
    ws.documentation = _sections((data.get("documentation") or {}).get("sections"))
    ws.decisions = [
        Section(str(d.get("title") or ""), str(d.get("content") or ""), str(d.get("format") or "Markdown"), 0)
        for d in (data.get("documentation") or {}).get("decisions") or []
    ]
    return ws


def load_workspace(path: Path) -> Workspace:
    """Read a ``workspace.json`` file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkspaceError(f"Cannot read '{path}': {exc.strerror or exc}") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"'{path}' is not JSON: {exc.msg} at line {exc.lineno}") from exc
    return workspace_from_dict(data)
