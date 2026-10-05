# py-doc: Markdown technical documentation tools

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

`py-doc` turns Markdown technical documentation into **Word (`.docx`)** documents and **PowerPoint (`.pptx`)** decks, checks its writing quality, and builds whole sets of documents from one `py-doc.yml`. It replaces three earlier tools (`py-doc2docx`, `py-doc2slides`, `py-doclint`) and the `createdocs` build files from `markbac/technical-documentation`.

All of it works from one parsed document tree, so the converters and the linter agree on what the Markdown means.

## Commands

| Command | What it does |
|---|---|
| `py-doc docx` | Convert Markdown to Word |
| `py-doc slides` | Convert Markdown to PowerPoint |
| `py-doc lint` | Check writing style, glossary terms and acronyms |
| `py-doc build` | Build every document described in `py-doc.yml` |
| `py-doc migrate` | Create `py-doc.yml` from legacy `createdocs` build files |

The old commands `py-doc2docx`, `py-doc2slides` and `py-doclint` still work and print a one-line note naming their replacement. `-q` hides the note. The old import names `pydoc2docx`, `pydoc2slides` and `pydoclint` also still work.

## Installation

```bash
git clone https://github.com/markbac/py-doc2docx.git
cd py-doc2docx

# Needs Python 3.10 or later. ctxlogkit is installed from GitHub automatically.
pip install -e .

# With development tools (pytest, ruff, build, twine)
pip install -e ".[dev]"
```

## Converting files

```bash
py-doc docx Technical_Specification.md -o Technical_Specification.docx
py-doc docx Technical_Specification.md -t Template.docx
py-doc docx docs/ -o dist/docx/              # a whole folder, structure kept

py-doc slides talk.md -o talk.pptx
py-doc slides talk.md -t Corporate.pptx --split-level 1
```

The same options work with the old command names (`py-doc2docx`, `py-doc2slides`).

| Option | Commands | Description |
|---|---|---|
| `input` | both | A Markdown file, or a folder searched for `.md` and `.markdown` files in any capitalisation |
| `-o`, `--output` | both | The output file, or a folder. A folder (an existing one, or a path ending in `/`) gets `<name>.docx` or `<name>.pptx` inside it |
| `-t`, `--template` | both | A reference `.docx` or `.dotx` (Word), or `.pptx` or `.potx` (PowerPoint). `-r`, `--reference` is the old slides name |
| `--allow-missing-template` | both | Warn and use a blank document if the template file is missing (default: fail) |
| `--keep-template-body` | docx | Keep the template's own content and append the converted document after it |
| `--keep-template-slides` | slides | Keep the template's own slides and add the converted ones after them |
| `--split-level N` | slides | Start a new slide at each heading up to level N (default 2) |
| `--title-layout`, `--content-layout` | slides | Name the template layouts to use |
| `-q`, `-v` | both | Only warnings and errors, or debug detail |
| `--version` | both | Print the version |

Behaviour that applies to a folder:

- Hidden folders and `node_modules`, `venv`, `env`, `site-packages`, `__pycache__`, `dist`, `build` and `vendor` are skipped, and so is an output folder inside the input.
- One bad file does not stop the rest. Each failure is printed on stderr, a summary follows, and the exit status is `1` if anything failed.
- Two sources that would write the same output (`a.md` and `a.markdown`) are refused before anything is converted.
- The input is checked before any folder is created, so a typo leaves nothing behind.

## Supported Markdown

Parsing follows CommonMark, plus tables. Each construct is written with a named Word style, so a reference template decides how it looks. A style the template lacks is created with a plain default.

| Markdown | Word output |
|---|---|
| Headings, levels 1 to 6 | `Heading 1` to `Heading 6`. A closing `#` sequence is removed, and an empty heading is skipped |
| Paragraphs | `Normal`. Soft line breaks become spaces, hard breaks become line breaks |
| Strong, emphasis, inline code | Bold, italic, and a `Consolas` run |
| Links, autolinks, reference links | Word hyperlinks, with the title as the tooltip |
| Images | A local picture is embedded, scaled to the page width, with its alt text. Anything else (a web address, a missing file, an unsupported format) becomes `[Image: alt text]` linked to the address, with a warning |
| Bullet and numbered lists | `List Bullet` and `List Number`, with `2` and `3` for nested levels (deeper levels stay at 3). Further paragraphs in an item use `List Continue` |
| Tables | A Word table in `Table Grid` style. The header row is bold and column alignment is kept |
| Block quotes | `Quote`. Nested quotes are indented further. Lists and code inside a quote keep their own styles |
| Fenced and indented code | `Code`. The language on a fence is not shown |
| Thematic breaks | An empty paragraph with a bottom border |
| Raw HTML | Shown as written, because Word cannot render it |
| Front matter | Not rendered. Title, author, keywords and similar keys become the document properties |

> **Note:** Markdown the parser does not know raises `ConversionError` instead of being dropped, so content never disappears silently. Task-list checkboxes, strikethrough and footnotes are not CommonMark and appear as literal text.

> **Note:** Markdown the parser does not know raises `ConversionError` instead of being dropped, so content never disappears silently. Task-list checkboxes, strikethrough and footnotes are not CommonMark and appear as literal text.

### Word templates

A template supplies styles, page setup, headers, footers and properties. Its body is removed unless you pass `--keep-template-body`. The converter writes each construct with a named style: `Normal`, `Heading 1` to `Heading 6`, `List Bullet` and `List Number` (with `2` and `3` added for nested levels), `List Continue`, `Quote`, `Table Grid` and `Code`. A style the template lacks is created with plain defaults, and one warning lists all of them so a template can be fixed in one pass. `Code` is optional and never reported. List styles created this way have no bullet or number, because numbering lives in the template.

## PowerPoint output

Slides are cut at a thematic break (`---`) and at headings up to `--split-level`. The first heading of a slide is its title, and a slide without one is called `Slide N`.

- **Title slide**: the first slide is a title slide when it has a title, and it has either front matter lines (subtitle, author, date) or at most one paragraph of body text. Other content follows on a `(continued)` slide.
- **Body**: paragraphs, bullets (nested up to nine levels), numbered lists (keeping their start number) and code (`Consolas`) go in the body placeholder. Block quotes are italic and indented.
- **Tables and pictures** are placed below the text without overlapping it, and pictures are scaled to fit. A picture that cannot be embedded stays as `[Image: alt]` with a warning.
- **Speaker notes**: write `<!-- notes: text -->`. Other HTML comments are dropped.
- **Long slides**: a slide with more than 16 lines gets a warning, because nothing is shrunk silently.

A PowerPoint template needs a layout with a title and a subtitle placeholder for the title slide (optional, with a warning if missing) and a layout with a title and a body placeholder for content slides. `Title Slide` and `Title and Content` are used when present, otherwise the first layout with the right placeholders. Name others with `--title-layout` and `--content-layout`. The template's own slides are removed unless you pass `--keep-template-slides`.

## Linting

`py-doc lint` (also `py-doclint`) checks Markdown for writing quality. It runs on the shared document tree, so code blocks, inline code, HTML, link destinations and front matter are never treated as prose, and URLs and file names written as plain text are skipped.

```bash
py-doc lint docs/             # lint a directory (default: the current one)
py-doc lint docs/Guide.md     # lint one file
py-doc lint docs/ --strict    # exit 1 if any warning or error is reported
py-doc lint . --exclude drafts
```

| Rule | Category | Default severity | What it reports |
|---|---|---|---|
| `DOC001` | Glossary | warning | A glossary term written differently from its canonical form, in any capitalisation (`mQTT`), plus listed misspellings (`Lw2m`) |
| `DOC002` | Style | warning | Wordy phrases such as "in order to", also when wrapped over two lines, with a shorter wording suggested |
| `DOC003` | Acronym | info | The first use of an all-capitals acronym that is never defined, or is defined only later |

- **Acronym definitions** are recognised in both orders, `Pre-Shared Key (PSK)` and `PSK (Pre-Shared Key)`, including mixed-case forms such as `LwM2M` and `IoT`. The words must spell out the acronym. Words in the built-in allow-list and glossary terms need no definition.
- **Directories**: hidden directories and `node_modules`, `venv`, `env`, `site-packages`, `__pycache__`, `dist`, `build` and `vendor` are skipped. `.md` and `.markdown` files are found in any capitalisation. Paths are printed relative to the working directory.
- **Exit status**: `0` when clean, or when only info is reported, or when warnings are reported without `--strict`. `1` for any issue the configuration calls an error, or with `--strict` and at least one warning. `2` when the target is missing or not Markdown, or when any file cannot be read, so an error is never mistaken for a clean result.
- **Limits**: issues carry a line number but no column, because the document tree records lines only. Terms inside a URL, a dotted or slashed name such as `lwm2m/dtls`, or code are not checked.

```python
from py_doc.lint import DocLinter

report = DocLinter().lint_path("docs")
for issue in report.issues:
    print(issue)  # docs/Guide.md:12: warning DOC001 [Glossary] ...
print(report.files_scanned, "files scanned,", len(report.errors), "could not be read")
```

## Project configuration (`py-doc.yml`)

One file describes documents, outputs and lint policy. `py-doc build` and `py-doc lint` find the nearest `py-doc.yml` above the current folder (or take `--config`). Paths are relative to the file. Every key is checked, so a typo is an error that names its place, such as `documents.guide.sources[1].page_brek`.

```yaml
project:
  name: Technical documentation

outputs:                       # defaults for every document
  docx:
    template: templates/Template.docx
    dir: build                 # where documents go unless they set a path
  pptx:
    split_level: 2

documents:
  c4-guide:
    title: C4 Architecture Modelling
    author: Mark Bacon
    version: "1.0.4"
    document_number: GD-001
    status: Proposed
    keywords: [architecture, C4]
    sources:
      - index.md
      - file: 01-foundations.md
        heading_offset: 0      # shift every heading level (kept within 1 to 6)
        page_break: true       # start on a new page, or a new slide
        title: Foundations     # replaces the first heading, or adds one
      - {file: draft.md, include: false}
    outputs:
      docx: {path: build/guides/c4-guide.docx}
      pptx: {}                 # also build a deck

lint:
  exclude: [drafts]
  rules:
    DOC001: error              # error, warning, info or off
    DOC002: off
  glossary:
    Kubernetes: [k8s]
  phrases:
    utilise: use
  acronyms:
    min_length: 3
    allowed: [SBOM]
```

- **Documents** join their sources in order. Properties come from the configuration, then from the first source's front matter. A document builds the formats listed under `outputs`, or Word if none is listed.
- **Output options** per format: `template`, `allow_missing_template`, `keep_template_body` (docx), `keep_template_slides`, `split_level`, `title_layout`, `content_layout` (pptx). A document's value overrides the default.
- **Lint** settings extend the built-in glossary, phrases and allowed acronyms. An issue whose rule is set to `error` fails `py-doc lint` even without `--strict`.
- **Reserved**: `collections`, `bundles`, `content` and `site` are accepted and kept, with a warning, because nothing uses them yet. `variables` and `conditions` on a document are also kept but not applied.

```bash
py-doc build                      # every document
py-doc build c4-guide -f pptx     # one document, one format
```

## Migrating from createdocs

```bash
py-doc migrate docs/ --check      # report only
py-doc migrate docs/              # write py-doc.yml
py-doc migrate docs/ --backup     # also keep .bak copies of the originals and any old py-doc.yml
```

Each `createdocs` YAML file becomes one document, so folders, sources, templates and shared chapters keep their relations. A template used by every Word document is set once under `outputs`. YAML files that are not build files (such as `mkdocs.yml`) are listed as skipped, and the originals are never changed or deleted. An existing output file is not replaced unless you pass `--backup` or `--force`.

The report lists what has no equivalent yet, so nothing is lost quietly:

- PDF, HTML and processed Markdown output, PlantUML and ditaa rendering, and the other build switches for them.
- The template chosen from the document status, and the version added to the output file name. `py-doc` writes exactly the path you give.
- Unknown `meta` and `entries` keys. `variables` and `conditions` are kept but not applied.

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

## Layout

```
src/
├── py_doc/
│   ├── app.py            # the py-doc command
│   ├── cli.py            # py-doc2docx and py-doc docx
│   ├── slides_cli.py     # py-doc2slides and py-doc slides
│   ├── _cli.py           # options, output paths and batch conversion shared by both
│   ├── config.py         # py-doc.yml model and validation
│   ├── build.py          # joins a document's sources and renders it
│   ├── migrate.py        # createdocs to py-doc.yml
│   ├── files.py          # finding Markdown, writing outputs, template types
│   ├── markdown/         # parser, document tree (AST) and front matter
│   ├── render/           # docx.py and pptx.py walk the tree
│   └── lint/             # rules, linter and py-doclint command line
├── pydoc2docx/           # old import names, kept as aliases
├── pydoc2slides/
└── pydoclint/
tests/                    # semantic, golden-output, command line and migration tests
```

## Running tests

```bash
python -m pytest
ruff check .
```

CI runs on Linux with Python 3.10 to 3.14, and on Windows and macOS with the oldest and newest.

## License

Licensed under the [MIT License](LICENSE).
