---
title: Sensor Node Guide
subtitle: Integrating and operating the SN-100 sensor node
author: A. Writer
date: 2026-01-15
version: "{{version}}"
status: Draft
classification: Internal
document_number: SN-GD-001
description: How to integrate, commission and operate the SN-100 sensor node.
keywords: [IoT, sensor, MQTT]
toc_depth: 2
---

# Overview

[[STYLE:Lead Paragraph]] The SN-100 is a battery powered sensor node. It measures temperature and
humidity and publishes the readings to a cloud platform.

This guide describes version {{version}}. It is an example for trying out `py-doc`: build it with
`py-doc build guide` from this folder.

[[INCLUDE: ../includes/audience.md]]

[[IF: internal]]
> [!WARNING]
> This build is for internal use. It contains notes that must not be sent to customers.
[[ENDIF]]

[[CAPTION:Figure]] The company logo
![Example Ltd](../images/logo.png)

## What the node does

The node wakes on a timer, reads its sensors over I2C and publishes the values with *MQTT*
over **TLS**. It keeps readings in flash while the network is down and sends them later.[^buffer]
Battery life follows from the capacity $C$ and the average current $I_{avg}$ as $t = C / I_{avg}$.

[^buffer]: The buffer holds seven days of readings at the default interval.

## Conventions

Both callout spellings work. The kinds are note, tip, important, warning and caution.

> **Note:** this is the bold spelling, which reads well in plain Markdown.

> [!TIP]
> This is the marker spelling. It is the one GitHub and most editors show as a box.

> [!CAUTION]
> Do not open the enclosure while the node is connected to a charger.

Text can be **bold**, *italic*, ~~struck out~~ or `code`. Terms have a definition:

Sleep current
: The current the node draws between measurements.

Active current
: The current the node draws while it measures and transmits.

See the [requirements](#requirements) and the [design](#design). The [operations](#operations)
chapter has the glossary.
