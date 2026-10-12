"""Logging setup for the command line tools. Library code never configures logging."""

from __future__ import annotations

import logging
import os
import sys

from ctxlogkit import setup_logging
from ctxlogkit.log_setup import _LEVEL_COLOURS, COLOUR_TIMESTAMP, DATE_FORMAT, SmartFieldFormatter

# ctxlogkit's "compact" layout is plain text. This is the same two fields, in ctxlogkit's level colours.
COMPACT_COLOUR = "[%(log_color)s%(levelname)s%(reset)s] %(log_color)s%(message)s%(reset)s"
# With --verbose each line also gets the time and the logger name, so a slow step can be found.
DEBUG_COLOUR = f"%({COLOUR_TIMESTAMP})s%(asctime)s%(reset)s {COMPACT_COLOUR} %(white)s(%(name)s)%(reset)s"


def configure_logging(quiet: bool = False, verbose: bool = False) -> None:
    """Send progress messages to stderr, in colour on a terminal and plain for pipes.

    ``quiet`` keeps warnings and errors only, and ``verbose`` adds debug detail, the time and the logger name. Colour is switched off when
    stderr is not a terminal, when ``NO_COLOR`` is set or ``TERM`` is ``dumb``, and ``FORCE_COLOR`` switches it on.
    """
    level = "WARNING" if quiet else "DEBUG" if verbose else "INFO"
    logger = setup_logging(name="py_doc", level=level, mode="compact", console_stream=sys.stderr)
    formatter = SmartFieldFormatter(
        fmt=DEBUG_COLOUR if verbose else COMPACT_COLOUR,
        datefmt=DATE_FORMAT if verbose else None,
        log_colors=_LEVEL_COLOURS,
        reset=True,
        stream=sys.stderr,
        no_color=os.environ.get("TERM") == "dumb",
    )
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is sys.stderr:
            handler.setFormatter(formatter)
