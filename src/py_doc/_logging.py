"""Logging setup for the command line tools. Library code never configures logging."""

from __future__ import annotations

import sys

from ctxlogkit import setup_logging


def configure_logging() -> None:
    """Send progress messages to stderr, in colour on a terminal and plain for pipes."""
    setup_logging(name="py_doc", level="INFO", mode="compact", console_stream=sys.stderr)
