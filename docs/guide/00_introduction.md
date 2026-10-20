---
title: py-doc user guide
subtitle: Markdown technical documentation to Word, PowerPoint, PDF, HTML and web sites
author: Mark Bacon
version: "0.1"
status: Draft
document_number: PD-UG-001
description: How to install py-doc, set up a documentation project, write, build, check and publish it.
keywords: [py-doc, Markdown, pandoc, documentation]
---

# Introduction

py-doc turns Markdown technical documentation into Word documents, PowerPoint decks, PDF, HTML and web sites. It checks the writing, draws diagrams of every common kind, writes and draws C4 architecture documentation from Structurizr models, and imports Word and PowerPoint files into Markdown. One `py-doc.yml` describes every document of a project.

This guide is for the people who write and build documentation with py-doc. The [requirements](../requirements/00_introduction.md) say what py-doc must do, and the [architecture](../architecture/00_introduction.md) describes how it does it. py-doc builds all three documents itself, from the `py-doc.yml` at the root of its repository.

## What py-doc does

| Command | What it does |
|---|---|
| `py-doc init` | Starts a project: `py-doc.yml`, a first document, and optionally a C4 model, templates and a site |
| `py-doc new` | Starts a legacy document, or numbers an existing Markdown file, from `doc-numbers.yml` at the repository root |
| `py-doc build` | Builds every document described in `py-doc.yml`, after its generators and, on request, lint, and then the site |
| `py-doc docx` | Converts Markdown files to Word |
| `py-doc slides` | Converts Markdown files to PowerPoint |
| `py-doc lint` | Checks writing style, glossary terms, acronyms, structure, links and project conventions |
| `py-doc check` | Checks a project without building it |
| `py-doc generate` | Writes the Markdown that the content generators make |
| `py-doc stats` | Counts the words, headings, tables, pictures and links of each document |
| `py-doc diff` | Compares two versions of documents section by section |
| `py-doc c4` | Checks, exports, draws and edits Structurizr workspaces |
| `py-doc site` | Makes and builds a web site of the documents with MkDocs or Astro + Starlight |
| `py-doc poster` | Builds self-contained HTML posters from Markdown, and prints them to PDF |
| `py-doc import` | Converts a Word document or a PowerPoint deck to Markdown |
| `py-doc template` | Checks and lists the styles of a Word or PowerPoint template |
| `py-doc tools`, `doctor`, `setup` | Builds and checks the tool container, and installs Docker Engine |
| `py-doc migrate` | Creates `py-doc.yml` from legacy `createdocs` build files |

Pandoc writes every output, and it runs in a container with every other tool, so only Python and Docker need installing. The linter reads Markdown with a parser of its own, so code, links and front matter are never checked as prose.

## How the guide is organised

1. [Installation](01_install.md): Python, Docker and the tool container.
1. [Projects](02_projects.md): `py-doc init`, `py-doc.yml` and `py-doc build`.
1. [Writing](03_writing.md): the Markdown py-doc reads, callouts, captions, includes, conditions, variables and diagrams.
1. [Outputs](04_outputs.md): Word, PowerPoint, PDF and HTML, templates and the build report.
1. [Importing](05_import.md): Word documents and PowerPoint decks to Markdown.
1. [C4 architecture](06_c4.md): Structurizr models, generated chapters and the live editor.
1. [Linting](07_lint.md): the built-in rules, structure rules, markdownlint and Vale.
1. [Web sites](08_sites.md): MkDocs and Astro + Starlight.
1. [Reference](09_reference.md): the Python API, exit statuses and troubleshooting.
1. [Legacy build files](10_legacy.md): `createdocs` build files, new documents, document numbers and migration.
1. [Generators, the build pipeline and analysis](11_pipeline.md): content generators, what `py-doc build` runs, and `check`, `stats` and `diff`.
1. [Posters](12_posters.md): every setting, block and theme of `py-doc poster`.
1. [Writing a poster](13_writing_posters.md): a poster from a blank file to a printed page.
1. [Writing a document](14_writing_documents.md): a technical document from an outline to a reviewed Word, PDF or HTML file.
1. [Writing a slide deck](15_writing_slides.md): a PowerPoint deck in Markdown, with notes, columns and diagrams.

## The examples

The `examples` folder of the repository is a small project that uses every feature: Markdown sources, a `py-doc.yml`, Word, PowerPoint, LaTeX and HTML templates, lint rules and a Structurizr workspace. Its `README.md` says which command makes which output.
