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

# Overview

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

# Diagrams

## Block diagram

[[CAPTION:Figure]] Blocks of the node
```blockdiag
blockdiag {
  sensors -> driver -> buffer -> uplink;
}
```

## Pinout

[[CAPTION:Figure]] Pin connections
```ditaa
+-------+    +-------+
| SDA   |<-->| Node  |
| SCL   |<---|       |
+-------+    +-------+
```

## Timing

[[CAPTION:Figure]] I2C timing
```wavedrom
{ signal: [
  { name: "SCL", wave: "p....." },
  { name: "SDA", wave: "x345x.", data: ["addr", "data", "ack"] }
]}
```

## Packet layout

[[CAPTION:Figure]] Header of a reading
```packetdiag
packetdiag {
  colwidth = 32;
  0-7: Version;
  8-15: Type;
  16-31: Length;
}
```

## Network

[[CAPTION:Figure]] Addresses on the site network
```nwdiag
nwdiag {
  network site {
    address = "10.0.0.0/24";
    sensor1 [address = "10.0.0.10"];
    broker [address = "10.0.0.2"];
  }
}
```

## Messages

[[CAPTION:Figure]] Publish and acknowledge
```seqdiag
seqdiag {
  node -> broker [label = "publish"];
  node <-- broker [label = "acknowledge"];
}
```

## Sketch

[[CAPTION:Figure]] A quick sketch
```pikchr
box "Sensor"; arrow; box "Node"; arrow; box "Cloud"
```

## Chart

[[CAPTION:Figure]] Average temperature by month
```vega-lite
{
  "data": {"values": [
    {"month": "Jan", "temp": 4}, {"month": "Feb", "temp": 5},
    {"month": "Mar", "temp": 9}, {"month": "Apr", "temp": 13}
  ]},
  "mark": "line",
  "encoding": {
    "x": {"field": "month", "type": "ordinal", "sort": null},
    "y": {"field": "temp", "type": "quantitative"}
  }
}
```
