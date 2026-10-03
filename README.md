# `py-doc2docx` — Markdown to Word (.docx) Technical Document Converter

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Docx](https://img.shields.io/badge/Microsoft-Word-blue.svg)

`py-doc2docx` is a generic, Python-based CLI developer toolkit for converting Markdown technical documentation into styled **Microsoft Word (`.docx`)** documents. Derived from the `createdocs` toolset in `markbac/technical-documentation`.

---

## 🎯 What It Does

`py-doc2docx` converts technical documentation written in Markdown into formatted Word documents suitable for client deliverables, specifications, and formal engineering documentation:

1. **Hierarchy Preservation**: Translates H1 (`#`), H2 (`##`), H3 (`###`), and H4 (`####`) headings into styled Word heading levels.
2. **List & Bullet Formatting**: Converts Markdown unordered bullet points (`- `, `* `) and ordered lists (`1. `) into native Word list items.
3. **Monospaced Code Block Support**: Renders technical code fences (` ``` `) into monospaced code blocks with left indentation and dark slate styling.
4. **Reference Template Injection**: Option to supply a custom reference Word template (`.docx`) for corporate fonts, margins, headers/footers, and branding.
5. **Py-LogKit Logging**: Color-coded progress output (`pylogkit`).

---

## 🏗️ Tool Architecture

The package wraps `python-docx` AST node builders into a clean conversion engine:

```
py-doc2docx/
├── src/
│   └── pydoc2docx/
│       ├── __init__.py         # Package initialization
│       ├── converter.py        # Core DocxConverter engine
│       ├── cli.py              # CLI Argument Parser & Runner
│       └── pylogkit/           # Py-LogKit logging framework
├── tests/
│   └── test_converter.py       # Unit test suite
├── .github/workflows/ci.yml    # Lint, test matrix, build and CI gate
├── pyproject.toml              # Package metadata, entry points, tool config
└── README.md                   # Comprehensive documentation
```

### Conversion Data Pipeline

```
[Markdown File (.md)] ──► [Markdown Line Buffer Parser]
                                    │
                                    ▼
                          [DocxConverter Engine]
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
[Heading Builder]           [List Item Builder]        [Code Fence Builder]
  (H1..H4 Styles)             (List Bullet/Number)       (Consolas 9.5pt)
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
                         [Optional Template Injector]
                                    │
                                    ▼
                         [Word File (.docx) Saved]
```

---

## 💻 Installation

```bash
# Clone repository
git clone https://github.com/markbac/py-doc2docx.git
cd py-doc2docx

# Install in editable mode
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

---

### 2. Python API

```python
from pathlib import Path
from pydoc2docx import DocxConverter

# Initialize converter with optional template
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
