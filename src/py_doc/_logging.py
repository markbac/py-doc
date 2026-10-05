"""Logging setup for the command line tools. Library code never configures logging."""

from __future__ import annotations

import sys

from ctxlogkit import setup_logging


def configure_logging(quiet: bool = False, verbose: bool = False) -> None:
    """Send progress messages to stderr, in colour on a terminal and plain for pipes.

    ``quiet`` keeps warnings and errors only, and ``verbose`` adds debug detail.
    """
    level = "WARNING" if quiet else "DEBUG" if verbose else "INFO"
    setup_logging(name="py_doc", level=level, mode="compact", console_stream=sys.stderr)
