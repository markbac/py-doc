---
title: Reference
---

# Reference

## Migrating from createdocs

```bash
py-doc migrate docs/ --check      # report only
py-doc migrate docs/              # write py-doc.yml
py-doc migrate docs/ --backup     # also keep .bak copies of the originals and any old py-doc.yml
```

Each `createdocs` YAML file becomes one document, so folders, sources, templates and shared chapters keep their relations. A template used by every Word document is set once under `outputs`. YAML files that are not build files (such as `mkdocs.yml`) are listed as skipped, and the originals are never changed or deleted. An existing output file is not replaced unless you pass `--backup` or `--force`.

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

The tests run pandoc, Graphviz and XeLaTeX on the host in place of the container when they are installed, and skip what they cannot run. CI runs on Linux with Python 3.10 to 3.14, and on Windows with the oldest and newest. macOS is not supported.
