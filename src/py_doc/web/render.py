"""One Markdown file to one output, for the web page: ``python -m py_doc.web.render KIND SOURCE OUTPUT``.

The kinds are what the page offers for a single file:

- ``docx``, ``pptx``, ``pdf`` and ``html``: the document as ``py-doc build`` writes it
- ``deck``: the slides as one self-contained HTML deck
- ``poster``: the file as an HTML poster
- ``preview-document`` and ``preview-deck``: the HTML twins that ``--watch`` shows

It runs as a process of its own, as the command line does, so a long or stuck build can be stopped
without taking the server with it.
"""

from __future__ import annotations

import sys
from pathlib import Path

KINDS = ("docx", "pptx", "pdf", "html", "deck", "poster", "preview-document", "preview-deck", "preview-poster")


def render(kind: str, source: Path, output: Path) -> Path:
    from py_doc.convert import DeckConverter, DocxConverter, SlidesConverter

    output.parent.mkdir(parents=True, exist_ok=True)
    if kind in ("poster", "preview-poster"):
        from py_doc.poster import write_poster
        from py_doc.runtime import connect

        connected = []

        def runtime():
            if not connected:
                connected.append(connect())
            return connected[0]

        write_poster(source, output, runtime, pdf=False)
        return output
    if kind == "docx":
        return DocxConverter().convert_file(source, output)
    if kind == "pptx":
        return SlidesConverter().convert_file(source, output)
    if kind == "deck":
        return DeckConverter().convert_file(source, output)
    if kind in ("pdf", "html"):
        converter = DocxConverter()
        return converter._render(source, output, kind, None, converter.options)
    if kind == "preview-document":
        return DocxConverter().convert_twin(source, output)
    if kind == "preview-deck":
        return SlidesConverter().convert_twin(source, output)
    raise ValueError(f"Unknown kind {kind!r}; one of {', '.join(KINDS)}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] not in KINDS:
        print(f"usage: python -m py_doc.web.render {{{','.join(KINDS)}}} SOURCE OUTPUT", file=sys.stderr)
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
