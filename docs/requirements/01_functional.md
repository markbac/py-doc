---
title: Functional requirements
---

# Functional requirements

## Project and configuration

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-001 | py-doc shall read one project file, `py-doc.yml`, that describes the documents, their sources and outputs, lint policy, C4 settings, the build report and the web site. | Must | Met |
| FR-002 | py-doc shall check every key of `py-doc.yml` when it loads, and report an unknown key, a wrong type or a bad value as an error that names its place. | Must | Met |
| FR-003 | py-doc shall find the nearest `py-doc.yml` in the current folder or a parent folder, and accept another file with `--config`. | Must | Met |
| FR-004 | A document shall join any number of source files in order, each with an optional heading offset, replacement title, page break and include switch. | Must | Met |
| FR-005 | Document properties shall come from `py-doc.yml`, then the first source's front matter, then its first heading, and reach every output format. | Must | Met |
| FR-006 | `py-doc init` shall start a project with a working `py-doc.yml` and a first document, and on request a C4 model, Word and PowerPoint templates and a web site. It shall never replace a file, and shall refuse a folder that already has a `py-doc.yml`. | Should | Met |
| FR-007 | `py-doc init` shall ask for its choices in a terminal, and ask nothing with `--yes` or when it is not run from a terminal. | Should | Met |
| FR-008 | `py-doc migrate` shall turn legacy `createdocs` build files into one `py-doc.yml`, report what has no equivalent, and never change or delete the originals. | Should | Met |
| FR-009 | The configuration shall support collections of sources and bundles of documents. | Could | Met: `collections` of source files and `bundles` of documents, built beside the documents |
| FR-010 | The configuration shall support content generators that run before the build. | Could | Met: `content.generators` with eleven built-in types and an entry point for more, run by `py-doc generate`, `build` and `site` |
| FR-011 | `py-doc build` shall run the generators, lint (on request), the documents and bundles, the site (on request) and a check that every output was written. It shall stop at a failed step, and record the steps in the build report. | Should | Met |
| FR-012 | `py-doc check` shall find missing sources, templates and site projects and the lint errors of a project without building it. | Should | Met |
| FR-013 | The reference documentation of an API shall be generated from its OpenAPI or AsyncAPI description with the standard tools of each (Redocly and Widdershins, the AsyncAPI generator). The description shall be checked first, and the result shall be Markdown for every output and a standalone HTML page. | Should | Met |

## Writing

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-020 | py-doc shall read pandoc Markdown with fenced divs, raw HTML, table captions, strikethrough, task lists, footnotes, definition lists and maths. | Must | Met |
| FR-021 | Callouts in both the `> [!NOTE]` and `> **Note:**` spellings shall become a box of their kind in every format. The kinds are note, tip, important, warning and caution. | Must | Met |
| FR-022 | `[[CAPTION:Figure]]` and `[[CAPTION:Table]]` shall caption the picture, diagram, code block or table next to them, numbered in Word. | Must | Met |
| FR-023 | `[[LANDSCAPE]]`, `[[PORTRAIT]]`, `[[STYLE:Name]]` and page break blocks shall control Word sections, styles and pages, and starting slides. | Should | Met |
| FR-024 | `[[INCLUDE:]]` and `[[INCLUDE-CODE:]]` shall include other files, `[[IF:]]` and `[[NOT:]]` shall keep text for some builds only, and `{{name}}` shall be replaced by a variable. Values shall come from `py-doc.yml` or the command line. | Must | Met |
| FR-025 | A missing or circular include, an unclosed `[[IF:]]` or an undefined condition shall be an error that names the file and line. | Must | Met |
| FR-026 | Fenced blocks of Mermaid, PlantUML, Graphviz, ditaa, the blockdiag family, WaveDrom, bytefield-svg, Pikchr, railroad, WireViz, Vega and Vega-Lite shall become pictures in every output. | Must | Met |
| FR-027 | A diagram that cannot be drawn shall stop the build with the file, the line and the tool's message. `--keep-going` shall list every failure. | Must | Met |
| FR-028 | `diagrams.mermaid` in `py-doc.yml` shall give every Mermaid diagram of documents, sites and posters the same Mermaid settings, under the diagram's own. | Could | Met |

## Outputs

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-040 | py-doc shall build Word documents from a template: styles, a title page filled from placeholders, the body at a marker, a contents list on request. | Must | Met |
| FR-041 | py-doc shall build PowerPoint decks from a template. They have a slide per heading up to a chosen level, section slides, columns, speaker notes, pictures with captions, a footer and the version. | Must | Met |
| FR-042 | py-doc shall build PDF with XeLaTeX, from a built-in or a project LaTeX template. | Must | Met |
| FR-043 | py-doc shall build one self-contained HTML file per document, with a project stylesheet. | Must | Met |
| FR-044 | A document with `status: Draft` shall use the `_Draft` twin of its template when one exists. | Should | Met |
| FR-045 | Output names shall follow a pattern with the document name and version, and `version: git` shall take the version from Git. | Should | Met |
| FR-046 | `py-doc build` shall write a JSON report of the tools, sources, outputs with checksums, diagrams and warnings of a build, also when the build fails. | Should | Met |
| FR-047 | `py-doc template` shall check, list, compare and count the styles of Word and PowerPoint templates. | Should | Met |
| FR-048 | `py-doc docx` and `py-doc slides` shall convert single files and folders without a `py-doc.yml`. | Must | Met |
| FR-049 | Where the output numbers its headings itself, the section numbers written in headings shall be left out, so no section is numbered twice. That is a Word template with numbered heading styles, or numbered PDF and HTML sections. A setting shall force or prevent it. | Must | Met |

## Importing

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-060 | `py-doc import` shall turn a Word document into Markdown that builds again: headings, lists, tables, code, quotes, callouts, captions, links, emphasis, pictures and properties. | Must | Met |
| FR-061 | `py-doc import` shall turn a PowerPoint deck into Markdown that `py-doc slides` builds into the same slides. It keeps the title slide, headings, nested bullets, columns, tables, pictures with captions, code, callouts and speaker notes. | Should | Met |
| FR-062 | What an import cannot carry over shall be counted in a warning, never dropped quietly. | Must | Met |
| FR-063 | An import shall not replace an existing Markdown file unless told to. | Must | Met |

## C4 architecture

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-080 | py-doc shall read Structurizr workspaces as DSL (through structurizr-cli) or JSON (directly, without Java). | Must | Met |
| FR-081 | py-doc shall write Markdown chapters from a model, one per C4 level, with an element catalogue, and join them with hand-written chapters in a document. | Must | Met |
| FR-082 | py-doc shall draw the views as Structurizr draws them, and fail with the view's name when one cannot be drawn. | Must | Met |
| FR-083 | `py-doc c4 check` and `py-doc lint` shall check a model for elements and relationships that lack the text a document needs. | Should | Met |
| FR-084 | `py-doc c4 up` shall open a workspace in Structurizr Local to view and arrange its views. It shall show changes to the DSL on reload, save layouts in the project beside the DSL, and stop Local on Ctrl+C. | Should | Met |
| FR-085 | Builds shall draw views with the layouts saved in the project. | Should | Met |
| FR-086 | `py-doc c4 lock` shall pin the Structurizr Local image by digest. | Could | Met |

## Linting

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-100 | `py-doc lint` shall check glossary terms, wordy phrases, undefined acronyms and directives, and never treat code, links, HTML or front matter as prose. | Must | Met |
| FR-101 | Rule severities shall be set in `py-doc.yml`, and a rule switched off. | Must | Met |
| FR-102 | Project structure rules shall be data: required files, line patterns, blank lines, paths, balanced markers, required captions and cross-file anchors. | Should | Met |
| FR-103 | `py-doc lint` shall run markdownlint and Vale beside the built-in rules and report one list with one exit status. | Should | Met |
| FR-104 | Lint results shall be available as text, CSV, GitHub annotations, JSON and SARIF. | Should | Met, with `--output` for a file |
| FR-105 | Acronym checks shall support a required definition and a definition scope. | Could | Met: `require_definition`, `scope` (file or document) and `suggestion` |
| FR-106 | Further checks: heading-level jumps, duplicate headings, broken links, missing alt text, long headings, required sections. | Could | Met: built-in rules DOC005 to DOC013 |
| FR-107 | `py-doc stats` shall count the words of prose, headings, code blocks, tables, pictures, links and lint issues of each document or file. | Could | Met |
| FR-108 | `py-doc diff` shall compare two versions of documents by section (added, removed, renamed, moved, changed), between files or against a Git revision. | Could | Met |

## Web sites

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-120 | `py-doc site` shall build a web site of the documents with MkDocs or Astro + Starlight, from the same sources as the other outputs. | Should | Met |
| FR-121 | `py-doc site init` shall make a site project when none exists, and leave an existing one as it is. | Should | Met |
| FR-122 | py-doc shall write the site navigation from the documents of `py-doc.yml`. It goes in a file of its own that the site's configuration takes in, so a hand-made navigation is kept. | Should | Met |
| FR-123 | py-doc shall never replace a site file it did not write, and shall remove pages whose sources are gone. | Must | Met |
| FR-124 | Site pages shall keep callouts, diagrams, pictures, captions and links between chapters. | Should | Met |
| FR-125 | One MkDocs site project shall build more than one site (`site.targets`), each from its own configuration file and to its own folder, from the same pages. | Should | Met |
| FR-126 | A document's site pages shall link the files `py-doc build` made for it (`site.downloads`), copied beside the site. | Should | Met |
| FR-127 | The site navigation py-doc writes shall also list pages of the user's own (`site.pages`), after the documents. | Should | Met |
| FR-128 | The site shall carry the posters `site.posters` names, each a page of its own, with a page that links them and their printed PDFs. | Could | Met |

## Posters

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-130 | `py-doc poster` shall make one self-contained HTML poster from one Markdown file, with its pictures, diagrams, logo and styles inside the page. | Should | Met |
| FR-131 | A poster shall keep the proportions of A paper, portrait or landscape. It shall fit its content at the narrowest layout that holds it, and print on one page of the chosen size. | Should | Met |
| FR-132 | A poster shall draw its diagram fences in the tool container, and a diagram that cannot be drawn shall be shown as code with a warning, without stopping the poster. | Should | Met |
| FR-133 | The colours, fonts, block palette and logo of a poster shall come from a theme: a built-in one, or a theme file that changes a built-in one. The theme shall be chosen on the command line, in the front matter or in `py-doc.yml`. | Should | Met |
| FR-134 | A mistake in a poster's settings, theme or blocks shall stop the build with the file and the key. | Must | Met |
| FR-135 | A poster's settings (orientation, layout, theme, colours, logo, header, footer, variables and conditions) shall be set in `py-doc.yml`, in the front matter, or on the command line. `py-doc.yml` shall hold them for every poster or for one named poster. Each place wins over the one before. | Should | Met |
| FR-136 | A poster shall take the py-doc Markdown of documents: includes, conditions, variables, captions and callouts. | Should | Met |
| FR-137 | A poster shall have full-width sections, timelines, trends in the stats, a references list, and charts drawn without the tool container. Its footer shall have three texts, logos and a QR code. | Could | Met |
| FR-138 | `py-doc poster` shall print a poster to a one-page PDF of its paper size and orientation, with the Chromium of the tool container. | Should | Met |
| FR-139 | `py-doc build` shall build the posters of `py-doc.yml` after the documents, with their PDFs, and `-f poster` and a poster's name shall choose them. | Should | Met |
| FR-150 | A poster shall carry its theme's fonts on request: its own font files, and the web fonts of its stylesheet. Those shall be downloaded once and kept, all of them or only the subsets named. A failed download shall leave the link, with a warning. | Could | Met |
| FR-151 | A poster's PDF shall have its theme's web fonts inside, though the container that prints it has no network. Offline, it shall be printed with the fallback fonts and a warning. | Should | Met |
| FR-152 | A poster shall draw its diagrams as SVG where the tool can, and embed its pictures, SVG included. | Should | Met |
| FR-153 | A poster's columns shall be balanced by the measured height of their sections, in order: the shortest tallest column, then the most even. A section marked `{.flow}` may go on in the next column, between its blocks. `split` shall choose the columns by hand. | Should | Met |
| FR-154 | A poster's `[[CAPTION:]]` captions shall be numbered, Figure and Table, in order down the poster. | Should | Met |
| FR-155 | A poster's charts shall take the axis range, gridline step, value labels, axis title, markers, shading and dashed series asked for. A column or bar axis shall start at zero. | Could | Met |
| FR-156 | A poster shall have blocks for numbered steps, a gallery of pictures, progress towards targets, a checklist, a comparison, people and highlighted figures. | Could | Met |
| FR-157 | `version: git` on a poster shall take its version from Git, as on a document. | Could | Met |
| FR-158 | `py-doc lint` and `py-doc build --lint` shall lint the posters of `py-doc.yml` with every rule but the document structure, acronym and passive voice rules. | Should | Met |
| FR-159 | `py-doc poster --watch` shall build the posters again on every save of their sources and reload them in the browser, and show a failed build's error over the last good page. | Could | Met |
| FR-160 | A poster's sections shall say in braces what they are and how they are laid out: `{.stats}`, `{.abstract}`, `{.summary}`, `{.references}`, `{.wide}` and `{cols=}`. No heading name shall have a meaning of its own, and every part shall be placed in the order of the file. Each kind shall have a choice of looks (`style=`), and `colour=` shall colour every one. | Should | Met |
| FR-161 | `py-doc docx --watch` and `py-doc slides --watch` shall build again on every save, serve an HTML preview of each file that reloads itself, and keep updating the preview while the document is open in Word or PowerPoint. The preview shall never overwrite a file of the user's. | Could | Met |
| FR-162 | The VS Code extension in `editors/vscode` shall preview py-doc Markdown in the editor without any tools, and start the live preview of the open file with the command that suits it. | Could | Met |

## Tool container

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-140 | Every program that is not Python shall run in one container image built from a definition shipped in the package, tagged by the hash of that definition. | Must | Met |
| FR-141 | `py-doc setup` shall install Docker Engine on Ubuntu or Debian, in WSL on Windows, after showing what it will run. | Should | Met |
| FR-142 | `py-doc doctor` shall say what works, what does not and what to do about it. | Must | Met |
| FR-143 | `py-doc tools` shall build, inspect, save, load and prune the image, and record tool checksums. | Should | Met |
