# `py-doc2docx` — Markdown to Word (.docx) Technical Document Converter

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

A Python CLI and developer toolkit for converting Markdown technical documentation into styled **Microsoft Word (`.docx`)** documents.

---

## 🚀 Features

- **Heading & Paragraph Formatting**: Preserves H1..H4 header hierarchies, bullet lists, and numbered lists.
- **Formatted Code Blocks**: Monospaced font rendering for technical code fences (` ``` `).
- **Template Support**: Option to supply a custom Word template (`.docx`).
- **Py-LogKit Integration**: Rich, color-coded console and file logging.

---

## 🛠️ Installation

```bash
pip install -e .
```

---

## 💻 CLI Usage

```bash
# Convert single Markdown file
py-doc2docx Technical_Specification.md -o Technical_Specification.docx

# Convert using custom Word template
py-doc2docx Technical_Specification.md -t Template.docx
```
