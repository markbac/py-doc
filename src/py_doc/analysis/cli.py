"""``py-doc stats``, ``py-doc check`` and ``py-doc diff``."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from py_doc._logging import configure_logging
from py_doc.config import ConfigError, ProjectConfig, find_config, load_config
from py_doc.errors import ConversionError
from py_doc.files import find_markdown
from py_doc.lint import DocLinter
from py_doc.lint.cli import exit_status, render
from py_doc.lint.linter import LintTargetError
from py_doc.markdown import ParseError
from py_doc.runtime import RuntimeSettings, connect

from .diff import diff_markdown
from .stats import FileStats, file_stats

logger = logging.getLogger(__name__)


def _shown(path: Path) -> str:
    try:
        return Path(os.path.relpath(path)).as_posix()
    except ValueError:  # another drive on Windows
        return path.as_posix()


def _noise(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")
    group.add_argument("-v", "--verbose", action="store_true", help="Show debug detail")


def _project(config_arg: str | None, start: Path) -> ProjectConfig | None:
    path = Path(config_arg) if config_arg else find_config(start)
    return load_config(path) if path else None


def _sources(project: ProjectConfig, name: str) -> list[Path]:
    return [s.file for s in project.documents[name].sources if s.include and s.structurizr is None]


# --- stats ---------------------------------------------------------------------------------------

STATS_EXAMPLES = """examples:
  py-doc stats                  each document of the nearest py-doc.yml, and the total
  py-doc stats docs README.md   each Markdown file named or below a folder
  py-doc stats --lint --format json"""

_COLUMNS = ("words", "headings", "code_blocks", "tables", "images", "links", "lint_issues")


def run_stats(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc stats", description="Count the words, headings, code blocks, tables, pictures and links of documents or files",
        epilog=STATS_EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("targets", nargs="*", metavar="TARGET", help="Documents of py-doc.yml, or Markdown files and folders (default: every document)")
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    parser.add_argument("--lint", action="store_true", help="Also count the lint issues of each")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="text, a table (default), or json")
    _noise(parser)
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        project = _project(args.config, Path.cwd())
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    groups: dict[str, list[Path]] = {}
    for target in args.targets or ([] if project is None else project.own_documents):
        if project is not None and target in project.documents:
            groups[target] = _sources(project, target)
        elif Path(target).is_dir():
            exclude = project.lint.exclude_dirs if project else DocLinter().config.exclude_dirs
            groups.update({_shown(f): [f] for f in find_markdown(Path(target).resolve(), exclude)})
        elif Path(target).is_file():
            groups[_shown(Path(target))] = [Path(target).resolve()]
        else:
            print(f"Error: {target} is not a document of py-doc.yml, a file or a folder", file=sys.stderr)
            return 2
    if not groups:
        print("Error: nothing to count. Name files or folders, or run it beside a py-doc.yml with documents", file=sys.stderr)
        return 2

    issues: dict[Path, int] = {}
    if args.lint:
        linter = DocLinter(config=project.lint if project else None, runtime=lambda: connect(project.runtime if project else RuntimeSettings()))
        try:
            report = linter.lint_paths(sorted({f for files in groups.values() for f in files if f.is_file()}))
        except (LintTargetError, ConversionError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        for issue in report.issues:
            issues[issue.file] = issues.get(issue.file, 0) + 1

    rows: dict[str, FileStats] = {}
    for name, files in groups.items():
        total = FileStats(lint_issues=0 if args.lint else None)
        for file in files:
            try:
                total = total + file_stats(file)
            except (OSError, UnicodeDecodeError, ParseError) as exc:
                print(f"Error: {_shown(file)}: {exc}", file=sys.stderr)
                return 2
            if args.lint:
                total.lint_issues += issues.get(file.resolve(), 0)
        rows[name] = total
    grand = FileStats(lint_issues=0 if args.lint else None)
    for row in rows.values():
        grand = grand + row

    if args.format == "json":
        print(json.dumps({"items": {k: v.as_dict() for k, v in rows.items()}, "total": grand.as_dict()}, indent=2))
        return 0
    columns = [c for c in _COLUMNS if c != "lint_issues" or args.lint]
    width = max(len(name) for name in [*rows, "total"])
    print(f"{'':<{width}}  " + "  ".join(f"{c.replace('_', ' '):>11}" for c in columns))
    for name, row in [*rows.items(), ("total", grand)]:
        print(f"{name:<{width}}  " + "  ".join(f"{getattr(row, c):>11}" for c in columns))
    return 0


# --- check ---------------------------------------------------------------------------------------

CHECK_EXAMPLES = """examples:
  py-doc check                  the configuration, every source and template, and lint
  py-doc check --strict         also fail on lint warnings (for CI)
  py-doc check --format sarif --output check.sarif"""


def check_project(project: ProjectConfig) -> list[str]:
    """Problems that would stop a build, found without building: missing sources, templates and site documents."""
    problems: list[str] = []
    for name, doc in project.documents.items():
        for source in doc.sources:
            if source.include and not source.file.exists():
                problems.append(f"documents.{name}: source {_shown(source.file)} is not there")
        for fmt, settings in doc.outputs.items():
            template = settings.template or (project.outputs.get(fmt).template if project.outputs.get(fmt) else None)
            if template is not None and not template.exists() and not settings.options.get("allow_missing_template"):
                problems.append(f"documents.{name}: the {fmt} template {_shown(template)} is not there")
    for fmt, settings in project.outputs.items():
        if settings.template is not None and not settings.template.exists() and not settings.options.get("allow_missing_template"):
            problems.append(f"outputs.{fmt}: the template {_shown(settings.template)} is not there")
    if project.site is not None:
        from py_doc.site import engine_for

        if not engine_for(project.site.engine, project.site.dir).exists():
            problems.append(f"site: there is no {project.site.engine} site in {_shown(project.site.dir)}. Run `py-doc site init`")
    return problems


def run_check(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc check", description="Check a documentation project without building it: py-doc.yml, sources, templates, the site and lint",
        epilog=CHECK_EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    parser.add_argument("--strict", action="store_true", help="Fail on lint warnings too")
    parser.add_argument("--no-lint", action="store_true", help="Check only the project, not the writing")
    parser.add_argument("--engine", choices=("auto", "builtin", "vale"), default="auto", help="Lint engine, as for py-doc lint")
    parser.add_argument("--format", choices=("text", "json", "sarif", "github", "csv"), default="text", help="How lint issues are written")
    parser.add_argument("--output", metavar="FILE", help="Write the lint issues to this file")
    _noise(parser)
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        project = _project(args.config, Path.cwd())
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if project is None:
        print("Error: No py-doc.yml found here or in a parent folder", file=sys.stderr)
        return 1
    problems = check_project(project)
    for problem in problems:
        print(f"Error: {problem}", file=sys.stderr)
    status = 1 if problems else 0
    if not args.no_lint:
        generated = {spec.output.resolve() for spec in project.generators}  # written by tools, not people
        files = sorted({f.resolve() for name in project.own_documents for f in _sources(project, name) if f.exists()} - generated)
        if files:
            linter = DocLinter(config=project.lint, runtime=lambda: connect(project.runtime), engine=args.engine)
            try:
                report = linter.lint_paths(files)
            except (LintTargetError, ConversionError) as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 2
            text = render(report, args.format)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(text, encoding="utf-8")
            else:
                print(text, end="")
            for result in report.errors:
                print(f"Error: {_shown(result.file)}: {result.error}", file=sys.stderr)
            status = max(status, exit_status(report, args.strict))
            lint_summary = f"{len(report.issues)} lint issue(s) in {report.files_scanned} file(s)"
        else:
            lint_summary = "no sources to lint"
    else:
        lint_summary = "lint skipped"
    print(f"\n[SUMMARY] {len(project.documents)} document(s), {len(problems)} project problem(s), {lint_summary}", file=sys.stderr)
    return status


# --- diff ----------------------------------------------------------------------------------------

DIFF_EXAMPLES = """examples:
  py-doc diff old/guide.md docs/guide.md     two versions of one file
  py-doc diff --rev main                     every source of py-doc.yml against the main branch
  py-doc diff --rev v1.0 docs/guide          the Markdown files below a folder against a tag
  py-doc diff --rev HEAD~1 --format json"""


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise ConversionError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def run_diff(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="py-doc diff", description="Compare two versions of Markdown documents by section: added, removed, renamed, moved and changed",
        epilog=DIFF_EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter,
    )  # fmt: skip
    parser.add_argument("paths", nargs="*", metavar="PATH", help="OLD NEW files, or with --rev the files and folders to compare (default: the sources of py-doc.yml)")
    parser.add_argument("--rev", metavar="REVISION", help="Compare the working files with this Git revision")
    parser.add_argument("-c", "--config", help="Configuration file (default: the nearest py-doc.yml)")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="text, a list per file (default), or json")
    parser.add_argument("--exit-code", action="store_true", help="Exit with status 1 when anything changed")
    _noise(parser)
    args = parser.parse_args(argv)
    configure_logging(quiet=args.quiet, verbose=args.verbose)
    try:
        pairs = _diff_pairs(args)
    except (ConfigError, ConversionError, OSError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    results = []
    for name, old, new in pairs:
        try:
            changes = diff_markdown(old, new)
        except ParseError as exc:
            print(f"Error: {name}: {exc}", file=sys.stderr)
            return 2
        if changes:
            results.append((name, changes))
    if args.format == "json":
        print(json.dumps({name: [c.as_dict() for c in changes] for name, changes in results}, indent=2))
    else:
        for name, changes in results:
            print(name)
            for change in changes:
                print(f"  {change.describe()}")
        print(f"\n[SUMMARY] {len(pairs)} file(s) compared, {len(results)} changed, {sum(len(c) for _, c in results)} section change(s)", file=sys.stderr)
    return 1 if args.exit_code and results else 0


def _diff_pairs(args: argparse.Namespace) -> list[tuple[str, str, str]]:
    """(name, old text, new text) of each file to compare. A file that is new or gone compares with empty text."""
    if args.rev is None:
        if len(args.paths) != 2:
            raise ConversionError("Give two files, OLD and NEW, or --rev REVISION")
        old, new = (Path(p) for p in args.paths)
        return [(_shown(new), old.read_text(encoding="utf-8-sig"), new.read_text(encoding="utf-8-sig"))]
    top = Path(_git(["rev-parse", "--show-toplevel"], Path.cwd()).strip())
    files: list[Path] = []
    if args.paths:
        for raw in args.paths:
            path = Path(raw).resolve()
            files += find_markdown(path, DocLinter().config.exclude_dirs) if path.is_dir() else [path]
    else:
        project = _project(args.config, Path.cwd())
        if project is None:
            raise ConversionError("Name the files to compare, or run it beside a py-doc.yml")
        files = [f.resolve() for name in project.own_documents for f in _sources(project, name)]
        # Files the revision had that are gone now: the ones under the same folders, listed by git
        folders = sorted({f.parent for f in files})
        listed = _git(["ls-tree", "-r", "--name-only", args.rev, "--", *[str(d.relative_to(top).as_posix()) for d in folders if d.is_relative_to(top)]], top)
        files += [top / line for line in listed.splitlines() if line.lower().endswith((".md", ".markdown"))]
    pairs = []
    for file in dict.fromkeys(files):
        relative = file.resolve().relative_to(top).as_posix() if file.resolve().is_relative_to(top) else None
        if relative is None:
            raise ConversionError(f"{file} is not in the Git repository {top}")
        try:
            old = _git(["show", f"{args.rev}:{relative}"], top)
        except ConversionError:
            old = ""  # not in that revision: every section is added
        new = file.read_text(encoding="utf-8-sig") if file.is_file() else ""
        pairs.append((_shown(file), old, new))
    return pairs
