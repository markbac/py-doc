"""``py-doc preview``: the live preview of one Markdown file, for an editor beside it.

    py-doc preview guide.md                    the guide as a document, reloaded in the browser on every save
    py-doc preview deck.md --kind slides       as a slide deck
    py-doc preview guide.md --stdin --no-open  for an editor: the next file to show comes on standard input

It is ``--watch`` without the outputs. Only the preview page is written, to a folder of the system's
temporary files that is removed when the preview stops, so nothing is left beside the Markdown: no .docx,
no .pptx and no ``.py-doc/preview``.

Python, py-doc and the tool container connection are kept between builds, and the server keeps running
when the file changes, so following the editor to another file is one build, not a start of py-doc.
The address is printed (``serving http://...``) before the first build, and the page reloads once it is built.

With ``--stdin``, each line of standard input is a JSON object ``{"file": PATH, "kind": KIND}`` that moves
the preview to that file, and the preview stops when standard input closes, as when the editor goes.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import queue
import shutil
import sys
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path

from ._cli import safe_console
from ._logging import configure_logging

logger = logging.getLogger(__name__)

# The kind asked for, and the page of py-doc.web.render that previews it
KINDS = {
    "document": "preview-document",
    "docx": "preview-document",
    "deck": "preview-deck",
    "slides": "preview-deck",
    "poster": "preview-poster",
}
STOP = object()  # standard input closed
PREFIX = "py-doc-preview-"
STALE = 12 * 3600  # seconds: the folder of a preview that was killed, and so could not remove it, goes after this

WAITING = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<body style="font:15px/1.5 sans-serif;color:#555;padding:24px">Building the preview of {name} ...</body>"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-doc preview",
        description="Live preview of one Markdown file as a document, deck or poster, without writing its outputs",
    )
    parser.add_argument("input", help="The Markdown file")
    parser.add_argument(
        "-k", "--kind", choices=sorted(KINDS), default="document",
        help="What to preview it as (default: document); docx and slides are the same as document and deck",
    )  # fmt: skip
    parser.add_argument("--port", type=int, default=0, help="The local port to serve on (default: a free one)")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser (or a Wave pane)")
    from .wave import add_options

    add_options(parser, with_watch=False)
    parser.add_argument(
        "--stdin", action="store_true",
        help='Read the next file to show from standard input, a JSON line {"file": PATH, "kind": KIND} each, '
        "and stop when it closes",
    )  # fmt: skip
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug output")
    return parser


def run_preview(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    source = Path(args.input).resolve()
    if not source.is_file():
        print(f"Error: Path not found: {source}", file=sys.stderr, flush=True)
        return 1
    requests: queue.Queue = queue.Queue()
    if args.stdin:
        threading.Thread(target=_read_requests, args=(sys.stdin, requests), daemon=True, name="preview-stdin").start()
    return preview(source, args.kind, requests, port=args.port, open_browser=not args.no_open, wave=args.wave)


def _read_requests(stream, requests: queue.Queue) -> None:
    """Put each file asked for on ``requests``, and STOP when ``stream`` closes."""
    try:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                requests.put((Path(request["file"]).resolve(), request.get("kind") or "document"))
            except (ValueError, KeyError, TypeError) as exc:
                print(f"Error: not a preview request: {line} ({exc})", flush=True)
    finally:
        requests.put(STOP)


def preview(
    source: Path,
    kind: str,
    requests: queue.Queue,
    port: int = 0,
    open_browser: bool = True,
    build=None,
    stop: threading.Event | None = None,
    interval: float | None = None,
    wave: bool | None = None,
) -> int:
    """Serve the preview of ``source``, build it again on every change, and move it to each file on
    ``requests``, until STOP comes, ``stop`` is set, or Ctrl+C. ``build(kind, source, output)`` is
    py_doc.web.render's own unless a test gives another."""
    from .watch import INTERVAL, State, serve, watched_files

    if build is None:
        from .web.render import render as build
    stop = stop or threading.Event()
    interval = INTERVAL if interval is None else interval
    _remove_stale(Path(tempfile.gettempdir()))
    folder = Path(tempfile.mkdtemp(prefix=PREFIX))
    page = folder / "preview.html"
    partial = folder / "preview.building.html"
    page.write_text(WAITING.format(title="py-doc preview", name=html.escape(source.name)), encoding="utf-8")
    state = State(title="py-doc preview")
    state.pages = {"preview": page}

    server = serve(state, port)
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"serving {address}", flush=True)  # at once: the page shows its first build when it is done
    from .wave import show

    show(address, open_browser=open_browser, wave=wave)  # once: moving to another file keeps the page and its pane

    def watched(target: Path) -> tuple[set[Path], set[Path]]:
        from .config import find_config

        config = find_config(target.parent)
        return {target.parent}, {target, *([config] if config else [])}

    def rebuild(target: Path, wanted: str) -> None:
        started = time.monotonic()
        try:
            if wanted not in KINDS:
                raise ValueError(f"Unknown kind {wanted!r}; one of {', '.join(sorted(KINDS))}")
            if not target.is_file():
                raise FileNotFoundError(f"{target.name} is no longer there")
            build(KINDS[wanted], target, partial)
            os.replace(partial, page)  # whole, so a reload never shows half a page
        except Exception as exc:  # shown over the last good page until the next save; the preview goes on
            print(f"Error: {exc}", flush=True)
            with state.lock:
                state.error = str(exc)
            return
        with state.lock:
            state.error, state.version = None, state.version + 1
        print(f"built {target.name} in {time.monotonic() - started:.1f} s, watching for changes", flush=True)

    try:
        folders, files = watched(source)
        seen = watched_files(folders, files, {page, partial})
        rebuild(source, kind)
        while not stop.is_set():
            asked = None
            try:
                while True:  # the last file asked for wins: a quick run of tab switches builds once
                    item = requests.get(timeout=interval) if asked is None else requests.get_nowait()
                    if item is STOP:
                        return 0
                    asked = item
            except queue.Empty:
                pass
            if asked is not None and asked != (source, kind):
                source, kind = asked
                print(f"previewing {source}", flush=True)
                folders, files = watched(source)
                seen = watched_files(folders, files, {page, partial})
                rebuild(source, kind)
                continue
            now = watched_files(folders, files, {page, partial})
            if now != seen:
                changed = sorted(str(p) for p in now.keys() | seen.keys() if now.get(p) != seen.get(p))
                print(f"changed: {', '.join(changed[:3])}{' ...' if len(changed) > 3 else ''}", flush=True)
                seen = now  # as it was before this build, so a save while it runs builds again
                rebuild(source, kind)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(folder, ignore_errors=True)
    return 0


def _remove_stale(temp: Path, now: float | None = None) -> None:
    """Remove the folders of previews that were killed rather than stopped, once they are old."""
    now = time.time() if now is None else now
    for folder in temp.glob(PREFIX + "*"):
        try:
            if folder.is_dir() and now - folder.stat().st_mtime > STALE:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass


def main() -> None:
    safe_console()
    sys.exit(run_preview())


if __name__ == "__main__":
    main()
