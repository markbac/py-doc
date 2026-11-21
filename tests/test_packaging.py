"""Every file py-doc reads at run time goes into the package, not only the Python.

A file missing from ``package-data`` works in a checkout and fails in an installed py-doc, as the science
image's definition once did in the py-doc web container.
"""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "py_doc"


def test_every_data_file_is_in_package_data():
    patterns = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"][
        "package-data"
    ]["py_doc"]
    missing = []
    for path in PACKAGE.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in (".py", ".pyc"):
            continue
        relative = path.relative_to(PACKAGE).as_posix()
        if not any(fnmatch.fnmatchcase(relative, pattern) and "/" not in relative[len(pattern.rstrip("*")):]
                   for pattern in patterns):  # fmt: skip
            missing.append(relative)
    assert not missing, f"add these to [tool.setuptools.package-data] in pyproject.toml: {missing}"
