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
