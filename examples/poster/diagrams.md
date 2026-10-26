---
title: Which tool draws what
subtitle: One small example of every diagram the tool container draws
byline: py-doc poster gallery, to check each renders in the poster's theme
orientation: landscape
paper: a1
width: 1800
columns: 4
footer:
  left: Diagram gallery
  right: docs/guide/13_writing_posters.md, Which tool for which diagram
---

## Introduction {.abstract}

Each section is one diagram type that a tool in the container already draws. Use these before writing a native block: they need no code in py-doc, and they work in documents and sites too.

## 1. Flow: sankey

```mermaid
sankey-beta
Grid,Home,40
Solar,Home,25
Solar,Battery,15
Battery,Home,10
Home,Losses,5
```

## 2. Trade-off: quadrant chart

```mermaid
quadrantChart
  title Range against bandwidth
  x-axis Short range --> Long range
  y-axis Low bandwidth --> High bandwidth
  quadrant-1 Cellular
  quadrant-2 Local
  quadrant-3 Sensor nets
  quadrant-4 LPWAN
  NB-IoT: [0.8, 0.25]
  LTE-M: [0.7, 0.55]
  BLE: [0.15, 0.4]
  Wi-Fi: [0.25, 0.85]
  LoRaWAN: [0.9, 0.1]
```

## 3. Comparison: radar

```mermaid
radar-beta
  axis r["Range"], b["Battery"], w["Bandwidth"], i["Indoor"], c["Cost"]
  curve nb["NB-IoT"]{8, 9, 3, 9, 7}
  curve lm["LTE-M"]{7, 7, 6, 7, 5}
  max 10
```

## 4. Proportion: treemap

```mermaid
treemap-beta
"Crypto"
    "X.509": 52
    "ECDSA": 38
"Network"
    "CoAP and DTLS": 44
    "Modem": 26
"RTOS": 40
```

## 5. Overlap: Venn

```mermaid
venn-beta
  set A["Mains powered"]
  set B["Battery powered"]
  union A,B["Hybrid nodes"]
```

## 6. Root cause: Ishikawa

```mermaid
ishikawa-beta
Battery drains in a year
    Hardware
        Leaky capacitor
        Floating pins
    Firmware
        Debug UART on
        Retry storm
    Network
        Poor indoor signal
```

## 7. Strategy: Wardley map

```mermaid
wardley-beta
title Metering service
anchor Customer [0.95, 0.60]
component Billing [0.70, 0.45]
component Head-end [0.50, 0.55]
component Cloud [0.20, 0.85]
Customer -> Billing
Billing -> Head-end
Head-end -> Cloud
```

## 8. Files: tree view

```mermaid
treeView-beta
    firmware/
        src/
            main.c
            radio.c
        tests/
        README.md
```

## 9. Ideas: mind map

```mermaid
mindmap
  root((LwM2M))
    Objects
      Device
      Firmware
    Interfaces
      Bootstrap
      Reporting
```

## 10. Branches: git graph

```mermaid
gitGraph
  commit
  branch feature
  commit
  commit
  checkout main
  commit
  merge feature
  commit tag: "v2.1"
```

## 11. Dates: timeline

```mermaid
timeline
  2016 : Release 13 : NB-IoT
  2017 : Release 14 : Cat-NB2
  2019 : Release 15 : Wake-up signal
```

## 12. Plan: Gantt

```mermaid
gantt
  dateFormat YYYY-MM-DD
  section Pilot
    Build      :a1, 2026-01-05, 30d
    Field test :after a1, 45d
  section Release
    Roll out   :2026-04-01, 30d
```

## 13. Values: XY chart

```mermaid
xychart-beta
  title "Messages a day"
  x-axis [Mon, Tue, Wed, Thu, Fri]
  y-axis "Messages" 0 --> 1500
  bar [1440, 980, 610, 700, 650]
  line [1440, 980, 610, 700, 650]
```

## 14. Layout: block diagram

```mermaid
block-beta
  columns 3
  Core Flash SRAM
  DMA:2 ADC
```

## 15. Hand-offs: swimlanes

```mermaid
swimlane-beta LR
  subgraph Customer
    A([Top up]) --> B(Send payment)
  end
  subgraph Supplier
    C[Credit the meter]
  end
  B --> C
```

## 16. Decisions: flowchart

```mermaid
flowchart TD
  A{Balance below zero?} -->|No| B[Supply on]
  A -->|Yes| C{Friendly hours?}
  C -->|Yes| B
  C -->|No| D[Cut off]
```

## 17. Bits: packet

```mermaid
packet-beta
  0-1: "Ver"
  2-3: "T"
  4-7: "TKL"
  8-15: "Code"
  16-31: "Message ID"
```

## 18. Timing: WaveDrom

```wavedrom
{ "signal": [
  { "name": "CLK",  "wave": "p......" },
  { "name": "CS#",  "wave": "10....1" },
  { "name": "MOSI", "wave": "x=.=.x.", "data": ["A5", "3C"] }
]}
```

## 19. Task states: PlantUML timing

```plantuml
@startuml
concise "Radio task" as R
concise "Sensor task" as S
@0
R is Sleep
S is Run
@10
S is Sleep
R is Send
@25
R is Sleep
@enduml
```

## 20. Messages: PlantUML sequence

```plantuml
@startuml
!pragma teoz true
participant Node
participant Server
Node ->(10) Server : CON POST /rd
Server ->(10) Node : 2.01 Created
Node ->x Server : lost NON
@enduml
```

## 21. Structure: Graphviz

```dot
digraph G {
  rankdir=LR; node [shape=record];
  stack [label="{stack|<p> main()|parse()}"];
  heap [label="{heap|<n> node 1|node 2}"];
  stack:p -> heap:n;
}
```

## 22. Rack: rackdiag

```rackdiag
rackdiag {
  8U;
  1: Patch panel;
  2: Switch;
  3: Firewall;
  4: Server [2U];
  6: UPS [2U];
}
```

## 23. Statistics: Vega-Lite

```vega-lite
{
  "data": {"values": [
    {"g": "A", "v": 3}, {"g": "A", "v": 5}, {"g": "A", "v": 4}, {"g": "A", "v": 9},
    {"g": "B", "v": 6}, {"g": "B", "v": 7}, {"g": "B", "v": 8}, {"g": "B", "v": 2}
  ]},
  "mark": "boxplot",
  "encoding": {"x": {"field": "g", "type": "nominal"}, "y": {"field": "v", "type": "quantitative"}}
}
```

## 24. Topology: architecture with icons

```mermaid
architecture-beta
    group cloud(logos:aws)[Cloud]
    service api(logos:aws-lambda)[API] in cloud
    service db(logos:postgresql)[Readings] in cloud
    service gateway(tabler:router)[Gateway]
    service node(mdi:thermometer)[Node]
    api:R -- L:db
    gateway:T -- B:api
    node:R -- L:gateway
```

## In short {.summary}

Look here first: if a tool in the container draws it, write the diagram, not a new block.
