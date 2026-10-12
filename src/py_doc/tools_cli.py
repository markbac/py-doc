"""``py-doc doctor``: check that the tool container works."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from ._logging import configure_logging
from .config import ConfigError, find_config, load_config
from .errors import EnvironmentProblem
from .runtime import RuntimeSettings
from .runtime.doctor import diagnose, failed, render
from .runtime.engine import Runtime

logger = logging.getLogger(__name__)

IMAGE_REF = "py-doc-tools:unbuilt"  # replaced by a content tag when the image definition lands


def _error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def settings_from_config(config_path: str | None) -> RuntimeSettings:
    """The ``runtime`` section of the nearest py-doc.yml, or the defaults when there is none."""
    path = Path(config_path) if config_path else find_config(Path.cwd())
    if path is None:
        return RuntimeSettings()
    return load_config(path).runtime


def make_runtime(settings: RuntimeSettings) -> Runtime:
    return Runtime(IMAGE_REF, docker=settings.docker or "docker", wsl_distro=settings.wsl_distro)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")


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
