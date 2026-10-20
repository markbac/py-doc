# py-doc: Markdown technical documentation tools

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

`py-doc` turns Markdown technical documentation into **Word (`.docx`)** documents, **PowerPoint (`.pptx`)** decks, **PDF**, **HTML** and **web sites** (MkDocs or Astro + Starlight). It checks the writing, draws every common kind of diagram, writes and draws C4 architecture documentation from Structurizr models, imports Word and PowerPoint files, and builds whole sets of documents from one `py-doc.yml`. It replaces three earlier tools (`py-doc2docx`, `py-doc2slides`, `py-doclint`) and the `createdocs` build files from `markbac/technical-documentation`.

Pandoc writes every output, and it runs in a container with every other tool, so only Python and Docker need installing. The linter reads the Markdown with its own parser.

> **Important:** Docker is required for every conversion. On Windows that is Docker Engine in WSL 2, which `py-doc setup` installs.

## Commands

| Command | What it does |
|---|---|
| `py-doc init` | Start a project: `py-doc.yml`, a first document, and optionally a C4 model, templates and a site |
| `py-doc new` | Start a legacy document, or number an existing Markdown file, from `doc-numbers.yml` at the repository root |
| `py-doc build` | Build every document described in `py-doc.yml` (generators, lint, documents, site), or one legacy `createdocs` file with `--legacy` |
| `py-doc docx` | Convert Markdown to Word |
| `py-doc slides` | Convert Markdown to PowerPoint |
| `py-doc lint` | Check writing style, glossary terms, acronyms, structure, links and project conventions; text, CSV, GitHub, JSON or SARIF |
| `py-doc check` | Check a project without building it: `py-doc.yml`, sources, templates, the site and lint |
| `py-doc generate` | Write the Markdown that `content.generators` makes: glossaries, indexes, traceability, API references |
| `py-doc stats` | Count the words, headings, tables, pictures and links of each document |
| `py-doc diff` | Compare two versions of documents section by section, or against a Git revision |
| `py-doc c4` | Check, export, draw and edit Structurizr workspaces (`c4 up` opens the live editor) |
| `py-doc site` | Make and build a web site of the documents with MkDocs or Astro + Starlight |
| `py-doc poster` | Build self-contained HTML posters from Markdown, and print them to PDF |
| `py-doc import` | Convert a Word document or a PowerPoint deck to Markdown |
| `py-doc template` | Check and list the styles of a Word or PowerPoint template |
| `py-doc tools`, `doctor`, `setup` | Build and check the tool container, and install Docker Engine |
| `py-doc migrate` | Create `py-doc.yml` from legacy `createdocs` build files |

The old commands `py-doc2docx`, `py-doc2slides`, `py-doclint` and `py-c4-exporter` still work and print a one-line note naming their replacement.

## Install

```bash
git clone https://github.com/markbac/py-doc.git
cd py-doc
pip install -e .            # Python 3.10 or later
py-doc setup                # install Docker Engine (in the WSL distro on Windows) if you have not
py-doc tools build          # build the tool image (several GB, 5 to 30 minutes the first time)
py-doc doctor               # check that everything works
```

Linux and Windows are supported. See [Installation](docs/guide/01_install.md) for the tool container, proxies and offline machines.

## Quick start

```bash
py-doc init my-docs --name "Pump Controller" --c4 --site mkdocs -y
cd my-docs
py-doc check                                # the project and the writing, without building
py-doc build                                # build/overview.docx, build/architecture.docx, ...
py-doc c4 up architecture/workspace.dsl     # arrange the C4 views in Structurizr; Ctrl+C stops it
py-doc site build                           # site/build/index.html
```

## Documentation

py-doc documents itself with py-doc. The sources are in [`docs/`](docs), and the [`py-doc.yml`](py-doc.yml) at the root of this repository builds them: `py-doc build` for Word, HTML and PDF, `py-doc site build` for the web site.

- **User guide**: [introduction](docs/guide/00_introduction.md), [installation](docs/guide/01_install.md), [projects and `py-doc.yml`](docs/guide/02_projects.md), [writing](docs/guide/03_writing.md), [outputs and templates](docs/guide/04_outputs.md), [importing](docs/guide/05_import.md), [C4 architecture](docs/guide/06_c4.md), [linting](docs/guide/07_lint.md), [web sites](docs/guide/08_sites.md), [reference](docs/guide/09_reference.md), [legacy build files and document numbers](docs/guide/10_legacy.md), [generators, the build pipeline and analysis](docs/guide/11_pipeline.md), [posters](docs/guide/12_posters.md), [writing a poster](docs/guide/13_writing_posters.md).
- **[Requirements](docs/requirements/00_introduction.md)**: what py-doc must do and how well, with the status of every requirement and the open issues.
- **[Architecture](docs/architecture/00_introduction.md)**: how py-doc is built, with C4 chapters generated from [its Structurizr model](docs/architecture/workspace.dsl), and the decisions behind it.
- **[Examples](examples/README.md)**: a small project that uses every feature, with a command for each output.
- **[Bundle audit](docs/bundle-audit.md)**: notes on the original scripts.

## Layout

```
src/
├── py_doc/
│   ├── app.py            # the py-doc command
│   ├── init.py           # py-doc init
│   ├── new.py            # py-doc new
│   ├── cli.py            # py-doc docx (and the old py-doc2docx)
│   ├── slides_cli.py     # py-doc slides (and the old py-doc2slides)
│   ├── _cli.py           # options, output paths and batch conversion shared by both
│   ├── convert.py        # DocxConverter and SlidesConverter, one file through pandoc
│   ├── config.py         # py-doc.yml model and validation
│   ├── build.py          # joins a document's sources and renders it
│   ├── directives.py     # includes, conditions and variables
│   ├── pandoc/           # the pandoc command, Word and PowerPoint finishing, Lua filters
│   ├── diagrams/         # diagram fences to pictures
│   ├── c4/               # Structurizr workspaces: model, chapters, pictures, live editor
│   ├── site/             # web sites: pages, navigation, MkDocs and Starlight engines
│   ├── docx_import.py    # Word to Markdown
│   ├── pptx_import.py    # PowerPoint to Markdown
│   ├── runtime/          # the tool container: image, runner, doctor, setup
│   ├── markdown/         # parser and front matter, used by the linter
│   ├── lint/             # rules, structure rules, markdownlint, Vale, JSON and SARIF output
│   ├── generators/       # content generators and py-doc generate
│   ├── analysis/         # py-doc stats, check and diff
│   ├── migrate.py        # createdocs to py-doc.yml
│   ├── report.py         # the JSON build report
│   └── poster.py         # py-doc poster: Markdown to an HTML poster
├── pydoc2docx/           # old import names, kept as aliases
├── pydoc2slides/
└── pydoclint/
docs/                     # py-doc's own user guide, requirements and architecture
examples/                 # a project that uses every feature
tests/
```

## Running tests

```bash
pip install -e ".[dev]"
python -m pytest
ruff check .
py-doc lint docs --strict
```

CI runs on Linux and Windows with Python 3.10 and 3.14, the oldest and newest supported. macOS is not supported.

## License

Licensed under the [MIT License](LICENSE).
