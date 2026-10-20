---
title: SN-100 firmware {{version}}
subtitle: Longer life, faster joins, safer updates
byline: Release notes for installers and support
document_number: SN-PO-003
footer:
  left: Firmware {{version}}
  version: "{{version}}"
  right: Example dark poster, `py-doc poster poster/release.md`
variables:
  version: "2.1"
theme: dark
paper: a3
width: 1100
split: 2
---

## Stats

| Value | Label | Change | Verdict |
|---|---|---|---|
| 5.7 years | Battery life | +14 % | |
| 4 s | Typical join | -7 s | good |
| 2 | Firmware copies kept | +1 | |

## Abstract

Firmware 2.1 sends less, joins faster and can always go back to the last version that worked.

## 1. Power: sending less

The node now compares each reading with the last one sent and stays quiet when nothing has changed.

```chart type=column title="Messages a day"
series: 2.0, 2.1
Office | 1440 | 610
Warehouse | 1440 | 980
Cold store | 1440 | 1210
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

> **Warning:** do not update a node whose battery shows below 2.4 V. The update stops and the node keeps 2.0.

```timeline vertical
1 May | Pilot sites | 200 nodes
15 May | Every site | Over the air, overnight
1 June | 2.0 retired | No more 2.0 updates
```

## Summary

Install 2.1 everywhere: it costs one message and saves months of battery.

### Installers

Nothing changes on site. Joining is simply quicker.

### Support

Every update reports its result, so a failed node is visible at once.

## References

1. SN-100 Datasheet, SN-DS-001.
1. SN-100 release notes, firmware {{version}}.
