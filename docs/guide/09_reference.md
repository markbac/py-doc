---
title: Reference
---

# Reference

## Migrating from createdocs

```bash
py-doc migrate docs/ --check      # report only
py-doc migrate docs/              # write py-doc.yml
py-doc migrate docs/ --backup     # also keep .bak copies of the originals and any old py-doc.yml
py-doc build --legacy docs/guide.yaml         # build one createdocs file as it is, without writing py-doc.yml
```

Each `createdocs` YAML file becomes one document, so folders, sources, templates and shared chapters keep their relations. A template used by every Word document is set once under `outputs`. YAML files that are not build files (such as `mkdocs.yml`) are listed as skipped, and the originals are never changed or deleted. An existing output file is not replaced unless you pass `--backup` or `--force`.

`py-doc build --legacy FILE` reads one `createdocs` file the same way and builds it straight away, so old build files keep working while you move over. The findings `migrate` would report are shown as warnings. The output format comes from the `emit-*` switches, else from the extension of `cli.output` (`.docx`, `.pptx`, `.pdf` or `.html`). `cli.template` goes to the PowerPoint output when it is a `.pptx` file, else to the Word output. An entry's `section` is taken as its `title`: it replaces the first heading of that file.

### New legacy documents

```bash
py-doc new                                   # asks for the title, type, format, author, classification and description
py-doc new --title "Build and Release Pipelines" --type TN --format docx -y
```

`py-doc new` writes a build file and its Markdown in the current folder, named after the number and the title (`G460-TN-013-Build-and-Release-Pipelines.yaml` and `.md`), ready for `py-doc build --legacy`. Every question has an option, and `-y` asks nothing. The author defaults to `git config user.name`, the date to today and the version to `0.1.0`. A file that is already there is never replaced.

The number comes from `doc-numbers.yml` at the repository root, found from any folder below it:

```yaml
prefix: G460
documents:
  - number: G460-TN-012
    title: Build and Release Pipelines
    file: docs/notes/G460-TN-012-build-and-release-pipelines.yaml
```

A number is `[prefix-][type-]NNN`. The prefix is set once in the register and the type is asked each time; either may be empty. `NNN` is one counter for every type, one more than the highest number in the register, so `G460-TN-012` and `G460-OV-012` cannot both be given out. The first `py-doc new` in a repository makes the register from the `document_number` of the legacy build files already there, and asks for the prefix. Commit the register with the new document: two people who take a number on separate branches then get a merge conflict in the register, not two documents with the same number.

Two options keep the register up to date and make no document:

```bash
py-doc new --scan               # add the legacy build files that are not in the register yet
py-doc new --scan --start 100   # and begin new numbers at 100
```

`--scan` adds every legacy build file below the repository root whose file is not in the register, even when its number is already taken, and lists each number used by more than one file as a clash. Fix those by hand: py-doc never renumbers a document. `--start N` is kept in the register as `start: N`. New numbers then begin at `N` and step over any number a document already has, so they stay unique however the old ones were given out. Without it, the next number is one more than the highest.

The `Setup-DocTools.ps1` script that installed pandoc, TeX and the diagram tools on Windows is no longer needed: the tools run in the tool container. Use `py-doc setup` (Docker Engine in WSL), then `py-doc tools build` and `py-doc doctor`.

The report lists what has no equivalent yet, so nothing is lost quietly:

- processed Markdown output and the build switches for it;
- the template chosen from the document status, and the version added to the output file name;
- unknown `meta` and `entries` keys.

## Python API

```python
from pathlib import Path
from py_doc import DocxConverter, SlidesConverter
from py_doc.config import load_config
from py_doc.build import build_document
from py_doc.lint import DocLinter

DocxConverter(template_path=Path("Template.docx")).convert_file(Path("a.md"), Path("out/a.docx"))
SlidesConverter(split_level=1).convert_file(Path("a.md"), Path("out/a.pptx"))

config = load_config(Path("py-doc.yml"))
build_document(config, config.documents["c4-guide"])

for issue in DocLinter().lint_path("docs").issues:
    print(issue)
```

Failures raise `py_doc.ConversionError` (unreadable or unsupported input, bad template, unwritable output) or `FileNotFoundError` (missing input or template). The library only uses the standard `logging` module and never configures it. The command line tools configure it with [ctxlogkit](https://github.com/markbac/py-logkit): progress on stderr, colour on a terminal only.

## Exit statuses

| Status | Meaning |
|---|---|
| `0` | Done, or only info and (without `--strict`) warnings reported |
| `1` | A document, file, diagram or tool failed, the configuration is wrong, an output exists and was not replaced, or lint found an error (or a warning with `--strict`) |
| `2` | The environment: no Docker, no image, an unsupported platform, a file that is not Word or PowerPoint, or a lint target that is missing or unreadable |

## Old names

The commands `py-doc2docx`, `py-doc2slides`, `py-doclint` and `py-c4-exporter` still work and print a one-line note naming their replacement. `-q` hides the note. The old import names `pydoc2docx`, `pydoc2slides` and `pydoclint` also still work.

## Troubleshooting

- **Exit status `2`** means the environment: Docker is not running or the image is not built. Run `py-doc doctor`.
- **Exit status `1`** means a tool ran and failed. Its whole output is shown above the error.
- **A diagram error** names the file, the line and the tool's own message. `py-doc build --keep-going` lists every failing diagram together.
- **Structurizr Local does not answer**: check that Docker is running and that port 8080 is free (`c4.port` changes it), then run `py-doc c4 down` and try again.
- **Caches**: generated pages and exports live in `.py-doc/` at the project root, and pictures in your user cache folder. Both are safe to delete.

## Running the tests

```bash
python -m pytest
ruff check .
```

The tests run pandoc, Graphviz and XeLaTeX on the host in place of the container when they are installed, and skip what they cannot run. CI runs on Linux and Windows with Python 3.10 and 3.14, the oldest and newest supported. macOS is not supported.
