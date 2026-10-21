"""``py-doc c4``: check, export and draw Structurizr workspaces, and manage the Structurizr Local container."""

from __future__ import annotations

import argparse
import logging
import sys
import time
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import C4Settings, ConfigError, find_config, load_config
from py_doc.errors import ConversionError, exit_status
from py_doc.lint.config import LintConfig
from py_doc.runtime import RuntimeSettings, connect

from .check import check_model
from .generate import LEVELS, generate
from .model import load_workspace
from .render import render_views
from .lock import LOCK, lock_image, resolve_image
from .stack import SERVER, SERVER_PORT, ExternalStack, Stack
from .structurizr import TEXT_FORMATS, StructurizrCli, find_workspaces, workspace_json

logger = logging.getLogger(__name__)
DRAWN = ("png", "svg")
FORMATS = (*DRAWN, *TEXT_FORMATS, "markdown")
WATCH_SECONDS = 2  # how often a running `c4 up` checks that Local is still there


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc c4", description="Structurizr workspaces: check, export and draw")
    actions = parser.add_subparsers(dest="action", metavar="action", required=True)

    def common(sub: argparse.ArgumentParser, many: bool = True) -> None:
        sub.add_argument(
            "workspace",
            nargs="?",
            default=".",
            help="A .dsl or workspace.json file, or a folder to search (default: .)",
        )
        sub.add_argument("-c", "--config", help="py-doc.yml to read (default: the nearest one)")
        noise = sub.add_mutually_exclusive_group()
        noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
        noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")

    check = actions.add_parser("check", help="Read workspaces and check the model (the CI dry run)")
    common(check)
    check.add_argument("--strict", action="store_true", help="Exit with status 1 for warnings as well as errors")

    export = actions.add_parser("export", help="Write diagrams, diagram source or Markdown for workspaces")
    common(export)
    export.add_argument("-o", "--output", default="c4_exports", help="Output folder (default: c4_exports)")
    export.add_argument(
        "-f", "--formats", nargs="+", choices=FORMATS, default=["svg", "plantuml", "mermaid"], help="Formats to write"
    )
    export.add_argument("--views", nargs="+", metavar="KEY", help="Draw only these views")
    export.add_argument("--levels", nargs="+", choices=LEVELS, help="Levels of Markdown to write (default: all)")
    export.add_argument(
        "--url", help="A Structurizr Local or server that is already running, as the tool container can reach it"
    )
    export.add_argument("--dry-run", action="store_true", help="List what would be written and write nothing")

    lock = actions.add_parser("lock", help="Pin the Structurizr Local image by digest in c4-images.lock")
    common(lock)
    lock.add_argument("--tag", default="latest", help="The structurizr/structurizr tag to pin (default: latest)")

    up = actions.add_parser("up", help="Open a workspace in Structurizr Local to view it and edit its layouts")
    common(up)
    up.add_argument("--detach", action="store_true", help="Leave Local running and return. `py-doc c4 down` stops it")
    up.add_argument("--no-browser", action="store_true", help="Do not open the diagrams in a browser")
    for name, text in (("down", "Stop Structurizr Local"), ("status", "Say whether Local is running")):
        common(actions.add_parser(name, help=text))
    return parser


def _settings(args: argparse.Namespace) -> tuple[C4Settings, RuntimeSettings, LintConfig, Path]:
    """The settings, and the project folder that holds the ``.py-doc`` cache (the folder of py-doc.yml, else here)."""
    path = Path(args.config) if args.config else find_config(Path.cwd())
    if path is None:
        return C4Settings(), RuntimeSettings(), LintConfig(), Path.cwd()
    project = load_config(path)
    return project.c4, project.runtime, project.lint, project.root


def _find(target: str) -> list[Path]:
    path = Path(target)
    if not path.exists():
        raise ConversionError(f"Path not found: {path}")
    found = find_workspaces(path)
    if not found:
        raise ConversionError(f"No Structurizr workspace (.dsl or workspace.json) found in {path}")
    return found


def run_c4(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 done, 1 a workspace failed or has errors, 2 the machine cannot run it."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        c4, runtime_settings, lint, root = _settings(args)
        cache = root / ".py-doc" / "c4" / "json"
        box = [None]

        def runtime():
            box[0] = box[0] or connect(runtime_settings)
            return box[0]

        if args.action == "lock":
            print(f"Pinned {lock_image(runtime(), root, args.tag)} in {root / LOCK}")
            return 0
        files = _find(args.workspace)
        if args.action in ("up", "down", "status"):
            return _stack(args, files, runtime, c4, root)
        if args.action == "check":
            return _check(files, runtime, c4, lint, args.strict, cache)
        return _export(args, files, runtime, c4, cache, root)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exit_status(exc)


def _stack(args: argparse.Namespace, files: list[Path], runtime, c4: C4Settings, root: Path) -> int:
    if len(files) != 1:
        raise ConversionError(f"{len(files)} workspaces found. Name one: {', '.join(str(f) for f in files)}")
    stack = Stack(
        runtime(),
        files[0],
        image=resolve_image(c4.image, root),
        port=c4.port or SERVER_PORT,
        live=True,
        state=root / ".py-doc",
    )
    if args.action == "status":
        print(stack.status())
        return 0
    if args.action == "down":
        stack.down()
        print("stopped")
        return 0
    if not stack.up():
        print(f"Structurizr Local is already running: {stack.browser_url}")
        return 0
    print(f"Structurizr Local: {stack.browser_url}")
    print(f"Changes to {files[0].name} show when the page is reloaded. Layouts saved in the browser go to "
          f"{files[0].parent / 'workspace.json'}")  # fmt: skip
    if not args.no_browser:
        webbrowser.open(stack.browser_url)
    if args.detach:
        stack.detach()
        print("Stop it with: py-doc c4 down")
        return 0
    return _serve(stack)


def _serve(stack: Stack) -> int:
    """Keep Local running until Ctrl+C, then stop it. Status 1 if it stops by itself."""
    print("Press Ctrl+C to stop")
    try:
        while stack.status() == "running":
            time.sleep(WATCH_SECONDS)
    except KeyboardInterrupt:
        stack.down()
        print("stopped")
        return 0
    logs = stack.runtime.engine(["logs", "--tail", "15", SERVER], check=False)
    stack.down()
    print(f"Error: Structurizr Local stopped by itself.\n{(logs.stdout + logs.stderr).strip()}", file=sys.stderr)
    return 1


def _check(files: list[Path], runtime, c4: C4Settings, lint: LintConfig, strict: bool, cache: Path) -> int:
    worst = 0
    for file in files:
        ws = load_workspace(workspace_json(file, cache, runtime, c4.cli))
        issues = check_model(ws, file, lint)
        for issue in issues:
            print(issue)
        errors = sum(i.severity == "error" for i in issues)
        warnings = sum(i.severity == "warning" for i in issues)
        print(
            f"{file}: {len(ws.elements)} element(s), {len(ws.relationships)} relationship(s), {len(ws.views)} view(s), "
            f"{errors} error(s), {warnings} warning(s)"
        )
        worst = max(worst, 1 if errors or (strict and warnings) else 0)
    return worst


def _export(args: argparse.Namespace, files: list[Path], runtime, c4: C4Settings, cache: Path, root: Path) -> int:
    failures: list[str] = []
    out_root = Path(args.output)
    for file in files:
        out = out_root / file.parent.name if len(files) > 1 else out_root
        try:
            _export_one(args, file, out, runtime, c4, cache, root)
        except ConversionError as exc:
            if exit_status(exc) == 2:
                raise
            print(f"Error: {file}: {exc}", file=sys.stderr)
            failures.append(str(file))
    if failures:
        print(f"{len(failures)} of {len(files)} workspace(s) failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def _export_one(
    args: argparse.Namespace, file: Path, out: Path, runtime, c4: C4Settings, cache: Path, root: Path
) -> None:
    formats = list(dict.fromkeys(args.formats))
    cli = StructurizrCli(runtime, c4.cli)
    ws = load_workspace(workspace_json(file, cache, runtime, c4.cli))
    from .render import plan

    if args.dry_run:
        names = [f"{out}/{p.name}" for fmt in formats if fmt in DRAWN for p in plan(ws, out, (fmt,), args.views).files]
        names += [f"{out}/{fmt}/" for fmt in formats if fmt in TEXT_FORMATS]
        names += [
            f"{out}/markdown/{page}"
            for page in (generate(ws, file.name, levels=args.levels) if "markdown" in formats else {})
        ]
        print("\n".join(sorted(names)) or "Nothing to write")
        return
    drawn = tuple(f for f in formats if f in DRAWN)
    pictures: dict[str, str] = {}
    if drawn:
        stack = (
            ExternalStack(args.url)
            if args.url
            else Stack(runtime(), file, image=resolve_image(c4.image, root), port=c4.port or SERVER_PORT)
        )
        files = render_views(ws, file, out, runtime(), formats=drawn, keys=args.views, stack=stack)
        pictures = {p.stem: p.name for p in files if p.suffix == f".{drawn[0]}"}
    for fmt in (f for f in formats if f in TEXT_FORMATS):
        if file.suffix != ".dsl":
            raise ConversionError(f"The {fmt} format needs the .dsl file, not workspace.json")
        cli.export(file, fmt, out / fmt)
    if "markdown" in formats:
        folder = out / "markdown"
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in generate(
            ws, file.name, levels=args.levels, images={k: f"../{v}" for k, v in pictures.items()}
        ).items():
            (folder / name).write_text(text, encoding="utf-8")
    print(f"Exported '{ws.name}' to {out}")
