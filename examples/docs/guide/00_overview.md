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
subject: Integrating the SN-100
category: Technical documentation
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
![Example Ltd](images/logo.png){width=40%}

## What the node does

The node wakes on a timer, reads its sensors over I2C and publishes the values with *MQTT*
over **TLS**. It keeps readings in flash while the network is down and sends them later.[^buffer]
Battery life follows from the capacity $C$ and the average current $I_{avg}$:

$$t = \frac{C}{I_{avg}}$$

[^buffer]: The buffer holds seven days of readings at the default interval.

## Conventions

### Callouts

Both callout spellings work, for all five kinds: note, tip, important, warning and caution.
The marker spelling is the one GitHub and most editors show as a box.

> [!NOTE]
> A note gives extra information.

> [!TIP]
> A tip suggests a better way.

> [!IMPORTANT]
> Important text is something the reader must not miss.

> [!WARNING]
> A warning names a risk.

> [!CAUTION]
> Do not open the enclosure while the node is connected to a charger.

The bold spelling reads well in plain Markdown:

> **Note:** a note in the bold spelling.

> **Tip:** a tip in the bold spelling.

> **Important:** an important point in the bold spelling.

> **Warning:** a warning in the bold spelling.

> **Caution:** a caution in the bold spelling.

An ordinary quotation is not a callout:

> Measure twice, publish once.

### Text

Text can be **bold**, *italic*, ***both***, ~~struck out~~ or `code`. Chemical and unit text uses
subscripts and superscripts, as in H~2~O and m^2^. A line can end with a backslash\
to break it. Links can point outside, such as the [py-doc repository](https://github.com/markbac/py-doc), or inside.

[[STYLE:Block Text]] This paragraph uses a Word style named in the Markdown. Other formats show the text as it is.

#### A fourth-level heading

Terms have a definition:

Sleep current
: The current the node draws between measurements.

Active current
: The current the node draws while it measures and transmits.

See the [requirements](#requirements) and the [design](#design). The [operations](#operations)
chapter has the glossary.
