---
title: py-doc architecture
subtitle: How the documentation toolset is built
author: Mark Bacon
version: "0.1"
status: Draft
document_number: PD-AD-001
description: The structure of py-doc, how a document is built, where its tools run, and the decisions behind them.
keywords: [py-doc, architecture, C4]
---

# Introduction

This document describes how py-doc meets its [requirements](../requirements/00_introduction.md). It covers what py-doc is made of, how a document travels from Markdown to each output, where the tools run, and why it is built this way. It is for maintainers and contributors.

py-doc writes the C4 chapters from the Structurizr model in `docs/architecture/workspace.dsl`, the way any py-doc project documents its architecture. They cover the context, containers, components, relationships, deployment, the dynamic view of a build, and the element catalogue. Change the model, not those chapters. `py-doc c4 up docs/architecture/workspace.dsl` opens it in Structurizr to arrange its views.

## Goals

- **One toolset** for the life of a technical document: start, import, write, check, build and publish.
- **Markdown as the source** of every format, so a document is written once and reviewed as text.
- **Nothing lost quietly**: every warning names what it concerns, and every failure stops with the tool's own message.
- **The same result everywhere**: the same tools, at the same versions, on Linux, Windows and in CI.
- **The user's files are safe**: a build changes no source, and nothing a user wrote is replaced.

## Principles

1. **Delegate, do not reimplement.** Pandoc writes the documents, Structurizr draws the views, MkDocs and Astro build the sites, Vale and markdownlint check prose. py-doc prepares their input, runs them and checks their output.
1. **Tools in one container.** Every program that is not Python runs in the tool image, started fresh for each step, as the calling user, with only the folders it needs.
1. **Configuration is checked, not guessed.** `py-doc.yml` is validated key by key, and a mistake is an error that names its place.
1. **Fail loudly and precisely.** A broken diagram, view or tool stops the step with the file, the line and the tool's message. `--keep-going` collects them.
1. **Own files only.** py-doc writes its own files (outputs, caches, generated pages, navigation) and records them, and leaves everything else as it found it.
