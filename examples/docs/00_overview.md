---
title: Meter Gateway Guide
subtitle: Example document for py-doc
author: A. Writer
date: 2026-01-15
version: "{{version}}"
status: Draft
classification: Internal
document_number: GD-001
description: A small guide that uses most of what py-doc can do.
---

# Overview

This guide describes the Meter Gateway, version {{version}}. It is an example for
trying out `py-doc`: build it with `py-doc build` from this folder.

[[INCLUDE: includes/audience.md]]

[[IF: internal]]
> [!WARNING]
> This build is for internal use. It contains notes that must not be sent to customers.
[[ENDIF]]

[[CAPTION:Figure]] The company logo
![Example Ltd](images/logo.png)

## What the gateway does

The gateway reads meters over **UART** and sends the readings to the head-end system
over *LwM2M* on **DTLS**. It buffers readings when the network is down.

> **Note:** Both callout spellings work. This one is `> **Note:** text`.

> [!TIP]
> This one is `> [!TIP]`. The kinds are NOTE, TIP, IMPORTANT, WARNING and `CAUTION`.

See the [requirements](#requirements) and the [design](#design).
