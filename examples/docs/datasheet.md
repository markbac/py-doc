---
title: SN-100 Datasheet
subtitle: One page of facts per diagram type
author: A. Writer
date: 2026-01-15
version: "{{version}}"
status: Draft
classification: Public
document_number: SN-DS-001
description: Electrical and protocol data for the SN-100, drawn with every diagram type py-doc supports.
---

# Datasheet overview

The SN-100 measures temperature and humidity. This datasheet shows the diagram types that
`py-doc` draws. Each one is a fenced block, so the diagram stays in the Markdown and is drawn at
build time.

## Specification

[[CAPTION:Table]] Key data

| Item | Value |
|---|---|
| Supply voltage | 1.8 V to 3.6 V |
| Sleep current | 2 uA |
| Temperature range | -40 to 85 degrees Celsius |
| Interface | I2C, up to 400 kHz |

[[INCLUDE: guide/05_diagram_types.md]]
