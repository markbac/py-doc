"""``py-doc new``: start one document in the legacy build file format, with a number from the register.

Given an existing Markdown file, it writes only the build file, beside it, and leaves the Markdown as it is.

The register is ``doc-numbers.yml`` in the repository root. It lists every number given out, with the
title and the build file, so two documents never get the same number. Committing it with the new
document makes a clash between branches show as a merge conflict. When there is no register yet, it is
made from the ``document_number`` of the legacy build files already in the repository.

A number is ``[PREFIX-][TYPE-]NNN``. The prefix (``G460``) is set once in the register and the type
(``TN``) is asked each time; both may be empty. ``NNN`` is one counter for every type: one more than the
highest in the register, or with ``start`` set, the first from there that no document has.

The register may also list the allowed ``prefixes``, ``types`` and ``classifications``. A value must then
be one of the list (the register's spelling is used); without a list anything goes.

``--scan`` adds the legacy build files that are not in the register yet, numbers that clash included
(they are listed), and ``--start N`` sets where new numbers begin. Neither makes a document.
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
from .platform import restore_console_input
from .migrate import discover, read_createdocs

REGISTER = "doc-numbers.yml"
REGISTER_HEADER = (
    "# Document numbers given out by `py-doc new`. Commit this file with the new document, so the\n"
    "# next number cannot be taken twice. A number is [prefix-][type-]NNN, one counter for every type.\n"
)
FORMATS = {"docx": "Word", "pptx": "PowerPoint"}
_SEQUENCE = re.compile(r"(\d+)$")
_CODE = re.compile(r"^[A-Za-z0-9]*$")
LISTS = {"prefixes": "G460, G470", "types": "TN, OV, SP", "classifications": "Confidential, Internal"}  # with an example


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
    start: int | None = None
    allowed: dict[str, list[str]] | None = None  # prefixes, types, classifications: the only values allowed

    def next_number(self, kind: str, prefix: str | None = None) -> str:
        found = [m for m in (_SEQUENCE.search(e.number) for e in self.entries or []) if m]
        used = {int(m[1]) for m in found}
        digits = max([3, *(len(m[1]) for m in found)])
        sequence = self.start if self.start is not None else max(used, default=0) + 1
        while sequence in used:
            sequence += 1
        prefix = self.prefix if prefix is None else prefix
        return "-".join(part for part in (prefix, kind, f"{sequence:0{digits}d}") if part)

    def clashes(self) -> dict[str, list[str]]:
        """Numbers held by more than one file."""
        files: dict[str, list[str]] = {}
        for entry in self.entries or []:
            files.setdefault(entry.number, []).append(entry.file)
        return {number: names for number, names in files.items() if len(names) > 1}

    def save(self) -> None:
        data: dict = {"prefix": self.prefix}
        if self.start is not None:
            data["start"] = self.start
        data.update({key: values for key, values in (self.allowed or {}).items() if values})
        data["documents"] = [vars(e) for e in self.entries or []]
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
    start = data.get("start")
    if start is not None and (not isinstance(start, int) or isinstance(start, bool) or start < 1):
        raise NewError(f"{path}: start must be a whole number from 1")
    allowed = {}
    for key in LISTS:
        values = data.get(key)
        if values is None:
            continue
        if not isinstance(values, list) or not all(isinstance(v, (str, int)) and str(v).strip() for v in values):
            raise NewError(f"{path}: {key} must be a list of values, such as [{LISTS[key]}]")
        allowed[key] = [str(v).strip() for v in values]
    return Register(path, str(data.get("prefix") or ""), entries, start, allowed)


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


NEW_EXAMPLES = """examples:
  py-doc new                                   ask for everything
  py-doc new -y --title "Meter Wakeup" --type TN --classification Confidential
  py-doc new --title "Overview" --type OV --format pptx
  py-doc new notes/pump-control.md --type TN   number an existing Markdown file
  py-doc new --scan                            add existing build files to the register
  py-doc new --scan --start 100                and begin new numbers at 100"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-doc new",
        description="Start a document here: a legacy build file and its Markdown, with the next number from "
        "doc-numbers.yml at the repository root. What is not given is asked, unless -y is set or there is no terminal",
        epilog=NEW_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "markdown", nargs="?", type=Path, metavar="FILE.md",
        help="An existing Markdown file to number: its build file is written beside it, and the file is not changed",
    )  # fmt: skip
    parser.add_argument("--title", help="The document title (needed; default for FILE.md: its front matter title or first heading)")
    parser.add_argument("--type", dest="kind", help="The type code in the number, such as TN: one of the register's types when it lists them, else anything or empty")
    parser.add_argument("--format", choices=sorted(FORMATS), help="Word (docx) or PowerPoint (pptx). Default: docx")
    parser.add_argument("--author", help="Default: git config user.name")
    parser.add_argument("--classification", help="Such as Confidential: one of the register's classifications when it lists them, else anything")
    parser.add_argument("--description", help="One sentence on what the document covers")
    parser.add_argument(
        "--prefix",
        help="The number prefix, such as G460 (default: the register's prefix). One of its prefixes when it lists them. "
        "When the register is made, it becomes its default",
    )
    parser.add_argument("--scan", action="store_true", help="Add the legacy build files not in the register yet (clashes included), and make no document")
    parser.add_argument("--start", type=int, metavar="N", help="New numbers begin at N, skipping any taken (kept in the register), and make no document")
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


def _chooser(ask: Callable[[str], str] | None):
    """A value that must be one of ``allowed`` when that is given (any case; the list's spelling is kept).

    A wrong answer is asked again; a wrong option, or a wrong answer with nobody to ask, is an error.
    """
    value = _asker(ask)

    def pick(question: str, given: str | None, default: str, allowed: list[str] | None, option: str) -> str:
        if not allowed:
            return value(question, given, default).strip()
        by_key = {item.upper(): item for item in allowed}
        listed = ", ".join(allowed)
        if given is not None:
            if given.strip().upper() not in by_key:
                raise NewError(f"{option} '{given}' is not in the register's list: {listed}")
            return by_key[given.strip().upper()]
        question = f"{question.split(',')[0].split(' (')[0]} ({listed})"
        while True:
            answer = value(question, None, default).strip()
            if answer.upper() in by_key:
                return by_key[answer.upper()]
            if ask is None:
                raise NewError(f"{option} is needed: one of {listed}")
            print(f"'{answer}' is not one of {listed}" if answer else f"Choose one of {listed}")

    return pick


@dataclass
class ExistingMarkdown:
    """What an existing Markdown file already says about itself, as defaults for the questions."""

    path: Path
    title: str = ""
    author: str = ""
    version: str = ""
    classification: str = ""
    description: str = ""


def _existing_markdown(path: Path) -> ExistingMarkdown:
    from .errors import ConversionError
    from .pandoc.source import first_heading, read_front_matter, split_front_matter

    path = path.resolve()
    if not path.is_file() or path.suffix.lower() not in (".md", ".markdown"):
        raise NewError(f"{path} is not a Markdown file")
    try:
        front, body = split_front_matter(path.read_text(encoding="utf-8-sig"))
        meta = read_front_matter(front, path)
    except (UnicodeDecodeError, ConversionError) as exc:
        raise NewError(f"Cannot read {path}: {exc}") from exc
    if meta.document_id:
        raise NewError(f"{path.name} already has the document number {meta.document_id} in its front matter")

    def extra(key: str) -> str:
        return str(meta.extra.get(key) or "").strip()

    return ExistingMarkdown(
        path, meta.title or first_heading(body) or "", meta.author or "", meta.version or "", extra("classification"), extra("description")
    )


def _not_registered(markdown: Path, register: Register, root: Path) -> None:
    """Refuse a Markdown file that a build file in the register already uses: it has a number."""
    for entry in register.entries or []:
        data = read_createdocs(root / entry.file) if entry.file else None
        for item in (data or {}).get("entries") or []:
            if ((root / entry.file).parent / str(item["file"])).resolve() == markdown:
                raise NewError(f"{markdown.name} is already a source of {entry.file}, number {entry.number}")


def make(folder: Path, args: argparse.Namespace, ask: Callable[[str], str] | None, today: datetime.date) -> tuple[list[Path], Register, bool]:
    """Write the build file and its Markdown in ``folder`` and record the number. Returns what was written.

    With ``args.markdown``, the build file goes beside that file and names it; the Markdown is not written.
    """
    value = _asker(ask)
    existing = _existing_markdown(args.markdown) if getattr(args, "markdown", None) else None
    if existing:
        folder = existing.path.parent
    root = find_root(folder)
    created = not (root / REGISTER).is_file()
    if created:
        register = Register(root / REGISTER, "", existing_numbers(root))
        register.prefix = value("Number prefix, kept in the register (empty for none)", args.prefix, "").strip()
    else:
        register = load_register(root)
    if existing:
        _not_registered(existing.path, register, root)

    allowed = register.allowed or {}
    pick = _chooser(ask)
    prefixes = allowed.get("prefixes")
    if prefixes:
        default = register.prefix if register.prefix.upper() in (p.upper() for p in prefixes) else prefixes[0]
        prefix = pick("Number prefix", args.prefix, default, prefixes, "--prefix")
    else:
        prefix = (register.prefix if args.prefix is None or created else args.prefix).strip()
    title = value("Title", args.title, existing.title if existing else "").strip()
    if not title:
        raise NewError("A title is needed (--title)")
    kind = pick("Type code, such as TN (empty for none)", args.kind, "", allowed.get("types"), "--type").upper()
    if not _CODE.match(kind) or not _CODE.match(prefix):
        raise NewError("The prefix and type may only have letters and digits")
    fmt = value("Word or PowerPoint (docx or pptx)", args.format, "docx").strip().lower()
    if fmt not in FORMATS:
        raise NewError(f"'{fmt}' is not docx or pptx")
    author = value("Author", args.author, (existing.author if existing else "") or _git_name()).strip()
    classification = pick(
        "Classification", args.classification, existing.classification if existing else "", allowed.get("classifications"), "--classification"
    )
    description = value("Description", args.description, existing.description if existing else "").strip()

    number = register.next_number(kind, prefix)
    stem = _stem(number, title)
    build = folder / f"{stem}.yaml"
    source = existing.path if existing else folder / f"{stem}.md"
    for path in (build,) if existing else (build, source):
        if path.exists():
            raise NewError(f"{path} already exists")
    meta = {
        "title": title, "author": author, "version": (existing.version if existing else "") or "0.1.0",
        "date": f"{today.day} {today:%B %Y}",
        "description": description, "document_number": number, "classification": classification,
    }  # fmt: skip
    folder.mkdir(parents=True, exist_ok=True)
    if not existing:
        source.write_text(f"# {title}\n\nWrite the document here.\n", encoding="utf-8")
    build.write_text(build_file(meta, f"{stem}.{fmt}", fmt, source.name), encoding="utf-8")
    register.entries = [*(register.entries or []), Entry(number, title, Path(os.path.relpath(build, root)).as_posix())]
    register.save()
    return ([build] if existing else [build, source]), register, created


def update(folder: Path, scan: bool, start: int | None, prefix: str | None) -> tuple[Register, list[Entry]]:
    """``--scan`` and ``--start``: bring the register up to date. Returns it and the entries added."""
    if start is not None and start < 1:
        raise NewError("--start must be 1 or more")
    root = find_root(folder)
    if (root / REGISTER).is_file():
        register = load_register(root)
    else:
        register = Register(root / REGISTER, prefix or "", [])
    added: list[Entry] = []
    if scan:
        known = {entry.file for entry in register.entries or []}
        added = [entry for entry in existing_numbers(root) if entry.file not in known]
        register.entries = [*(register.entries or []), *added]
    if start is not None:
        register.start = start
    register.save()
    return register, added


def _report_clashes(register: Register) -> None:
    for number, files in register.clashes().items():
        print(f"clash     {number} is used by {', '.join(files)}")


def run_new(argv: Sequence[str] | None = None) -> int:
    """Exit status: 0 made, 1 nothing made."""
    args = build_parser().parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    ask = None if args.yes or not sys.stdin.isatty() else input
    if ask:
        restore_console_input()
    if args.scan or args.start is not None:
        try:
            register, added = update(Path.cwd(), args.scan, args.start, args.prefix)
        except NewError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"Error: cannot write: {exc.strerror or exc}", file=sys.stderr)
            return 1
        for entry in added:
            print(f"added     {entry.number}  {entry.file}")
        _report_clashes(register)
        print(f"register  {os.path.relpath(register.path)}: {len(register.entries or [])} number(s), the next ends in {register.next_number('').rsplit('-', 1)[-1]}")
        return 0
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
        _report_clashes(register)
    for path in written:
        print(f"written   {Path(os.path.relpath(path))}")
    print(f"number    {register.entries[-1].number}, recorded in {shown}")
    print(f"\nNext: commit {REGISTER} with the new files, then `py-doc build --legacy {Path(os.path.relpath(written[0]))}`")
    return 0
