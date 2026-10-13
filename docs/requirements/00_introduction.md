---
title: py-doc requirements specification
subtitle: What the documentation toolset must do, and how well
author: Mark Bacon
version: "0.1"
status: Draft
document_number: PD-RS-001
description: The functional and quality requirements of py-doc, its constraints, and where each requirement is met and tested.
keywords: [py-doc, requirements]
---

# Introduction

## Purpose

This document states what py-doc must do and how well it must do it. It is the reference for deciding whether a change belongs in py-doc, whether a feature is finished, and what the tests must show. The [architecture](../architecture/00_introduction.md) describes how the requirements are met, and the [user guide](../guide/00_introduction.md) describes how to use the result.

## Scope

py-doc is a command line toolset and Python package for documentation written in Markdown. It covers the whole life of a technical document:

- starting a project, and importing existing Word and PowerPoint files;
- writing, with includes, conditions, variables, callouts, captions and diagrams;
- checking the writing, the structure and C4 models;
- building Word, PowerPoint, PDF and HTML files, and web sites;
- documenting software architecture from Structurizr C4 models.

py-doc does not edit Word or PowerPoint files interactively, host or serve web sites, or store documents.

## Readers

- **Maintainers** decide what to build next and check that a change keeps every requirement.
- **Contributors** find what a module must do and which tests show it.
- **Authors** and teams who adopt py-doc see what they can rely on.

## Conventions

Each requirement has an identifier, a statement, a priority and a status.

| Prefix | Kind |
|---|---|
| `FR-` | Functional requirement: something py-doc does |
| `QR-` | Quality requirement: how well it does it (reliability, security, portability, performance, usability, maintainability) |
| `CON-` | Constraint: a decision fixed from outside, which the design must work within |

| Priority | Meaning |
|---|---|
| Must | Without it py-doc does not serve its purpose |
| Should | Expected by users; left out only with a reason |
| Could | Useful; done when it costs little |

| Status | Meaning |
|---|---|
| Met | Implemented and tested |
| Partly met | Some of the statement is implemented: the notes say what is missing |
| Open | Not implemented yet |

"Shall" states a requirement. Issue numbers such as #42 refer to the issues of the py-doc repository.
