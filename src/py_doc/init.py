"""``py-doc init``: start a documentation project.

It writes a ``py-doc.yml`` with a comment on every setting, a first document, and ``.gitignore`` lines, and,
when asked, a C4 model with a document generated from it, Word and PowerPoint templates and a site project.
It never replaces a file: one that is there is kept and named, and a folder that already has a
``py-doc.yml`` is refused.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from ._logging import configure_logging
from .config import CONFIG_NAMES, SITE_ENGINES, ConfigError, load_config, parse_config
from .errors import ConversionError, EnvironmentProblem, exit_status
from .runtime import Mount, connect

logger = logging.getLogger(__name__)

IGNORED = ("build/", ".py-doc/", ".structurizr/")


@dataclass
class Choices:
    name: str
    site: str | None = None  # mkdocs, starlight or None
    c4: bool = False
    templates: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc init", description="Start a documentation project: py-doc.yml, a first document and more")
    parser.add_argument("folder", nargs="?", default=".", type=Path, help="Where to make it (default: here)")
    parser.add_argument("--name", help="The project name (default: the folder name)")
    parser.add_argument("--site", choices=(*SITE_ENGINES, "none"), help="Also make a web site project")
    parser.add_argument("--c4", action="store_true", default=None, help="Also make a Structurizr C4 model and a document from it")
    parser.add_argument("--templates", action="store_true", default=None, help="Also write Word and PowerPoint templates (needs the tool container)")
    parser.add_argument("-y", "--yes", action="store_true", help="Ask nothing: take the defaults for what is not given")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    return parser


def _ask(question: str, default: str, ask: Callable[[str], str]) -> str:
    answer = ask(f"{question} [{default}]: ").strip()
    return answer or default


def _yes(question: str, ask: Callable[[str], str]) -> bool:
    return _ask(question, "n", ask).lower() in ("y", "yes")


def choose(args: argparse.Namespace, folder: Path, ask: Callable[[str], str] | None) -> Choices:
    """What to make: the options given, then answers to questions (when ``ask`` is given), then the defaults."""
    name = args.name or (_ask("Project name", folder.resolve().name, ask) if ask else folder.resolve().name)
    site = args.site
    if site is None and ask:
        site = _ask(f"Web site ({', '.join(SITE_ENGINES)} or none)", "none", ask).lower()
        while site not in (*SITE_ENGINES, "none"):
            site = _ask(f"Web site: {', '.join(SITE_ENGINES)} or none", "none", ask).lower()
    c4 = args.c4 if args.c4 is not None else (_yes("A C4 architecture model (Structurizr)?", ask) if ask else False)
    templates = args.templates if args.templates is not None else (_yes("Word and PowerPoint templates?", ask) if ask else False)
    return Choices(name, None if site in (None, "none") else site, c4, templates)


def project_files(choices: Choices) -> dict[str, str]:
    """The text files of a new project, by path below its folder."""
    files = {"py-doc.yml": config_text(choices), "docs/overview.md": OVERVIEW.format(name=choices.name)}
    if choices.c4:
        files["architecture/workspace.dsl"] = WORKSPACE.format(name=choices.name)
        files["docs/architecture-intro.md"] = ARCHITECTURE_INTRO
    return files


def config_text(choices: Choices) -> str:
    text = CONFIG.format(name=choices.name)
    if choices.templates:
        text = text.replace("    # template: templates/reference.docx", "    template: templates/reference.docx")
        text = text.replace("    # template: templates/reference.pptx", "    template: templates/reference.pptx")
    if choices.c4:
        text = text.replace("\n# A JSON report", "\n" + ARCHITECTURE_DOC.replace("{name}", choices.name) + "# A JSON report", 1)
    if choices.site:
        text += SITE.format(engine=choices.site)
    return text


def make_project(folder: Path, choices: Choices, runtime=connect) -> list[Path]:
    """Write the project. Returns the files written or extended. Raises ConversionError if one is there already."""
    folder = Path(folder)
    for name in CONFIG_NAMES:
        if (folder / name).exists():
            raise ConversionError(f"{folder / name} is already there: this folder is a py-doc project. Nothing was changed")
    files = project_files(choices)
    try:  # a configuration that would not load is a bug: say so before anything is written
        parse_config(yaml.safe_load(files["py-doc.yml"]), folder.resolve())
    except (ConfigError, yaml.YAMLError) as exc:
        raise ConversionError(f"The new py-doc.yml would not load: {exc}") from exc
    written: list[Path] = []
    for name, text in files.items():
        path = folder / name
        if path.exists():
            logger.warning(f"Kept {path}: it is already there")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    gitignore = _gitignore(folder)
    if gitignore:
        written.append(gitignore)
    if choices.templates:
        written += _templates(folder, runtime)
    if choices.site:
        from .site import engine_for

        config = load_config(folder / "py-doc.yml")
        written += engine_for(choices.site, config.site.dir).scaffold(config.site.title or choices.name)
    return written


def _gitignore(folder: Path) -> Path | None:
    path = folder / ".gitignore"
    have = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    missing = [line for line in IGNORED if line not in have]
    if not missing:
        return None
    lead = "\n" if have and have[-1].strip() else ""
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(lead + "# py-doc: built files and caches\n" + "\n".join(missing) + "\n")
    return path


def _templates(folder: Path, runtime) -> list[Path]:
    """pandoc's own reference documents, with py-doc's callout styles in the Word one."""
    from .pandoc.reference import default_reference

    target = folder / "templates"
    wanted = [target / "reference.docx", target / "reference.pptx"]
    if all(path.exists() for path in wanted):
        return []
    try:
        box = runtime()
    except EnvironmentProblem as exc:
        logger.warning(f"The templates were not written, because the tool container is not available: {exc}")
        return []
    target.mkdir(parents=True, exist_ok=True)
    written = []
    with tempfile.TemporaryDirectory(prefix="py-doc-init-") as tmp:
        work = Path(tmp)
        if not wanted[0].exists():
            wanted[0].write_bytes(default_reference(box, work).read_bytes())
            written.append(wanted[0])
        if not wanted[1].exists():
            made = work / "reference.pptx"
            box.run(["pandoc", "-o", made, "--print-default-data-file", "reference.pptx"], mounts=[Mount(work, writable=True)], workdir=work)
            wanted[1].write_bytes(made.read_bytes())
            written.append(wanted[1])
    return written


def run_init(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 made, 1 the folder is a project already or a file cannot be written."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    ask = None if args.yes or not sys.stdin.isatty() else input
    folder = args.folder
    try:
        choices = choose(args, folder, ask)
        written = make_project(folder, choices)
    except (ConversionError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc) if isinstance(exc, ConversionError) else 1
    except OSError as exc:
        print(f"Error: cannot write in {folder}: {exc.strerror or exc}", file=sys.stderr)
        return 1
    for path in written:
        print(f"written   {path}")
    steps = ["py-doc lint docs", "py-doc build"]
    if choices.c4:
        steps.append("py-doc c4 up architecture/workspace.dsl")
    if choices.site:
        steps.append("py-doc site build")
    where = "" if folder.resolve() == Path.cwd().resolve() else f"cd {folder}\n"
    print("\nNext:\n" + where + "\n".join(steps))
    return 0


CONFIG = """\
# py-doc project: `py-doc build` builds every document below, `py-doc lint docs` checks the writing.
# Every key is checked when the file loads, so a typo is an error that names its place. Paths are
# relative to this file. The README of py-doc lists every setting.

project:
  name: {name}

# Defaults for every document. A document's own `outputs` override them.
outputs:
  docx:
    dir: build
    # template: templates/reference.docx   # a Word file whose styles the document takes
  pptx:
    dir: build
    # template: templates/reference.pptx   # a PowerPoint file whose layouts the slides take
  pdf:
    dir: build
  html:
    dir: build

documents:
  overview:
    # The front matter of the first source gives the title, author, version and status.
    sources:
      - docs/overview.md
    outputs:
      docx: {{toc: true}}   # build/overview.docx, with a contents list
      html: {{}}            # build/overview.html

# A JSON report of every build: tools and versions, sources, outputs with SHA-256, diagrams.
reports:
  path: build/report.json

lint:
  exclude: [build]
  rules: {{}}           # for example DOC003: info, or DOC001: off
  glossary: {{}}        # the right spelling, then the wrong ones: {{MQTT: [mqtt, Mqtt]}}
  acronyms:
    min_length: 3
"""

ARCHITECTURE_DOC = """\
  architecture:
    # Chapters generated from the C4 model, after a hand-written introduction.
    # `py-doc c4 up architecture/workspace.dsl` opens the model in Structurizr to arrange its views.
    title: {name} architecture
    sources:
      - docs/architecture-intro.md
      - structurizr: architecture/workspace.dsl
        heading_offset: 1
        diagrams: {engine: browser, format: png}
    outputs:
      docx: {}
      html: {}

"""

SITE = """
# A web site of the documents: `py-doc site build`. The site project lives in site/.
site:
  engine: {engine}
  dir: site
"""

OVERVIEW = """\
---
title: {name} overview
author: Your Name
version: "0.1"
status: Draft
---

# Overview

One paragraph that says what this document is for and who reads it.

## Scope

What the document covers, and what it leaves to other documents.

> [!NOTE]
> Callouts come in five kinds: note, tip, important, warning and caution.

## How it works

[[CAPTION:Figure]] The parts and how they talk
```mermaid
flowchart LR
  user[User] --> app[Application] --> store[(Store)]
```
"""

ARCHITECTURE_INTRO = """\
---
title: Architecture introduction
---

# Introduction

This document describes the architecture. py-doc writes the chapters after this one from the C4 model in
`architecture/workspace.dsl`, so change the model, not the chapters.
"""

WORKSPACE = """\
workspace "{name}" "The C4 model of {name}." {{
    model {{
        user = person "User" "Uses the system."
        system = softwareSystem "{name}" "What the system does." {{
            app = container "Application" "Does the work." "Python"
            store = container "Store" "Keeps the data." "PostgreSQL" "Database"
        }}
        user -> app "Uses"
        app -> store "Reads and writes"
    }}
    views {{
        systemContext system "Context" {{
            include *
            autoLayout lr
        }}
        container system "Containers" {{
            include *
            autoLayout lr
        }}
        styles {{
            element "Database" {{
                shape cylinder
            }}
        }}
    }}
}}
"""
