"""Wave Terminal: the live preview in a Wave pane, the sidebar widget, and what ``py-doc doctor`` says about it.

    py-doc docx guide.md --watch          inside Wave, the preview opens in a pane beside the terminal
    py-doc docx guide.md --watch --wave   the same, also when py-doc cannot tell it is inside Wave
    py-doc preview guide.md --no-wave     the browser, as outside Wave
    py-doc wave widget                    print the sidebar widget, to add to Wave's widgets.json
    py-doc wave widget --install          add it, or bring it up to date; other widgets are kept
    py-doc wave pick                      what the widget runs: choose a Markdown file, and preview it

Wave (https://www.waveterm.dev/) shows a web page in a pane of its own with ``wsh web open URL``. The
preview server already serves the page that reloads on every save, so the pane only needs its address.

Inside Wave, a terminal has ``TERM_PROGRAM=waveterm`` and ``WAVETERM`` set. ``wsh web open`` prints
``created block <ORef>``; that block is remembered for the Wave tab, so the next preview in the same tab
replaces it (``wsh web open -r <ORef>``) instead of opening another pane each time.

Where the address works:

- Windows: py-doc and Wave on the same PC, so 127.0.0.1 is the same.
- WSL: WSL 2 forwards a port of 127.0.0.1 in the distribution to the PC's 127.0.0.1 (its default,
  ``localhostForwarding``), so the pane can show it.
- SSH: 127.0.0.1 is the remote machine, which Wave's window cannot reach. py-doc says so, prints the
  address and the port forward that shows it, and does not open a blank pane.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

OFF_VARIABLE = "PY_DOC_NO_WAVE"  # set to 1 (or true, yes): the browser, even inside Wave
WIDGET_NAME = "py-doc-preview"  # its key in widgets.json
TIMEOUT = 10  # seconds wsh may take to answer
SKIPPED = {"node_modules", "__pycache__", "site", "build", "dist"}  # folders the picker does not look in
MOST = 40  # Markdown files the picker lists

Run = Callable[..., subprocess.CompletedProcess]


# ---------------------------------------------------------------------------
# Where py-doc runs
# ---------------------------------------------------------------------------


def inside_wave(env: Mapping[str, str] | None = None) -> bool:
    """Whether this process runs in a Wave Terminal pane."""
    env = os.environ if env is None else env
    return env.get("TERM_PROGRAM", "").lower() == "waveterm" or bool(env.get("WAVETERM"))


def over_ssh(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("SSH_CONNECTION") or env.get("SSH_CLIENT") or env.get("SSH_TTY"))


def in_wsl(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("WSL_DISTRO_NAME") or env.get("WSL_INTEROP"))


def switched_off(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get(OFF_VARIABLE, "").strip().lower() in ("1", "true", "yes", "on")


def find_wsh(env: Mapping[str, str] | None = None, which: Callable[[str], str | None] | None = None) -> str | None:
    """The wsh command: on the PATH, else in Wave's own bin folder (WAVETERM_WSHBINDIR), which Wave sets."""
    env = os.environ if env is None else env
    which = which or shutil.which
    found = which("wsh")
    if found:
        return found
    folder = env.get("WAVETERM_WSHBINDIR")
    if folder:
        for name in ("wsh.exe", "wsh"):
            if Path(folder, name).is_file():
                return str(Path(folder, name))
    return None


# ---------------------------------------------------------------------------
# Opening the preview
# ---------------------------------------------------------------------------


def add_options(parser: argparse.ArgumentParser, with_watch: bool = True) -> None:
    """--wave and --no-wave, for the commands that serve a live preview."""
    prefix = "With --watch, o" if with_watch else "O"
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--wave", action="store_true", default=None,
        help=f"{prefix}pen the preview in a Wave Terminal pane (the default inside Wave)",
    )  # fmt: skip
    group.add_argument(
        "--no-wave", dest="wave", action="store_false", default=None,
        help=f"{prefix}pen the browser even inside Wave Terminal (or set {OFF_VARIABLE}=1)",
    )  # fmt: skip


@dataclass
class Opened:
    """What became of the preview: where it was shown (wave, browser or nowhere), and why, when not in Wave."""

    where: str
    reason: str = ""
    block: str = ""


def show(
    address: str,
    open_browser: bool = True,
    wave: bool | None = None,
    env: Mapping[str, str] | None = None,
    run: Run | None = None,
    which: Callable[[str], str | None] | None = None,
    browser: Callable[[str], object] | None = None,
    state_dir: Path | None = None,
) -> Opened:
    """Show the preview at ``address``: in a Wave pane when asked (``wave=True``) or inside Wave (``None``),
    else in the browser. It never raises: a pane that cannot open is one printed line, and the preview goes on.
    ``open_browser=False`` (``--no-open``) shows it nowhere."""
    env = os.environ if env is None else env
    browser = browser or webbrowser.open
    if not open_browser:
        return Opened("nowhere")
    wanted = wave if wave is not None else (inside_wave(env) and not switched_off(env))
    if not wanted:
        browser(address)
        return Opened("browser")
    opened = open_pane(address, env=env, run=run, which=which, state_dir=state_dir)
    if opened.where == "wave":
        print(f"opened the preview in a Wave pane ({opened.block or 'wsh web open'})", flush=True)
        if in_wsl(env):
            print("  from WSL: if the pane stays blank, turn on localhostForwarding in .wslconfig", flush=True)
        return opened
    if over_ssh(env):  # the browser of the remote machine is no use either
        print(f"not opened in a Wave pane: {opened.reason}", flush=True)
        return opened
    print(f"not opened in a Wave pane: {opened.reason}. Opening the browser instead", flush=True)
    browser(address)
    return Opened("browser", opened.reason)


def open_pane(
    address: str,
    env: Mapping[str, str] | None = None,
    run: Run | None = None,
    which: Callable[[str], str | None] | None = None,
    state_dir: Path | None = None,
) -> Opened:
    """Open ``address`` in a Wave web pane, replacing the pane the last preview in this Wave tab opened."""
    env = os.environ if env is None else env
    run = run or subprocess.run
    if over_ssh(env):
        port = address.rstrip("/").rsplit(":", 1)[-1]
        return Opened(
            "nowhere",
            f"py-doc runs over SSH, so {address} is on the remote machine, which Wave's window cannot reach. "
            f"Forward the port (ssh -L {port}:127.0.0.1:{port} HOST) and run: wsh web open {address}",
        )
    wsh = find_wsh(env, which)
    if not wsh:
        return Opened("nowhere", "wsh was not found on the PATH (see `py-doc doctor`)")
    remembered = _remembered(env, state_dir)
    attempts = ([[wsh, "web", "open", "-r", remembered, address]] if remembered else []) + [
        [wsh, "web", "open", address]
    ]
    problem = ""
    for command in attempts:
        try:
            result = run(command, capture_output=True, text=True, timeout=TIMEOUT, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            return Opened("nowhere", f"wsh did not run: {exc}")
        if result.returncode == 0:
            block = _block(result.stdout or "")
            _remember(env, state_dir, block)
            return Opened("wave", block=block)
        problem = ((result.stderr or result.stdout or "").strip().splitlines() or [""])[-1]
        logger.debug(f"{' '.join(command)} failed ({result.returncode}): {problem}")
    return Opened("nowhere", f"wsh web open failed{': ' + problem if problem else ''}")


def _block(output: str) -> str:
    """The ORef in ``created block <ORef>``, or nothing when wsh printed something else."""
    for line in output.splitlines():
        if line.strip().startswith("created block "):
            return line.strip().split()[-1]
    return ""


def _state_file(env: Mapping[str, str], state_dir: Path | None) -> Path | None:
    tab = env.get("WAVETERM_TABID", "")
    if not tab:
        return None
    safe = "".join(c for c in tab if c.isalnum() or c in "-_")[:80]
    return (state_dir or Path(tempfile.gettempdir())) / f"py-doc-wave-{safe}.txt"


def _remembered(env: Mapping[str, str], state_dir: Path | None) -> str:
    path = _state_file(env, state_dir)
    try:
        return path.read_text(encoding="utf-8").strip() if path and path.is_file() else ""
    except OSError:
        return ""


def _remember(env: Mapping[str, str], state_dir: Path | None, block: str) -> None:
    path = _state_file(env, state_dir)
    if path and block:
        try:
            path.write_text(block, encoding="utf-8")
        except OSError:
            pass  # the next preview opens a pane of its own; nothing else depends on it


# ---------------------------------------------------------------------------
# py-doc doctor
# ---------------------------------------------------------------------------


def doctor_checks(env: Mapping[str, str] | None = None, run: Run | None = None, which=None) -> list:
    """The Wave lines of ``py-doc doctor``: none outside Wave, and never a failure (W-23, W-24)."""
    from .runtime.doctor import Check

    env = os.environ if env is None else env
    if not inside_wave(env):
        return []
    run = run or subprocess.run
    version = env.get("WAVETERM_VERSION", "") or "version unknown"
    if switched_off(env):
        return [
            Check("wave", "info", f"Wave Terminal {version}; the preview opens in the browser ({OFF_VARIABLE} is set)")
        ]
    if over_ssh(env):
        return [Check("wave", "info", f"Wave Terminal {version} over SSH",
                      "The preview's address is on this machine: forward its port to see it in a Wave pane")]  # fmt: skip
    wsh = find_wsh(env, which)
    fix = (
        "Open this shell from Wave again, or install wsh in it: Wave adds wsh to the connections it manages "
        "(WSL and SSH) when you connect, and asks first unless conn:askbeforewshinstall is false"
    )
    if not wsh:
        return [Check("wave", "WARN", f"Wave Terminal {version}, but wsh is not on the PATH, so the preview opens in the browser", fix)]  # fmt: skip
    try:
        result = run([wsh, "version"], capture_output=True, text=True, timeout=TIMEOUT, check=False)
        answer = (result.stdout or "").strip().splitlines()
        ok = result.returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        ok, answer = False, [str(exc)]
    if not ok:
        return [Check("wave", "WARN", f"Wave Terminal {version}, but wsh at {wsh} does not answer", fix)]
    detail = f"Wave Terminal {version}; wsh answers ({answer[0] if answer else wsh}), so previews open in a Wave pane"
    return [Check("wave", "ok", detail)]


# ---------------------------------------------------------------------------
# The sidebar widget
# ---------------------------------------------------------------------------


def widget(folder: str | None = None) -> dict:
    """py-doc's widget for Wave's widgets.json: a terminal pane that runs ``py-doc wave pick``."""
    meta: dict = {"view": "term", "controller": "cmd", "cmd": "py-doc wave pick", "cmd:closeonexit": False}
    if folder:
        meta["cmd:cwd"] = folder
    return {
        "icon": "eye",
        "label": "preview",
        "description": "py-doc: live preview of a Markdown document, deck or poster",
        "display:order": 50,
        "blockdef": {"meta": meta},
    }


def config_dir(env: Mapping[str, str] | None = None) -> Path:
    """Wave's configuration folder: WAVETERM_CONFIG_HOME when set, else ~/.config/waveterm on every system."""
    env = os.environ if env is None else env
    configured = env.get("WAVETERM_CONFIG_HOME")
    return Path(configured) if configured else Path.home() / ".config" / "waveterm"


def install_widget(config: Path, definition: dict) -> tuple[str, str]:
    """Add py-doc's widget to ``config``/widgets.json, or bring it up to date. The other widgets and keys
    are never changed (W-14, W-43). Returns (outcome, detail): added, updated, up to date, or skipped."""
    path = config / "widgets.json"
    widgets: dict = {}
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8-sig")
            widgets = json.loads(text) if text.strip() else {}
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return "skipped", f"{path} cannot be read ({exc}), so it is left as it is"
        if not isinstance(widgets, dict):
            return "skipped", f"{path} is not a JSON object, so it is left as it is"
    current = widgets.get(WIDGET_NAME)
    if current == definition:
        return "up to date", str(path)
    outcome = "added" if current is None else "updated"
    widgets[WIDGET_NAME] = definition
    try:
        config.mkdir(parents=True, exist_ok=True)
        partial = path.with_name("widgets.json.py-doc-tmp")
        partial.write_text(json.dumps(widgets, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(partial, path)
    except OSError as exc:
        return "skipped", f"{path} cannot be written ({exc})"
    return outcome, str(path)


# ---------------------------------------------------------------------------
# py-doc wave pick: what the widget runs
# ---------------------------------------------------------------------------

KINDS = {"d": "document", "s": "slides", "p": "poster"}


def markdown_below(folder: Path, most: int = MOST) -> list[Path]:
    """The Markdown files in ``folder`` and below it, nearest first, without hidden and build folders."""
    found: list[Path] = []
    for root, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIPPED)
        for name in sorted(names):
            if name.lower().endswith((".md", ".markdown")):
                found.append(Path(root, name))
    found.sort(key=lambda p: (len(p.relative_to(folder).parts), str(p).lower()))
    return found[:most]


def guess_kind(path: Path) -> str:
    """Slides for a deck (``marp: true``, ``deck: true`` or a front matter ``kind``), a poster when the front
    matter says ``poster``, else a document."""
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        return "document"
    if not head.startswith("---"):
        return "document"
    front = head.split("\n---", 1)[0].lower()
    if "poster:" in front or "kind: poster" in front:
        return "poster"
    if "marp: true" in front or "deck: true" in front or "kind: slides" in front or "kind: deck" in front:
        return "slides"
    return "document"


def pick(
    folder: Path,
    given: str | None = None,
    kind: str | None = None,
    ask: Callable[[str], str] = input,
    out=print,
) -> tuple[Path, str] | None:
    """Choose the file to preview: ``given``, or one of the Markdown files below ``folder``, by number or path.
    Returns the file and its kind, or None when nothing was chosen."""
    if given:
        chosen = Path(given).expanduser()
        if not chosen.is_absolute():
            chosen = folder / chosen
        if not chosen.is_file():
            out(f"Error: {chosen} is not a file")
            return None
        return chosen.resolve(), kind or guess_kind(chosen)
    while True:
        files = markdown_below(folder)
        out(f"Markdown files in {folder}:")
        if not files:
            out("  (none)")
        for number, path in enumerate(files, 1):
            out(f"  {number:>2}  {path.relative_to(folder).as_posix()}")
        try:
            answer = ask("Number, a file, or a folder to look in (Enter stops): ").strip().strip('"')
        except EOFError:
            return None
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(files):
            chosen = files[int(answer) - 1]
        else:
            chosen = Path(answer).expanduser()
            chosen = chosen if chosen.is_absolute() else folder / chosen
            if chosen.is_dir():
                folder = chosen.resolve()
                continue
            if not chosen.is_file():
                out(f"No file or folder {answer}")
                continue
        if kind:
            return chosen.resolve(), kind
        guessed = guess_kind(chosen)
        try:
            reply = ask(f"Preview as a [d]ocument, [s]lides or a [p]oster? (Enter: {guessed}) ").strip().lower()
        except EOFError:
            return None
        return chosen.resolve(), KINDS.get(reply[:1], guessed) if reply else guessed


# ---------------------------------------------------------------------------
# py-doc wave
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-doc wave",
        description="Wave Terminal: the sidebar widget that starts a live preview, and the picker it runs",
        epilog="The preview itself opens in a Wave pane from `py-doc docx|slides|poster FILE --watch` and "
        "`py-doc preview FILE` when they run inside Wave. The user guide's live preview chapter has the details.",
    )
    commands = parser.add_subparsers(dest="action", metavar="action", required=True)
    show_widget = commands.add_parser(
        "widget", help="Print py-doc's sidebar widget for Wave's widgets.json, or add it with --install"
    )
    show_widget.add_argument("--install", action="store_true", help="Add it to widgets.json, or bring it up to date")
    show_widget.add_argument("--folder", help="The folder its terminal starts in (default: your home folder)")
    show_widget.add_argument(
        "--config-dir",
        type=Path,
        help="Wave's configuration folder (default: WAVETERM_CONFIG_HOME, else ~/.config/waveterm)",
    )
    show_widget.add_argument("-y", "--yes", action="store_true", help="With --install, do not ask first")
    chooser = commands.add_parser("pick", help="Choose a Markdown file here and preview it (what the widget runs)")
    chooser.add_argument("file", nargs="?", help="The file to preview, which skips the question")
    chooser.add_argument("-k", "--kind", choices=["document", "slides", "poster"], help="What to preview it as")
    chooser.add_argument("--port", type=int, default=0, help="The local port to serve on (default: a free one)")
    add_options(chooser, with_watch=False)
    return parser


def run_wave(argv: Sequence[str] | None = None, ask: Callable[[str], str] = input) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "widget":
        return _widget(args, ask)
    chosen = pick(Path.cwd(), args.file, args.kind, ask=ask)
    if chosen is None:
        print("Nothing chosen")
        return 1
    source, kind = chosen
    print(f"previewing {source} as a {kind}", flush=True)
    from .preview_cli import run_preview

    command = [str(source), "--kind", kind, "--port", str(args.port)]
    if args.wave is not None:
        command.append("--wave" if args.wave else "--no-wave")
    return run_preview(command)


def _widget(args: argparse.Namespace, ask: Callable[[str], str]) -> int:
    definition = widget(args.folder)
    snippet = json.dumps({WIDGET_NAME: definition}, indent=2)
    if not args.install:
        print(snippet)
        print(f"\nAdd the entry above to {config_dir() / 'widgets.json'} (inside its outer braces), "
              "or run `py-doc wave widget --install`.", file=sys.stderr)  # fmt: skip
        return 0
    config = args.config_dir or config_dir()
    if in_wsl() and not args.config_dir:
        print(
            "py-doc runs in WSL, but Wave's settings are on Windows. Run `py-doc wave widget --install` "
            "there (scripts\\update.ps1 does), or name the folder: --config-dir /mnt/c/Users/YOU/.config/waveterm"
        )
        return 1
    if not args.yes:
        print(snippet)
        if ask(f"Add this widget to {config / 'widgets.json'}? Other widgets are kept. [y/N] ").strip().lower() not in ("y", "yes"):  # fmt: skip
            print("Nothing was changed.")
            return 1
    outcome, detail = install_widget(config, definition)
    if outcome == "skipped":
        print(f"note: {detail}")
        return 1
    print(f"{outcome}: py-doc's widget in {detail}" if outcome != "up to date" else f"up to date: {detail}")
    return 0


def main() -> None:
    sys.exit(run_wave())


if __name__ == "__main__":
    main()
