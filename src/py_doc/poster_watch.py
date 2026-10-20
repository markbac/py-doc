"""``py-doc poster --watch``: rebuild the posters on every save, and reload them in the browser.

The pages are served on a local address, each with a small script that asks the server every 0.7 s
whether a newer build is there, and reloads when it is. A build that fails keeps the last good page and
shows the error over it until the next save. The script is added as the page is served, so the files
written are the same as without ``--watch``.
"""

from __future__ import annotations

import html
import json
import logging
import os
import threading
import time
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger(__name__)

INTERVAL = 0.5  # seconds between two looks at the files
SKIPPED = {"node_modules", "__pycache__"}  # folders never watched, as are hidden ones
# The kinds of file a poster is made from: its Markdown, includes, pictures, data, diagram sources and fonts.
# Any other file in the folder, such as a log, is not watched, or writing it would build again without end.
SOURCES = {".md", ".markdown", ".yml", ".yaml", ".json", ".csv", ".txt", ".py", ".svg", ".png", ".jpg", ".jpeg",
           ".gif", ".webp", ".puml", ".iuml", ".plantuml", ".dot", ".gv", ".mmd", ".dsl", ".woff2", ".woff", ".ttf", ".otf"}  # fmt: skip

RELOAD = """<script>(function(){var seen=__VERSION__;
function poll(){fetch('/__status').then(function(r){return r.json();}).then(function(s){
  if(s.version!==seen){location.reload();return;}
  var bar=document.getElementById('py-doc-watch');
  if(s.error&&!bar){bar=document.createElement('div');bar.id='py-doc-watch';
    bar.style.cssText='position:fixed;left:0;right:0;top:0;z-index:99;background:#a3322b;color:#fff;font:15px/1.4 sans-serif;padding:10px 14px;white-space:pre-wrap';
    document.body.appendChild(bar);}
  if(bar){if(s.error){bar.textContent='The last save did not build: '+s.error;}else{bar.remove();}}
}).catch(function(){}).then(function(){setTimeout(poll,700);});}
poll();})();</script>"""

# What a build gives the watcher: the page of each poster, by name, and the files it was made from
Build = Callable[[], tuple[dict[str, Path], set[Path]]]


class State:
    """The pages being served, the build they are from, and the error of the last build, if it failed."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.pages: dict[str, Path] = {}
        self.version = 0
        self.error: str | None = None


def watched_files(folders: set[Path], files: set[Path], outputs: set[Path]) -> dict[Path, int]:
    """The modification time of every source file below ``folders``, and of ``files``, but not the ``outputs``."""
    found: dict[Path, int] = {}
    for folder in folders:
        for root, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIPPED]
            for name in names:
                path = Path(root, name)
                if path.suffix.lower() in SOURCES and path not in outputs:
                    found[path] = _mtime(path)
    for path in files:
        found[path] = _mtime(path)
    return found


def _mtime(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0  # a file that is gone counts as changed when it comes back


def serve(state: State, port: int) -> ThreadingHTTPServer:
    """A server on this computer only, for the pages of ``state``, in a thread of its own."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (the name http.server calls)
            path = self.path.split("?", 1)[0]
            with state.lock:
                pages, version, error = dict(state.pages), state.version, state.error
            if path == "/__status":
                return self._send(200, "application/json", json.dumps({"version": version, "error": error}))
            name = path.strip("/").removesuffix(".html")
            if not name and len(pages) == 1:
                name = next(iter(pages))
            if name in pages:
                page = pages[name].read_text(encoding="utf-8")
                script = RELOAD.replace("__VERSION__", str(version))
                return self._send(200, "text/html; charset=utf-8", page.replace("</body>", script + "</body>", 1))
            if not name:
                links = "".join(f'<li><a href="/{html.escape(n)}.html">{html.escape(n)}</a></li>' for n in pages)
                return self._send(200, "text/html; charset=utf-8", f"<!doctype html><title>Posters</title><ul>{links}</ul>")
            self._send(404, "text/plain", f"No poster {name}")

        def _send(self, code: int, kind: str, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args) -> None:
            pass  # one line a poll is noise

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def watch(build: Build, errors: tuple[type[Exception], ...], port: int = 0, open_browser: bool = True,
          stop: threading.Event | None = None, interval: float = INTERVAL) -> int:
    """Build, serve, and build again on every change, until Ctrl+C or ``stop``. Returns the exit status."""
    state, stop = State(), stop or threading.Event()

    def rebuild() -> set[Path]:
        started = time.monotonic()
        try:
            pages, sources = build()
        except errors as exc:
            print(f"Error: {exc}", flush=True)
            with state.lock:
                state.error = str(exc)
            return set()
        with state.lock:
            state.pages, state.error, state.version = pages, None, state.version + 1
        print(f"built in {time.monotonic() - started:.1f} s, watching for changes (Ctrl+C stops)", flush=True)
        return sources

    sources = rebuild()
    if not state.pages:
        return 1  # nothing to show: the first build failed

    def look() -> dict[Path, int]:
        with state.lock:
            outputs = set(state.pages.values())
        return watched_files({p.parent for p in sources if p.suffix.lower() in (".md", ".markdown")}, sources, outputs)

    seen = look()  # before the page is served, so no save made once it can be seen is missed
    server = serve(state, port)
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"serving {address}", flush=True)
    if open_browser:
        webbrowser.open(address)
    try:
        while not stop.wait(interval):
            now = look()
            if now != seen:
                changed = sorted(str(p) for p in now.keys() | seen.keys() if now.get(p) != seen.get(p))
                print(f"changed: {', '.join(changed[:3])}{' ...' if len(changed) > 3 else ''}", flush=True)
                seen = now  # as it was before this build, so a save while it runs builds again
                sources = rebuild() or sources
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0
