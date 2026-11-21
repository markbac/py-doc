"""``py-doc web``: serve the web page of py-doc for a workspace folder."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

EXAMPLES = """examples:
  py-doc web                                   serve ./workspace on http://127.0.0.1:8888
  py-doc web --root /srv/py-doc/workspace --host 0.0.0.0 --port 8888
  PYDOC_WEB_PASSWORD=secret py-doc web --host 0.0.0.0     ask for a password (any user name)

Each folder of the workspace is a project. Keep the server on your own network: it runs py-doc on
whatever is uploaded. Set a password, or put it behind a proxy that asks for one, before others can reach it.
The settings can also come from PYDOC_WEB_ROOT, PYDOC_WEB_HOST, PYDOC_WEB_PORT, PYDOC_WEB_PASSWORD,
PYDOC_WEB_WORKERS and PYDOC_WEB_TIMEOUT."""


def run_web(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc web",
        description="Serve py-doc in the browser: explore, edit, preview, convert, build and lint projects",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    env = os.environ.get
    parser.add_argument("--root", default=env("PYDOC_WEB_ROOT", "workspace"), help="The workspace folder")
    parser.add_argument("--host", default=env("PYDOC_WEB_HOST", "127.0.0.1"),
                        help="The address to listen on; 0.0.0.0 for every one (default: this computer only)")  # fmt: skip
    parser.add_argument("--port", type=int, default=int(env("PYDOC_WEB_PORT", "8888")))
    parser.add_argument("--workers", type=int, default=int(env("PYDOC_WEB_WORKERS", "1")),
                        help="Jobs that run at the same time (default: 1)")  # fmt: skip
    parser.add_argument("--timeout", type=float, default=float(env("PYDOC_WEB_TIMEOUT", "1800")),
                        help="Seconds a job may take before it is stopped (default: 1800)")  # fmt: skip
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    args = parser.parse_args(argv)

    from py_doc._logging import configure_logging

    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        import uvicorn

        from .app import Settings, create_app
    except ImportError:
        logger.error("py-doc web needs its extra packages: pip install -e .[web]")
        return 2

    password = env("PYDOC_WEB_PASSWORD") or None
    if args.host not in ("127.0.0.1", "localhost", "::1") and not password:
        logger.warning("Listening on %s with no password: anyone who can reach it can run py-doc. "
                       "Set PYDOC_WEB_PASSWORD, or put it behind a proxy that asks for one", args.host)  # fmt: skip
    root = Path(args.root).resolve()
    app = create_app(Settings(root=root, password=password, workers=args.workers, timeout=args.timeout))
    logger.info("Workspace %s, on http://%s:%d/", root, args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning" if args.quiet else "info")
    return 0
