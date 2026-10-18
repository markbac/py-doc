"""Finding and running generators."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING

from py_doc.errors import ConversionError

if TYPE_CHECKING:
    from py_doc.config import GeneratorSpec, ProjectConfig

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "py_doc.generators"
Generator = Callable[["GeneratorSpec", "ProjectConfig"], str]


class GeneratorError(ConversionError):
    """A generator could not make its Markdown. The message names the generator."""


def _builtins() -> dict[str, Generator]:
    from . import builtin

    return dict(builtin.GENERATORS)


def available() -> dict[str, Generator]:
    """Every generator type: the built-in ones, then those packages register under ``py_doc.generators``."""
    found = _builtins()
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name in found:
            logger.debug(f"The generator {entry.name} of {entry.value} is a built-in name, so it is not used")
            continue
        found[entry.name] = _lazy(entry)
    return found


def _lazy(entry) -> Generator:
    def run(spec, project):
        return entry.load()(spec, project)

    return run


def load_callable(target: str) -> Generator:
    """``package.module:function``."""
    module, _, name = target.partition(":")
    if not module or not name:
        raise GeneratorError(f"'{target}' is not module:function")
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError) as exc:
        raise GeneratorError(f"Cannot load the generator {target}: {exc}") from exc


def run_generators(project: ProjectConfig, names: list[str] | None = None) -> list[Path]:
    """Run the generators of ``project`` (or the ones named), in order. Returns the files that changed."""
    specs = project.generators
    if names:
        unknown = [name for name in names if name not in {spec.name for spec in specs}]
        if unknown:
            raise GeneratorError(f"Unknown generator(s): {', '.join(unknown)}. Defined: {', '.join(s.name for s in specs) or 'none'}")
        specs = [spec for spec in specs if spec.name in names]
    registry = available()
    changed: list[Path] = []
    for spec in specs:
        generate = load_callable(spec.options["callable"]) if spec.type == "python" else registry.get(spec.type)
        if generate is None:
            raise GeneratorError(f"content.generators: '{spec.name}' has the unknown type '{spec.type}'. Types: {', '.join(sorted(registry))}")
        logger.info(f"Generating {spec.name} ({spec.type})")
        try:
            text = generate(spec, project)
        except GeneratorError:
            raise
        except Exception as exc:  # a generator of someone else's must not hide where it failed
            raise GeneratorError(f"The generator {spec.name} ({spec.type}) failed: {type(exc).__name__}: {exc}") from exc
        if not isinstance(text, str):
            raise GeneratorError(f"The generator {spec.name} ({spec.type}) returned {type(text).__name__}, not Markdown text")
        text = text.rstrip() + "\n"
        old = spec.output.read_text(encoding="utf-8") if spec.output.is_file() else None
        if old != text:
            spec.output.parent.mkdir(parents=True, exist_ok=True)
            spec.output.write_text(text, encoding="utf-8", newline="\n")
            changed.append(spec.output)
            logger.info(f"Wrote {spec.output}")
    return changed
