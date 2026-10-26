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
| FR-040 to FR-049 | `pandoc/engine.py`, `pandoc/reference.py`, `pandoc/docx_finish.py`, `pandoc/pptx_finish.py`, `naming.py`, `report.py`, `template_check.py`, `convert.py`, `_cli.py` | `test_pandoc.py`, `test_pptx_pandoc.py`, `test_report.py`, `test_template_check.py`, `test_cli.py`, `test_slides_cli.py`, `test_convert.py`, `test_examples.py`, `test_heading_numbers.py` |
| FR-060, FR-062, FR-063 | `docx_import.py`, `import_cli.py` | `test_docx_import.py` |
| FR-061 | `pptx_import.py` | `test_pptx_import.py` |
| FR-080 to FR-086, QR-081 | `c4/` | `test_c4.py` |
| FR-100 to FR-106 | `lint/`, `markdown/` | `test_lint.py`, `test_lint_cli.py`, `test_structure.py`, `test_vale.py`, `test_markdownlint.py`, `test_markdown_ast.py` |
| FR-120 to FR-127, QR-082 | `site/`, `pandoc/resources/site.lua` | `test_site.py` |
| FR-130 to FR-139, FR-150 to FR-160, FR-163 to FR-166 | `poster.py`, `poster_blocks.py`, `poster_svg.py`, `poster_math.py`, `poster_scales.py`, `poster_embedded.py`, `poster_shapes.py`, `poster_space.py`, `poster_elements.py`, `poster_plot.py`, `poster_fonts.py`, `poster_settings.py`, `poster_themes.py`, `poster_cli.py`, `watch.py`, `config.py`, `app.py`, `lint/linter.py`, `diagrams/tools/poster_pdf.js` | `test_poster.py`, `test_poster_svg.py`, `test_poster_math.py`, `test_poster_scales.py`, `test_poster_embedded.py`, `test_poster_shapes.py`, `test_poster_space.py`, `test_poster_plot.py`, `test_poster_browser.py` |
| FR-161 | `_cli.py`, `convert.py`, `watch.py`, `pandoc/engine.py`, `pandoc/resources/preview.css`, `pandoc/resources/slides-preview.lua` | `test_cli.py`, `test_slides_cli.py`, `test_convert.py`, `test_preview_cases.py` |
| FR-162 | `editors/vscode/extension.js`, `editors/vscode/src/` | `editors/vscode/test/`, `test_preview_cases.py` |
| FR-028 | `diagrams/render.py`, `config.py` | `test_diagrams.py` |
| FR-167, FR-168 | `diagrams/blocks.py`, `diagrams/render.py`, `diagrams/scan.py`, `diagrams/tools/block_png.js`, `poster_blocks.py`, `config.py` | `test_document_blocks.py`, `test_poster_diagrams.py` |
| FR-169 | `diagram_cli.py`, `app.py` | `test_diagram_cli.py` |
| FR-170, FR-144 | `diagrams/declarative.py`, `diagrams/registry.py`, `diagrams/tools/*_render.py`, `diagrams/tools/music_render.js`, `runtime/image.py`, `runtime/science/`, `tools_cli.py` | `test_declarative_fences.py`, `test_image.py` |
| FR-128 | `site/pages.py`, `site/engines.py` | `test_site.py` |
| FR-140 to FR-143, QR-040 to QR-043 | `runtime/`, `tools_cli.py` | `test_runtime.py`, `test_image.py`, `test_setup.py`, `test_doctor.py`, `test_platform.py` |
| QR-102 | `cli.py`, `slides_cli.py`, `pydoc2docx`, `pydoc2slides`, `pydoclint` | `test_compat.py` |
| QR-123 | `_logging.py` | `test_logging.py`, `test_logging_policy.py` |
| QR-103 | `py-doc.yml`, `docs/` | `py-doc lint docs --strict` and `py-doc build` in CI |

## Open issues

The issues of the repository, as reviewed on 18 October 2026, and the requirements they map to.

| Issue | Title | Requirements | State |
|---|---|---|---|
| #3 | Merge py-doc2docx, py-doc2slides and py-doclint into a py-doc toolset | FR-001, FR-048, FR-100, QR-102 | Done and closed: one `py-doc` command and package, old names kept. `render docx` became `docx`, and `init` now exists |
| #4 | Canonical py-doc.yml configuration model | FR-001 to FR-005, FR-009, FR-010, FR-120 | Done: documents, collections, bundles, outputs, lint and site. Only `content` is reserved, for the generators (#18) |
| #11 | Configurable lint rules in py-doc.yml | FR-101, FR-102, FR-106 | Done: rules, severities, glossary, phrases, acronyms, structure rules, heading, link and alt-text rules, and `lint.limits` |
| #12 | Complete acronym linting | FR-105 | Done: length, allow-list, `require_definition`, `scope` (file or document), `suggestion` and severity |
| #14 | HTML renderer and PDF output pipeline | FR-042, FR-043 | Done and closed: pandoc HTML and XeLaTeX PDF, with templates and per-document settings |
| #15 | Multiple documents, collections and combined bundles | FR-004, FR-009 | Done: many documents, shared sources, `collections` and `bundles`, built side by side |
| #16 | MkDocs project integration and scaffolding | FR-120 to FR-124 | Done and closed: `py-doc site` with `engine: mkdocs` |
| #17 | Astro + Starlight project integration and scaffolding | FR-120 to FR-124 | Done and closed: `py-doc site` with `engine: starlight` |
| #18 | Configurable content generators | FR-010 | Done: `content.generators` with glossary, documents, toc, `adr-index`, requirements, `openapi`, `asyncapi`, `python-api`, diagram, command and python types, entry points for other packages, and `py-doc generate` |
| #19 | Unified build pipeline and CI integration | FR-011, FR-046, FR-104 | Done: `py-doc build` runs generators, lint, documents and bundles, the site and an output check, with steps in the JSON report and SARIF lint output |
| #41 | Documentation quality checks beyond current lint rules | FR-106 | Done: DOC005 to DOC013 (heading jumps, broken links, alt text, long sentences and headings, repeated headings, unclosed fences, required sections, terminology) and glossary checks |
| #42 | py-doc init and project scaffolding | FR-006, FR-007 | Done. Can be closed |
| #43 | Documentation analysis and semantic diff tools | FR-012, FR-107, FR-108 | Done: `py-doc stats`, `py-doc check` and `py-doc diff` (by section, with Git revisions), beside `doctor` |
| #44 | Front matter and document metadata | FR-005 | Done: front matter reaches every format, and the site pages carry the description, number, version and status |
| #47 | Machine-readable lint and build output | FR-046, FR-104 | Done: lint output as text, CSV, GitHub annotations, JSON and SARIF, and the JSON build report |
| #48 | Site navigation from document metadata | FR-122 | Done: navigation from the documents, their titles and order, `site.groups`, and a hand-made navigation kept |
| #149 | HTML posters from Markdown: py-doc poster, themes and orientation | FR-130 to FR-135 | Done: `py-doc poster`, portrait and landscape, columns, built-in and file themes, examples |
| #150 | Poster: full-width sections | FR-137 | Done: `{.wide}` on a section heading, and `{colour=}` for its heading bar |
| #151 | Poster: callout types, timeline, trend stats and references | FR-136, FR-137 | Done: callouts in both spellings, `timeline`, trends in the `{.stats}` strip, a `{.references}` list, and `chart` |
| #152 | Poster: QR code and partner logos in the footer | FR-137 | Done: `footer.qr`, `footer.logos`, and a `qr` block |
| #153 | Poster: embed theme fonts so a poster looks the same offline | FR-150 | Done: `fonts.files` in a theme, and `embed_fonts` (or `--embed-fonts`) for the stylesheet's web fonts, cached |
| #161 | A host runtime, to build with the tools on the PATH instead of the container | None yet | Open, low priority |
| #192 | Roadmap: poster visualisation plan | FR-163 to FR-170, FR-144 | Open: the plan. Phases 0 and 1 are done in #208 |
| #178, #193, #194, #196 to #199, #202, #205, #206 | The phase 0 and phase 1 issues of the plan | FR-162 to FR-170, FR-144 | Done in #208 (the stretch items of #206, and sky maps of #202, are left) |
| #195 | Theme and document the container's diagrams | FR-168 | Done in part in #208: the Mermaid icon packs (logos, tabler, mdi) are open |
| #190 | `py-doc diagram`, standalone images | FR-169 | Phase 1 done in #208; phase 2 open |
| #200, #201, #203, #204, #207 | Phase 2 and 3 of the plan: structure diagrams, icons and illustrations, reference data, the science backlog, HTML slides | None yet | Open |

## Closed issues

The 91 closed issues, checked on 13 October 2026 against the code, the tests and a run of each behaviour through the real pipeline. The 20 duplicates (#21 to #40) point at their originals, which are reviewed above or here.

| Issues | Outcome |
|---|---|
| #1, #5, #6, #10, #13, #45, #46, #50, #51, #62 to #64, #69 to #71, #73 to #84, #92, #94, #95, #97 to #100, #102, #103, #105 to #116, #118 | Done as described, with tests |
| #2, #7, #8, #9, #58, #59, #66, #67, #75 | Done for the native renderers, which #117 removed. The same behaviour now comes from pandoc. Checked: fences, headings, numbers in text, the byte order mark, invalid UTF-8, vertical tabs, code style, heading levels 5 and 6 |
| #20, #65 | Done, with two changes of plan: the heavy tools moved into the container instead of optional Python extras, and macOS was dropped from CI by #102 |
| #49, #72 | The code of an unclosed fence was kept, but as text and without the warning the issues asked for. A warning that names the file and line is added |
| #53 | Seven or more `#` became a level 7 heading under pandoc. Such a line is now text, as in CommonMark |
| #60 | A template's body text is kept before the document when the template has no `[[INSERTCONTENT]]` line, as #117 decided. That was silent. A warning now names the text and says how to place the document |
| #93 | Each rule of the `PyDoc` style now has a test that it flags a bad line and leaves a good one, which found the passive-voice rule missing irregular verbs. The repository's documentation lints with no findings |
| #96 | The end-to-end test with the real `structurizr-cli` was missing. It is added, and CI installs the pinned CLI to run it |
| #104 | The note that `Setup-DocTools.ps1` is no longer needed is added to the reference chapter |
| #117 | Done. The template-body choice it made is recorded under #60 |
| — | Found on the way: a template in the same folder as the Markdown failed with a duplicate mount, now fixed |
