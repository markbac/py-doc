"""``py-doc preview``: the live preview for editors, which writes nothing beside the Markdown."""

from __future__ import annotations

import io
import json
import queue
import re
import threading
import time
import urllib.request
from pathlib import Path

from py_doc import preview_cli
from py_doc.preview_cli import PREFIX, STALE, STOP, _read_requests, _remove_stale, preview


def _fake_build(calls):
    def build(kind, source, output):
        calls.append((kind, source))
        output.write_text(f"<html><body>{kind} {source.name}</body></html>", encoding="utf-8")
        return output

    return build


def _start(tmp_path, source, kind, requests, build):
    stop = threading.Event()
    result = {}
    thread = threading.Thread(
        target=lambda: result.setdefault(
            "code", preview(source, kind, requests, open_browser=False, build=build, stop=stop, interval=0.05)
        ),
        daemon=True,
    )
    thread.start()
    return stop, thread, result


def _wait(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def _get(address: str) -> str:
    with urllib.request.urlopen(address, timeout=5) as response:
        return response.read().decode("utf-8")


def test_preview_follows_files_and_writes_nothing_beside_them(tmp_path, capsys):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# A\n", encoding="utf-8")
    b.write_text("# B\n", encoding="utf-8")
    before = sorted(p.name for p in tmp_path.iterdir())
    calls: list = []
    requests: queue.Queue = queue.Queue()
    stop, thread, result = _start(tmp_path, a.resolve(), "document", requests, _fake_build(calls))

    assert _wait(lambda: len(calls) == 1)
    address = re.search(r"serving (http://\S+)", capsys.readouterr().out).group(1)
    assert _wait(lambda: "preview-document a.md" in _get(address))

    requests.put((b.resolve(), "slides"))  # moved to another file, by the same server
    assert _wait(lambda: "preview-deck b.md" in _get(address))
    requests.put((b.resolve(), "slides"))  # the same file again builds nothing
    time.sleep(0.2)
    assert len(calls) == 2

    time.sleep(0.05)
    b.write_text("# B again\n", encoding="utf-8")  # a save builds again
    assert _wait(lambda: len(calls) == 3)

    requests.put(STOP)
    thread.join(5)
    assert result["code"] == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # no .docx, no .py-doc


def test_a_failed_build_keeps_serving(tmp_path, capsys):
    source = tmp_path / "a.md"
    source.write_text("# A\n", encoding="utf-8")

    def broken(kind, path, output):
        raise RuntimeError("no luck")

    requests: queue.Queue = queue.Queue()
    stop, thread, result = _start(tmp_path, source.resolve(), "poster", requests, broken)
    assert _wait(lambda: "Error: no luck" in capsys.readouterr().out)
    stop.set()
    thread.join(5)
    assert result["code"] == 0


def test_requests_are_read_one_json_line_each_until_input_closes(tmp_path):
    requests: queue.Queue = queue.Queue()
    stream = io.StringIO(json.dumps({"file": str(tmp_path / "x.md"), "kind": "poster"}) + "\nnot json\n\n")
    _read_requests(stream, requests)
    assert requests.get_nowait() == ((tmp_path / "x.md").resolve(), "poster")
    assert requests.get_nowait() is STOP


def test_a_missing_file_is_an_error(tmp_path, capsys):
    assert preview_cli.run_preview([str(tmp_path / "missing.md"), "--no-open"]) == 1
    assert "Path not found" in capsys.readouterr().err


def test_py_doc_lists_the_command():
    from py_doc.app import _DELEGATES

    assert _DELEGATES["preview"][1] is preview_cli.run_preview
    assert Path(preview_cli.__file__).name == "preview_cli.py"


def test_folders_of_killed_previews_are_removed_once_old(tmp_path):
    old, new, other = tmp_path / f"{PREFIX}old", tmp_path / f"{PREFIX}new", tmp_path / "other"
    for folder in (old, new, other):
        folder.mkdir()
    now = old.stat().st_mtime + STALE + 60
    import os

    os.utime(new, (now, now))
    os.utime(other, (0, 0))
    _remove_stale(tmp_path, now=now)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([new.name, other.name])
