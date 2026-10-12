"""The old ``py-c4-exporter`` command, now ``py-doc c4 export``."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from py_doc._cli import deprecation_notice
from py_doc.c4.cli import run_c4


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-q" not in args and "--quiet" not in args:
        print(deprecation_notice("py-c4-exporter", "py-doc c4 export"), file=sys.stderr)
    return run_c4(["export", *args])


if __name__ == "__main__":
    sys.exit(main())
