---
title: SN-100 firmware 2.1
subtitle: Longer life, faster joins, safer updates
byline: Release notes for installers and support
footer-left: Firmware 2.1
footer-right: Example dark poster, py-doc poster poster/release.md
theme: dark
paper: a3
width: 1100
---

## Stats

| Value | Label |
|---|---|
| +14 % | Battery life |
| 4 s | Typical join, was 11 s |
| 2 | Firmware copies kept |

## Abstract

Firmware 2.1 sends less, joins faster and can always go back to the last version that worked.

## 1. Power: sending less

The node now compares each reading with the last one sent and stays quiet when nothing has changed.

```segments
title: Messages a day, 2.0 against 2.1
6 | 2.0 | 1440 messages | grey
4 | 2.1 | about 900 | blue
```

## 2. Joining: faster

```flow
[Wake|navy] -scan 3 channels, was 8-> [Join|blue] -> [Report|green]
```

The node remembers the channel of its last gateway and tries it first.

## 3. Updates: safe by design

```cards cols=2 style=top
Two copies | The new firmware is written beside the old one | blue
Self-test | The node checks the new one before switching | green
Roll back | A failed self-test returns to the old copy | amber
Report | The result goes to the broker either way | navy
```

## 4. Upgrading

| From | Do this |
|---|---|
| 2.0 | Update over the air, no visit needed |
| 1.x | Update to 2.0 first, then 2.1 |

> Do not update a node whose battery shows below 2.4 V. The update stops and the node keeps 2.0.

## Summary

Install 2.1 everywhere: it costs one message and saves months of battery.

### Installers

Nothing changes on site. Joining is simply quicker.

### Support

Every update reports its result, so a failed node is visible at once.
