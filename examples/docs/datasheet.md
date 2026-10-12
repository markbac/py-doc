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

## Frame layout

[[CAPTION:Figure]] Bytes of a reading frame
```bytefield-svg
(def boxes-per-row 8)
(draw-column-headers)
(draw-box "Version" {:span 2})
(draw-box "Type" {:span 2})
(draw-box "Length" {:span 4})
(draw-box "Payload" {:span 8})
```

## Wiring

[[CAPTION:Figure]] Cable to the sensor board
```wireviz
connectors:
  X1:
    pincount: 2
  X2:
    pincount: 2
cables:
  W1:
    wirecount: 2
    colors: [RD, BK]
connections:
  -
    - X1: [1, 2]
    - W1: [1, 2]
    - X2: [1, 2]
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

## Activities

[[CAPTION:Figure]] Who does what at start up
```actdiag
actdiag {
  measure -> publish -> sleep;
  lane sensor {
    label = "Sensor";
    measure;
  }
  lane radio {
    label = "Radio";
    publish;
    sleep;
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

## Syntax

[[CAPTION:Figure]] Syntax of a reading command
```railroad
Sequence
  Terminal "READ"
  Optional
    Terminal "ALL"
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

## Bar chart

[[CAPTION:Figure]] Readings per sensor, drawn with full Vega
```vega
{
  "width": 300, "height": 150, "padding": 5,
  "data": [{"name": "table", "values": [{"c": "A", "a": 4}, {"c": "B", "a": 7}, {"c": "C", "a": 2}]}],
  "scales": [
    {"name": "x", "type": "band", "domain": {"data": "table", "field": "c"}, "range": "width", "padding": 0.1},
    {"name": "y", "type": "linear", "domain": {"data": "table", "field": "a"}, "nice": true, "range": "height"}
  ],
  "axes": [{"orient": "bottom", "scale": "x"}, {"orient": "left", "scale": "y"}],
  "marks": [{"type": "rect", "from": {"data": "table"}, "encode": {"enter": {
    "x": {"scale": "x", "field": "c"}, "width": {"scale": "x", "band": 1},
    "y": {"scale": "y", "field": "a"}, "y2": {"scale": "y", "value": 0}}}}]
}
```
