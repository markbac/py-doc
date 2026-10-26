---
title: Architecture decisions
---

# Architecture decisions

Each decision records the context, the choice and its consequences.

## AD-01 Pandoc is the only renderer

- **Context**: py-doc began with three tools that drew Word and PowerPoint files themselves, each with its own Markdown parser and gaps.
- **Decision**: pandoc writes every format. py-doc prepares its input with Lua filters and finishes Word and PowerPoint files afterwards.
- **Consequences**: one parser for every output, mature format support, and pandoc's own warnings. Docker is needed for every conversion, and pandoc's behaviour can change between versions, so its version is pinned in `tools.lock`.

## AD-02 Every tool runs in one container image

- **Context**: the toolchain is large (TeX, Java, Chromium, Node, Python tools) and differs between machines.
- **Decision**: one image built from a definition in the package, tagged by its hash, run as the calling user with only the folders each step needs.
- **Consequences**: the same results on every machine and in CI, and nothing to install but Python and Docker. The first build takes 5 to 30 minutes and about 4 GB. On Windows it needs WSL 2.

## AD-03 Docker Engine in WSL, not Docker Desktop

- **Context**: Docker Desktop needs a licence in larger companies and adds a layer that changes file paths and permissions.
- **Decision**: on Windows, Docker Engine runs in an Ubuntu or Debian WSL 2 distribution, installed by `py-doc setup`.
- **Consequences**: no licence question and Linux file semantics. py-doc must translate paths and keep the distro running while a long-lived container needs it.

## AD-04 structurizr-cli reads the DSL, Structurizr Local draws the views

- **Context**: the Structurizr DSL is large and evolving, and diagrams should look as they do in Structurizr.
- **Decision**: structurizr-cli exports the DSL to JSON, which py-doc reads. Structurizr Local (successor of the retired Structurizr Lite) draws the views in headless Chromium.
- **Consequences**: no DSL parser to maintain, and identical pictures. Drawing needs Docker and takes seconds to start Local.

## AD-05 Layouts live in `workspace.json` beside the DSL

- **Context**: authors arrange C4 views by hand in Structurizr, and the arrangement must survive edits to the model and reach the documents.
- **Decision**: `py-doc c4 up` gives Local the project folder, so it saves layouts to `workspace.json` beside the `.dsl`, and builds take that file with the DSL. The DSL cannot hold manual positions.
- **Consequences**: two files describe one workspace, and both belong in Git. Builds work on a copy, so they never write either file.

## AD-06 Sites are orchestrated, not replaced

- **Context**: teams already use MkDocs or Starlight, with their own themes and plugins.
- **Decision**: py-doc writes pages and a navigation file of its own, and runs the site's tool. It never edits the site's configuration, and an engine adapter holds everything engine-specific.
- **Consequences**: an existing site keeps its look, and adding an engine is one class. The site's configuration must take in py-doc's navigation file, and `py-doc site generate` says so when it does not.

## AD-07 The linter has its own Markdown parser

- **Context**: lint findings need exact lines and source text, and must skip code, links and front matter reliably.
- **Decision**: the linter parses with markdown-it-py into py-doc's own document model.
- **Consequences**: precise, fast checks without the container. Two parsers can disagree on edge cases, so the anchor rules are tested against pandoc's own identifiers.

## AD-08 Previews are served, not written beside the outputs

- **Context**: authors want to see a document while they write it. Word and PowerPoint have no live view, and a document open in Word cannot be written. The in-editor Markdown preview cannot draw most diagrams.
- **Decision**: `--watch` builds an HTML twin of each document with the same pipeline, and keeps it in `.py-doc/preview`. It serves the twin with a reload script, added as the page is served. Since extension 2.0, the VS Code extension runs that command, and has no preview of its own. Its old instant preview re-implemented py-doc's blocks in JavaScript, and drifted from the build.
- **Consequences**: the preview shows every diagram exactly as the build draws it, and a document open in Word does not stop it. It is one HTML page: slides are boxes and page breaks are lines, but Word's page layout is not shown. A first build waits for the tool container.

## AD-09 A poster block is drawn once, and is a picture everywhere else

- **Context**: posters have many native blocks (charts, scales, shapes, protocol and physics diagrams), and authors want the same blocks in Word, PowerPoint, PDF and sites. Writing each block again for each output would double the work and drift.
- **Decision**: a block is drawn by one function, which returns its HTML, or its picture alone when it is all SVG. Documents, decks and sites draw it as a picture through the diagram pipeline: the SVG as it is, or the HTML photographed by the container's Chromium. The VS Code preview shows py-doc's own `--watch` page, and draws no block itself.
- **Consequences**: a new block works in every output and in the editor as soon as it is written. In Word and PowerPoint a block made of HTML is a PNG, not editable text. Drawing it needs the tool container.

## AD-10 Specialist fences have a written form, and the heavy libraries an image of their own

- **Context**: circuits, chessboards, molecules, Smith charts and the like are drawn well by existing libraries, which take code. Running code from a document would make every fence a program; the scientific libraries add a few hundred MB that most projects never use.
- **Decision**: each such fence has a short written form of its own, which py-doc reads and turns into the JSON of a runner script in the image; no code of a fence runs. The libraries without matplotlib (schemdraw, python-chess, abcjs) are in the tool image. The scientific ones are in a second image, built on top of the tool image the first time a fence needs it.
- **Consequences**: a fence can only say what its written form allows, so a new feature of a library needs a change to py-doc. A first use of a scientific fence waits a few minutes for the science image. A project without one stays as small as before.

