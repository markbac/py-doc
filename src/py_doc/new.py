"""``py-doc new``: start one document in the legacy build file format, with a number from the register.

The register is ``doc-numbers.yml`` in the repository root. It lists every number given out, with the
title and the build file, so two documents never get the same number. Committing it with the new
document makes a clash between branches show as a merge conflict. When there is no register yet, it is
made from the ``document_number`` of the legacy build files already in the repository.

A number is ``[PREFIX-][TYPE-]NNN``. The prefix (``G460``) is set once in the register and the type
(``TN``) is asked each time; both may be empty. ``NNN`` is one counter for every type.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from ._logging import configure_logging
from .migrate import discover, read_createdocs

REGISTER = "doc-numbers.yml"
REGISTER_HEADER = (
    "# Document numbers given out by `py-doc new`. Commit this file with the new document, so the\n"
    "# next number cannot be taken twice. A number is [prefix-][type-]NNN, one counter for every type.\n"
)
FORMATS = {"docx": "Word", "pptx": "PowerPoint"}
_SEQUENCE = re.compile(r"(\d+)$")
_CODE = re.compile(r"^[A-Za-z0-9]*$")


class NewError(Exception):
    """The document cannot be made. The message says why."""


@dataclass
class Entry:
    number: str
    title: str
    file: str


@dataclass
class Register:
    path: Path
    prefix: str = ""
    entries: list[Entry] | None = None

    def next_number(self, kind: str) -> str:
        found = [m for m in (_SEQUENCE.search(e.number) for e in self.entries or []) if m]
        last = max((int(m[1]) for m in found), default=0)
        digits = max([3, *(len(m[1]) for m in found)])
        return "-".join(part for part in (self.prefix, kind, f"{last + 1:0{digits}d}") if part)

    def save(self) -> None:
        data = {"prefix": self.prefix, "documents": [vars(e) for e in self.entries or []]}
        body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120)
        self.path.write_text(REGISTER_HEADER + body, encoding="utf-8")


def find_root(start: Path) -> Path:
    """The folder of the nearest register, else of the repository (``.git``), else ``start``."""
    start = start.resolve()
    for folder in (start, *start.parents):
        if (folder / REGISTER).is_file():
            return folder
    for folder in (start, *start.parents):
        if (folder / ".git").exists():
            return folder
    return start


def load_register(root: Path) -> Register:
    path = root / REGISTER
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except (yaml.YAMLError, OSError) as exc:
        raise NewError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("documents") or [], list):
        raise NewError(f"{path} must have a 'documents' list")
    entries = []
    for index, item in enumerate(data.get("documents") or []):
        if not isinstance(item, dict) or not item.get("number"):
            raise NewError(f"{path}: documents[{index}] has no number")
        entries.append(Entry(str(item["number"]), str(item.get("title") or ""), str(item.get("file") or "")))
    return Register(path, str(data.get("prefix") or ""), entries)


def existing_numbers(root: Path) -> list[Entry]:
    """The numbers of the legacy build files below ``root``, for a new register."""
    entries = []
    for path in discover([root]):
        data = read_createdocs(path)
        meta = (data or {}).get("meta") or {}
        number = meta.get("document_number") or meta.get("doc_number")
        if number:
            entries.append(Entry(str(number), str(meta.get("title") or ""), path.relative_to(root).as_posix()))
    return sorted(entries, key=lambda e: e.number)


def _git_name() -> str:
    try:
        done = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip()


def _stem(number: str, title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title)
    return "-".join([number, *words]) if words else number


def build_file(meta: dict[str, str], output: str, fmt: str, source: str) -> str:
    """The legacy build file: meta, cli and entries, as ``py-doc build --legacy`` reads it."""
    lines = ["meta:"]
    lines += [f"  {key}: {json.dumps(value, ensure_ascii=False)}" for key, value in meta.items() if value]
    lines += ["", "cli:"]
    if fmt == "docx":
        lines.append("  emit-docx: true")
    lines += [f"  output: {output}", f"  # template: path/to/Template.{fmt}", "", "entries:", f"  - file: {source}", "    heading_offset: 0", ""]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-doc new", description="Start a document here: a legacy build file and its Markdown, with the next number from the register"
    )
    parser.add_argument("--title", help="The document title")
    parser.add_argument("--type", dest="kind", help="The type code in the number, such as TN (empty for none)")
    parser.add_argument("--format", choices=sorted(FORMATS), help="Word (docx) or PowerPoint (pptx). Default: docx")
    parser.add_argument("--author", help="Default: git config user.name")
    parser.add_argument("--classification", help="Such as Confidential")
    parser.add_argument("--description", help="One sentence on what the document covers")
    parser.add_argument("--prefix", help="The number prefix, such as G460, kept in the register (only when it is made)")
    parser.add_argument("-y", "--yes", action="store_true", help="Ask nothing: take the defaults for what is not given")
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    noise.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")
    return parser


def _asker(ask: Callable[[str], str] | None) -> Callable[[str, str | None, str], str]:
    def value(question: str, given: str | None, default: str) -> str:
        if given is not None or ask is None:
            return default if given is None else given
        answer = ask(f"{question} [{default}]: " if default else f"{question}: ").strip()
        return answer or default

    return value


def make(folder: Path, args: argparse.Namespace, ask: Callable[[str], str] | None, today: datetime.date) -> tuple[list[Path], Register, bool]:
    """Write the build file and its Markdown in ``folder`` and record the number. Returns what was written."""
    value = _asker(ask)
    root = find_root(folder)
    created = not (root / REGISTER).is_file()
    if created:
        register = Register(root / REGISTER, "", existing_numbers(root))
        register.prefix = value("Number prefix, kept in the register (empty for none)", args.prefix, "").strip()
    else:
        register = load_register(root)

    title = value("Title", args.title, "").strip()
    if not title:
        raise NewError("A title is needed (--title)")
    kind = value("Type code, such as TN (empty for none)", args.kind, "").strip().upper()
    if not _CODE.match(kind) or not _CODE.match(register.prefix):
        raise NewError("The prefix and type may only have letters and digits")
    fmt = value("Word or PowerPoint (docx or pptx)", args.format, "docx").strip().lower()
    if fmt not in FORMATS:
        raise NewError(f"'{fmt}' is not docx or pptx")
    author = value("Author", args.author, _git_name()).strip()
    classification = value("Classification", args.classification, "").strip()
    description = value("Description", args.description, "").strip()

    number = register.next_number(kind)
    stem = _stem(number, title)
    build, source = folder / f"{stem}.yaml", folder / f"{stem}.md"
    for path in (build, source):
        if path.exists():
            raise NewError(f"{path} already exists")
    meta = {
        "title": title, "author": author, "version": "0.1.0", "date": f"{today.day} {today:%B %Y}",
        "description": description, "document_number": number, "classification": classification,
    }  # fmt: skip
    folder.mkdir(parents=True, exist_ok=True)
    source.write_text(f"# {title}\n\nWrite the document here.\n", encoding="utf-8")
    build.write_text(build_file(meta, f"{stem}.{fmt}", fmt, source.name), encoding="utf-8")
    register.entries = [*(register.entries or []), Entry(number, title, Path(os.path.relpath(build, root)).as_posix())]
    register.save()
    return [build, source], register, created


def run_new(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 made, 1 nothing made."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    ask = None if args.yes or not sys.stdin.isatty() else input
    try:
        written, register, created = make(Path.cwd(), args, ask, datetime.date.today())
    except NewError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: cannot write: {exc.strerror or exc}", file=sys.stderr)
        return 1
    shown = Path(os.path.relpath(register.path))
    if created:
        print(f"made      {shown} with {len(register.entries) - 1} existing number(s)")
    for path in written:
        print(f"written   {path.name}")
    print(f"number    {register.entries[-1].number}, recorded in {shown}")
    print(f"\nNext: commit {REGISTER} with the new files, then `py-doc build --legacy {written[0].name}`")
    return 0
