---
title: Traceability
---

# Traceability

## Requirements to code and tests

| Requirements | Modules | Tests |
|---|---|---|
| FR-001 to FR-005 | `config.py`, `build.py`, `pandoc/source.py` | `test_config.py`, `test_build.py`, `test_front_matter.py` |
| FR-006, FR-007 | `init.py` | `test_init.py` |
| FR-008 | `migrate.py` | `test_migrate.py` |
| FR-020 to FR-025 | `directives.py`, `pandoc/resources/*.lua`, `pandoc/docx_post.py` | `test_directives.py`, `test_pandoc.py`, `test_word_control.py`, `test_word_layout.py` |
| FR-026, FR-027, QR-080 | `diagrams/` | `test_diagrams.py` |
| FR-040 to FR-048 | `pandoc/engine.py`, `pandoc/docx_finish.py`, `pandoc/pptx_finish.py`, `naming.py`, `report.py`, `template_check.py`, `convert.py`, `_cli.py` | `test_pandoc.py`, `test_pptx_pandoc.py`, `test_report.py`, `test_template_check.py`, `test_cli.py`, `test_slides_cli.py`, `test_convert.py`, `test_examples.py` |
| FR-060, FR-062, FR-063 | `docx_import.py`, `import_cli.py` | `test_docx_import.py` |
| FR-061 | `pptx_import.py` | `test_pptx_import.py` |
| FR-080 to FR-086, QR-081 | `c4/` | `test_c4.py` |
| FR-100 to FR-106 | `lint/`, `markdown/` | `test_lint.py`, `test_lint_cli.py`, `test_structure.py`, `test_vale.py`, `test_markdownlint.py`, `test_markdown_ast.py` |
| FR-120 to FR-124, QR-082 | `site/`, `pandoc/resources/site.lua` | `test_site.py` |
| FR-140 to FR-143, QR-040 to QR-043 | `runtime/`, `tools_cli.py` | `test_runtime.py`, `test_image.py`, `test_setup.py`, `test_doctor.py`, `test_platform.py` |
| QR-102 | `cli.py`, `slides_cli.py`, `pydoc2docx`, `pydoc2slides`, `pydoclint` | `test_compat.py` |
| QR-123 | `_logging.py` | `test_logging.py`, `test_logging_policy.py` |
| QR-103 | `py-doc.yml`, `docs/` | `py-doc lint docs --strict` and `py-doc build` in CI |

## Open issues

The issues of the repository, as reviewed on 12 October 2026, and the requirements they map to.

| Issue | Title | Requirements | State |
|---|---|---|---|
| #3 | Merge py-doc2docx, py-doc2slides and py-doclint into a py-doc toolset | FR-001, FR-048, FR-100, QR-102 | Done: one `py-doc` command and package, old names kept. `render docx` became `docx`, and `init` now exists. Can be closed |
| #4 | Canonical py-doc.yml configuration model | FR-001 to FR-005, FR-009, FR-010, FR-120 | Mostly done: the site section is now used. Collections, bundles and content remain (#15, #18) |
| #11 | Configurable lint rules in py-doc.yml | FR-101, FR-102, FR-106 | Mostly done: rules, severities, glossary, phrases, acronyms and structure rules. Built-in link and style-limit rules remain (#41) |
| #12 | Complete acronym linting | FR-105 | Partly done: required-definition and definition-scope options remain |
| #14 | HTML renderer and PDF output pipeline | FR-042, FR-043 | Done through pandoc (HTML and XeLaTeX PDF, with templates and per-document settings). Can be closed |
| #15 | Multiple documents, collections and combined bundles | FR-004, FR-009 | Partly done: many documents and shared sources work. Collections and bundles remain |
| #16 | MkDocs project integration and scaffolding | FR-120 to FR-124 | Done: `py-doc site` with `engine: mkdocs`. Can be closed |
| #17 | Astro + Starlight project integration and scaffolding | FR-120 to FR-124 | Done: `py-doc site` with `engine: starlight`. Can be closed |
| #18 | Configurable content generators | FR-010 | Open: C4 chapters are the only generator |
| #19 | Unified build pipeline and CI integration | FR-046, FR-104 | Mostly done: `py-doc build` with a JSON report and GitHub annotations from lint. Site builds are a separate command. SARIF remains (#47) |
| #41 | Documentation quality checks beyond current lint rules | FR-106 | Partly done through markdownlint and structure rules |
| #42 | py-doc init and project scaffolding | FR-006, FR-007 | Done. Can be closed |
| #43 | Documentation analysis and semantic diff tools | | Open: `doctor` exists for the environment. `stats`, `diff` and a document `check` do not |
| #44 | Front matter and document metadata | FR-005 | Done: front matter reaches every format and the site pages |
| #47 | Machine-readable lint and build output | FR-046, FR-104 | Partly done: the JSON build report, CSV and GitHub lint output. JSON and SARIF lint output remain |
| #48 | Site navigation from document metadata | FR-122 | Done: navigation from the documents and their titles, a hand-made navigation kept. Can be closed |
