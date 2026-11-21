"""One Markdown file to one output, for the web page.

    python -m py_doc.web.render KIND SOURCE OUTPUT    one file, then exit
    python -m py_doc.web.render --serve               a worker: one request a line on stdin, until it closes

The kinds are what the page offers for a single file:

- ``docx``, ``pptx``, ``pdf`` and ``html``: the document as ``py-doc build`` writes it
- ``deck``: the slides as one self-contained HTML deck
- ``poster``: the file as an HTML poster
- ``preview-document``, ``preview-deck`` and ``preview-poster``: the HTML pages the live preview shows

A file that is part of a project is built with the project's settings: the variables, conditions and Mermaid
settings of the document in py-doc.yml whose sources list it, or a poster's entry under ``posters:``, as
``py-doc build`` and ``py-doc poster`` would.

The worker keeps Python, py-doc and the tool container connection between previews, so a preview starts at
once rather than after a second or two of starting up. It runs apart from the server, so a stuck build can
be stopped without taking the server with it.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("docx", "pptx", "pdf", "html", "deck", "poster", "preview-document", "preview-deck", "preview-poster")
REPLY = "@@py-doc-render@@ "  # a worker's answer is the one line that starts with this

logger = logging.getLogger(__name__)
_connected: list = []


def _runtime():
    """The tool container runtime, connected once and kept: the worker reuses it for every preview."""
    if not _connected:
        from py_doc.runtime import connect

        _connected.append(connect())
    return _connected[0]


@dataclass
class Context:
    """What py-doc.yml says about one file."""

    variables: dict = field(default_factory=dict)
    conditions: dict = field(default_factory=dict)
    mermaid: dict | None = None
    poster: dict | None = None  # the poster's own settings, when it is listed under posters:
    poster_defaults: dict = field(default_factory=dict)  # poster: of py-doc.yml, for every poster


def context(source: Path) -> Context:
    """The settings py-doc.yml gives ``source``: those of the document that lists it, else the variables and
    conditions of every document (the first that sets one wins), so a preview of a file that is only
    included somewhere still builds."""
    from py_doc.config import find_config, load_config

    found = Context()
    config_path = find_config(source.parent)
    if config_path is None:
        return found
    project = load_config(config_path)
    found.mermaid = project.mermaid or None
    found.poster_defaults = project.poster or {}
    target = source.resolve()
    for poster in project.posters.values():
        if poster.source.resolve() == target:
            found.poster = poster.settings
    owners = [d for d in project.documents.values() if any(s.file and s.file.resolve() == target for s in d.sources)]
    for document in owners or list(project.documents.values()):
        for key, value in document.variables.items():
            found.variables.setdefault(key, value)
        for key, value in document.conditions.items():
            found.conditions.setdefault(key, value)
    return found


def render(kind: str, source: Path, output: Path) -> Path:
    from py_doc.convert import DeckConverter, DocxConverter, SlidesConverter

    output.parent.mkdir(parents=True, exist_ok=True)
    settings = context(source)
    if kind in ("poster", "preview-poster"):
        from py_doc.poster import write_poster

        write_poster(source, output, _runtime, settings.poster, settings.poster_defaults, pdf=False,
                     mermaid=settings.mermaid)  # fmt: skip
        return output
    project = {"variables": settings.variables, "conditions": settings.conditions, "mermaid": settings.mermaid}
    if kind == "docx":
        return DocxConverter(runtime=_runtime, **project).convert_file(source, output)
    if kind == "pptx":
        return SlidesConverter(runtime=_runtime, **project).convert_file(source, output)
    if kind == "deck":
        return DeckConverter(runtime=_runtime, **project).convert_file(source, output)
    if kind in ("pdf", "html"):
        converter = DocxConverter(runtime=_runtime, **project)
        return converter._render(source, output, kind, None, converter.options)
    if kind == "preview-document":
        return DocxConverter(runtime=_runtime, **project).convert_twin(source, output)
    if kind == "preview-deck":
        return SlidesConverter(runtime=_runtime, **project).convert_twin(source, output)
    raise ValueError(f"Unknown kind {kind!r}; one of {', '.join(KINDS)}")


def serve(requests=None, replies=None, build=render) -> int:
    """Answer requests until the input closes. Each request is a JSON line ``{"kind", "source", "output"}``;
    each answer a line of REPLY and JSON ``{"ok", "log"}``, with what the build printed and logged."""
    requests = requests or sys.stdin
    replies = replies or sys.stdout
    for line in requests:
        if not line.strip():
            continue
        captured = io.StringIO()
        handler = logging.StreamHandler(captured)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        ok = False
        try:
            request = json.loads(line)
            with contextlib.redirect_stdout(captured):
                written = build(request["kind"], Path(request["source"]).resolve(), Path(request["output"]).resolve())
            captured.write(f"wrote {written}\n")
            ok = True
        except Exception as exc:  # the message is what the page shows; the worker goes on
            captured.write(f"Error: {exc}\n")
        finally:
            root.removeHandler(handler)
        replies.write(REPLY + json.dumps({"ok": ok, "log": captured.getvalue()}) + "\n")
        replies.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--serve"]:
        logging.getLogger().setLevel(logging.INFO)
        return serve()
    if len(args) != 3 or args[0] not in KINDS:
        print(f"usage: python -m py_doc.web.render {{{','.join(KINDS)}}} SOURCE OUTPUT", file=sys.stderr)
        print("       python -m py_doc.web.render --serve", file=sys.stderr)
        return 2
    from py_doc._logging import configure_logging
    from py_doc.errors import exit_status

    configure_logging(quiet=False, verbose=False)
    try:
        written = render(args[0], Path(args[1]).resolve(), Path(args[2]).resolve())
    except Exception as exc:  # the message is what the page shows
        print(f"Error: {exc}", file=sys.stderr, flush=True)
        return exit_status(exc) or 1
    print(f"wrote {written}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
