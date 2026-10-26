"""``py-doc tools`` and ``py-doc doctor``: manage the tool image and check that it works."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import replace
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from ._logging import configure_logging
from .config import ConfigError, find_config, load_config
from .errors import ConversionError, EnvironmentProblem, exit_status
from .runtime import RuntimeSettings, image
from .runtime.doctor import diagnose, failed, render
from .runtime import setup as docker_setup
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
    build.add_argument(
        "--science",
        action="store_true",
        help="Also build the science image, for the molecule, smith, plasmid and other fences",
    )
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
        if args.science:
            image.build_science(runtime, no_cache=args.no_cache)
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


NEXT_AFTER_SETUP = "Next: `py-doc tools build`, then `py-doc doctor`"


def run_setup(argv: Sequence[str] | None = None, *, run=None, ask=input) -> int:
    """``py-doc setup``: install Docker Engine for the tool runner, after showing the steps and asking."""
    import subprocess

    run = run or subprocess.run
    parser = argparse.ArgumentParser(
        prog="py-doc setup",
        description="Install Docker Engine (Ubuntu or Debian) in the WSL distro on Windows, or on this Linux machine",
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Do not ask first")
    parser.add_argument("--dry-run", action="store_true", help="Show the script that would run, and run nothing")
    parser.add_argument(
        "--distro", help="The WSL distribution to set up (default: runtime.wsl_distro, else the default one)"
    )
    _common(parser)
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        settings = settings_from_config(args.config)
        if args.distro:
            settings = replace(settings, wsl_distro=args.distro)
        runtime = make_runtime(settings)
        return _setup(runtime, args, run, ask)
    except ConfigError as exc:
        _error(str(exc))
        return 1
    except ConversionError as exc:
        _error(str(exc))
        return exit_status(exc)


def _setup(runtime: Runtime, args: argparse.Namespace, run, ask) -> int:
    where = f"the WSL distribution {runtime.wsl_distro or 'that is the default'}" if runtime.windows else "this machine"
    state = docker_setup.probe(runtime)
    if state.name == "ready":
        print(f"Docker Engine already works on {where}. {NEXT_AFTER_SETUP}")
        return 0
    if state.name == "stopped" and not args.dry_run:
        print(f"Docker Engine is installed on {where} but not running. Starting it.")
        docker_setup.start_service(runtime, run)
        if docker_setup.probe(runtime).name == "ready":
            print(f"Docker Engine is running. {NEXT_AFTER_SETUP}")
            return 0
    try:
        user = docker_setup.target_user(runtime, run)
    except EnvironmentProblem:
        if not args.dry_run:
            raise
        user = "YOUR_USER"
    print(f"Docker Engine will be set up on {where} for the user '{user}':")
    for number, step in enumerate(docker_setup.describe(runtime), 1):
        print(f"  {number}. {step}")
    if args.dry_run:
        print("\nThe script (run as root):\n")
        print(docker_setup.script(user, runtime.windows))
        return 0
    if not runtime.windows and os.geteuid() != 0:
        print("sudo will ask for your password.")
    if not args.yes and ask("Run these steps as root? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Nothing was changed.")
        return 1
    docker_setup.install(runtime, user, run)
    docker_setup.restart(runtime, run)
    if runtime.windows:
        docker_setup.start_service(runtime, run)
    state = docker_setup.probe(runtime)
    if state.name == "ready":
        print(f"Docker Engine works. {NEXT_AFTER_SETUP}")
        return 0
    if runtime.windows:
        _error(
            "Docker is installed but not usable yet"
            + (f": {state.detail}" if state.detail else "")
            + ". Close every WSL window, run `wsl --shutdown`, and run `py-doc doctor`"
        )
    else:
        print(
            "Docker is installed. Log out and in again so the docker group applies (or run `newgrp docker`), then run `py-doc doctor`."
        )
        return 0
    return 2
