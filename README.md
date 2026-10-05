# `py-doc2docx` — Markdown to Word (.docx) Technical Document Converter

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Docx](https://img.shields.io/badge/Microsoft-Word-blue.svg)

`py-doc2docx` is a generic, Python-based CLI developer toolkit for converting Markdown technical documentation into styled **Microsoft Word (`.docx`)** documents. Derived from the `createdocs` toolset in `markbac/technical-documentation`.

---

## 🎯 What It Does

`py-doc2docx` converts technical documentation written in Markdown into formatted Word documents suitable for client deliverables, specifications, and formal engineering documentation:

1. **Hierarchy Preservation**: Translates headings (ATX `#` to `######` and setext underlines) into Word heading styles `Heading 1` to `Heading 6`.
2. **Lists**: Bullet and numbered lists become native Word list items, nested up to three levels. Each numbered list restarts at its own start number.
3. **Inline Formatting and Links**: Strong, emphasis and inline code become run formatting. Links become Word hyperlinks.
4. **Tables, Quotes and Images**: Tables become Word tables, block quotes use the `Quote` style, and local pictures are embedded with their alt text.
5. **Code Blocks**: Fenced (backtick or tilde) and indented code become paragraphs in the `Code` style: monospaced, with a left indent. A template that defines a `Code` style controls how they look.
6. **Reference Template Injection**: Option to supply a custom reference Word template (`.docx`) for corporate fonts, margins, headers/footers, and branding. The template's styles, page setup, headers, footers and properties are used. Its body content (cover page, placeholder text) is removed unless you pass `--keep-template-body`.
7. **Progress Logging**: Progress messages on stderr, configured by the command line with [py-logkit](https://github.com/markbac/py-logkit) (colour on a terminal, off for pipes and `NO_COLOR`). The library itself only uses the standard `logging` module and never configures it.

---

## 🏗️ Tool Architecture

The package parses Markdown into a typed tree and renders it with `python-docx`:

```
py-doc2docx/
├── src/
│   ├── py_doc/
│   │   ├── __init__.py         # Package initialization
│   │   ├── cli.py              # CLI Argument Parser, Runner and logging setup
│   │   ├── markdown/           # Shared parser and typed document tree (AST)
│   │   ├── lint/               # py-doclint: rules, linter and command line
│   │   └── render/
│   │       └── docx.py         # DocxConverter: renders the tree as Word
│   └── pydoc2docx/             # Compatibility alias for the old import name
├── tests/
│   ├── fixtures/               # Markdown corpus used by the regression suite
│   ├── golden/                 # Expected DOCX outlines (change detectors)
│   ├── test_converter.py       # Semantic tests of the converter
│   ├── test_docx_render.py     # How each Markdown construct is rendered
│   ├── test_markdown_ast.py    # Parser and document tree tests
│   ├── test_lint.py            # Lint rules, with exact expected issues
│   ├── test_lint_cli.py        # Lint file errors, directory walk and command line
│   ├── test_cli.py             # CLI integration tests
│   ├── test_logging.py         # Logging is configured by the CLI, not on import
│   ├── test_compat.py          # Old pydoc2docx import name and command still work
│   └── test_fixtures.py        # Corpus and golden-output tests
├── .github/workflows/ci.yml    # Lint, test matrix, build and CI gate
├── pyproject.toml              # Package metadata, entry points, tool config
└── README.md                   # Comprehensive documentation
```

### Conversion Data Pipeline

```
[Markdown File (.md)] ──► [py_doc.markdown parser (markdown-it-py)]
                                    │
                                    ▼
                          [Typed document tree (AST)]
                                    │
                                    ▼
                          [DocxConverter renderer]
                                    │
                                    ▼
                  [Word styles: Heading n, List Bullet, Code, ...]
                                    │
                                    ▼
                         [Optional Template Injector]
                                    │
                                    ▼
                         [Word File (.docx) Saved]
```

## 📝 Supported Markdown

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
| Front matter | Not rendered. Metadata support is tracked in #44 |

> **Note:** Markdown the parser does not know raises `ConversionError` instead of being dropped, so content never disappears silently. Task-list checkboxes, strikethrough and footnotes are not CommonMark and appear as literal text.

---

## 🔍 Documentation Linting (`py-doclint`)

The same package checks Markdown for writing quality. It runs on the shared document tree, so code blocks, inline code, HTML, link destinations and front matter are never treated as prose, and URLs and file names written as plain text are skipped.

```bash
py-doclint docs/             # lint a directory (default: the current one)
py-doclint docs/Guide.md     # lint one file
py-doclint docs/ --strict    # exit 1 if any warning or error is reported
py-doclint . --exclude drafts
```

| Rule | Category | Default severity | What it reports |
|---|---|---|---|
| `DOC001` | Glossary | warning | A glossary term written differently from its canonical form, in any capitalisation (`mQTT`), plus listed misspellings (`Lw2m`) |
| `DOC002` | Style | warning | Wordy phrases such as "in order to", also when wrapped over two lines, with a shorter wording suggested |
| `DOC003` | Acronym | info | The first use of an all-capitals acronym that is never defined, or is defined only later |

- **Acronym definitions** are recognised in both orders, `Pre-Shared Key (PSK)` and `PSK (Pre-Shared Key)`, including mixed-case forms such as `LwM2M` and `IoT`. The words must spell out the acronym. Words in the built-in allow-list and glossary terms need no definition.
- **Directories**: hidden directories and `node_modules`, `venv`, `env`, `site-packages`, `__pycache__`, `dist`, `build` and `vendor` are skipped. `.md` and `.markdown` files are found in any capitalisation. Paths are printed relative to the working directory.
- **Exit status**: `0` when clean, or when only info is reported, or without `--strict`. `1` with `--strict` and at least one warning or error. `2` when the target is missing or not Markdown, or when any file cannot be read, so an error is never mistaken for a clean result.
- **Limits**: issues carry a line number but no column, because the document tree records lines only. Terms inside a URL, a dotted or slashed name such as `lwm2m/dtls`, or code are not checked.

```python
from py_doc.lint import DocLinter

report = DocLinter().lint_path("docs")
for issue in report.issues:
    print(issue)  # docs/Guide.md:12: warning DOC001 [Glossary] ...
print(report.files_scanned, "files scanned,", len(report.errors), "could not be read")
```

---

## 💻 Installation

```bash
# Clone repository
git clone https://github.com/markbac/py-doc2docx.git
cd py-doc2docx

# Install in editable mode (needs Python 3.10 or later; py-logkit is installed from GitHub automatically)
pip install -e .

# Install with development tools (pytest, ruff, build, twine)
pip install -e ".[dev]"
```

---

## 🛠️ How To Use

### 1. Command-Line Interface (CLI)

```bash
# Convert single Markdown file to Word .docx
py-doc2docx Technical_Specification.md -o Technical_Specification.docx

# Convert using custom reference template
py-doc2docx Technical_Specification.md -t Template.docx

# Batch convert entire documentation folder
py-doc2docx docs/ -o dist/docx/
```

#### CLI Options Reference

| Flag | Short | Default | Description |
|---|---|---|---|
| `input` | | *Required* | Path to input Markdown (`.md`) file or directory |
| `--output` | `-o` | Same as input | Output `.docx` file path or destination directory |
| `--template` | `-t` | `None` | Optional path to reference Word (`.docx`) template |
| `--allow-missing-template` | | Off | Warn and use a blank document if the template file is missing (default: fail with exit status 1) |
| `--keep-template-body` | | Off | Keep the template's own body content and append the converted document after it (default: remove it) |

---

### 2. Python API

```python
from pathlib import Path
from py_doc import DocxConverter  # the old `pydoc2docx` import name still works

# Initialize converter with optional template.
# A missing template raises FileNotFoundError unless allow_missing_template=True.
# The template's body content is removed unless keep_template_body=True.
# Input that is not valid UTF-8 raises py_doc.ConversionError.
converter = DocxConverter(template_path=Path("templates/Template.docx"))

# Convert Markdown file
output_path = converter.convert_file(
    md_path=Path("Architecture.md"),
    output_path=Path("output/Architecture.docx")
)
print(f"Generated: {output_path}")
```

---

## 🧪 Running Tests

```bash
python -m pytest
```

---

## 📄 License

Licensed under the [MIT License](LICENSE).
