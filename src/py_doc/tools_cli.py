"""``py-doc tools`` and ``py-doc doctor``: manage the tool image and check that it works."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from ._logging import configure_logging
from .config import ConfigError, find_config, load_config
from .errors import ConversionError, EnvironmentProblem, exit_status
from .runtime import RuntimeSettings, image
from .runtime.doctor import diagnose, failed, render
from .runtime.engine import Runtime

logger = logging.getLogger(__name__)

# What `tools status` runs inside the image to report versions.
VERSION_PROBES = (
    ("pandoc", ["pandoc", "--version"]),
    ("xelatex", ["xelatex", "--version"]),
    ("java", ["java", "-version"]),
    ("plantuml", ["java", "-jar", "/opt/plantuml.jar", "-version"]),
    ("graphviz", ["dot", "-V"]),
    ("mermaid", ["mmdc", "--version"]),
    ("inkscape", ["inkscape", "--version"]),
    ("python", ["python3", "--version"]),
)


def _error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def settings_from_config(config_path: str | None) -> RuntimeSettings:
    """The ``runtime`` section of the nearest py-doc.yml, or the defaults when there is none."""
    path = Path(config_path) if config_path else find_config(Path.cwd())
    if path is None:
        return RuntimeSettings()
    return load_config(path).runtime


def make_runtime(settings: RuntimeSettings) -> Runtime:
    return Runtime(image.image_ref(), docker=settings.docker or "docker", wsl_distro=settings.wsl_distro)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")


def tools_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="py-doc tools", description="Manage the tool container image")
    commands = parser.add_subparsers(dest="action", metavar="action", required=True)
    build = commands.add_parser("build", help="Build the tool image here (slow the first time)")
    build.add_argument("--ca-file", type=Path, help="Extra certificate for builds behind a TLS-inspecting proxy")
    build.add_argument("--no-cache", action="store_true", help="Build every layer again")
    commands.add_parser("status", help="Show the image tag, size and the version of each tool in it")
    commands.add_parser("prune", help="Remove tool images left by earlier py-doc versions")
    commands.add_parser("lock", help="Download the tools in tools.lock and record their checksums")
    save = commands.add_parser("save", help="Write the image to a file, for machines that cannot build it")
    save.add_argument("file", type=Path)
    load = commands.add_parser("load", help="Load an image written by `tools save`")
    load.add_argument("file", type=Path)
    for sub in commands.choices.values():
        _common(sub)
    return parser


def run_tools(argv: Sequence[str] | None = None) -> int:
    args = tools_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        if args.action == "lock":
            names = image.lock()
            print(f"Recorded checksums for: {', '.join(names)}" if names else "Every checksum is already recorded")
            return 0
        runtime = make_runtime(settings_from_config(args.config))
        return _tools_action(args, runtime)
    except ConfigError as exc:
        _error(str(exc))
        return 1
    except ConversionError as exc:
        _error(str(exc))
        return exit_status(exc)


def _tools_action(args: argparse.Namespace, runtime: Runtime) -> int:
    if args.action == "build":
        image.build(runtime, ca_file=args.ca_file, no_cache=args.no_cache)
    elif args.action == "status":
        return _status(runtime)
    elif args.action == "prune":
        removed = image.prune(runtime)
        print("\n".join(f"removed {tag}" for tag in removed) if removed else "Nothing to remove")
    elif args.action == "save":
        image.save(runtime, args.file.resolve())
    elif args.action == "load":
        image.load(runtime, args.file.resolve())
    return 0


def _status(runtime: Runtime) -> int:
    present = image.exists(runtime)
    print(f"image    {runtime.image}  {'built' if present else 'not built'}")
    others = [tag for tag in image.tags(runtime) if tag != runtime.image]
    if others:
        print(f"older    {', '.join(others)}  (remove with `py-doc tools prune`)")
    unlocked = image.unlocked()
    if unlocked:
        print(f"lock     no checksum for {', '.join(unlocked)}  (run `py-doc tools lock`)")
    if not present:
        return 0
    for name, command in VERSION_PROBES:
        result = runtime.run(command, check=False)
        text = (result.stdout or result.stderr).strip().splitlines()
        print(f"{name:<9}{text[0] if text and result.returncode == 0 else 'not available'}")
    return 0


def run_doctor(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="py-doc doctor", description="Check that the tool container works")
    _common(parser)
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        runtime = make_runtime(settings_from_config(args.config))
    except ConfigError as exc:
        _error(str(exc))
        return 1
    except EnvironmentProblem as exc:
        print(f"FAIL  platform   {exc}")
        return 2
    checks = diagnose(runtime)
    print(render(checks))
    return 2 if failed(checks) else 0
