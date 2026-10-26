---
title: Shapes that explain
subtitle: Layers, rings and proportions, drawn to their share
byline: py-doc example poster for the shape blocks
orientation: landscape
paper: a1
width: 1800
columns: 4
footer:
  left: Shape blocks
  right: docs/guide/12_posters.md, Poster blocks
---

## Introduction {.abstract}

Each section is one shape block. The shape carries the meaning: a pyramid for proportions that narrow, rings for layers that wrap a core, a column for altitude, a map for memory.

## 1. Testing: the pyramid

```pyramid
End-to-end | 5 % | Real network and hardware | red
Hardware in the loop | 20 % | Automated rig, RF attenuators | amber
Integration | 25 % | Simulated peripherals | blue
Unit tests | 50 % | Off target, under a second | green
```

## 2. Exoplanets: the funnel

```funnel
Candidates | 4,000 | Transit signals | blue
Vetted | 1,200 | Not false positives | navy
Confirmed | 300 | Radial velocity | green
```

## 3. Requests: the cone

```cone
Ideas | 400 | Every request | blue
Scoped | 120 | Fits the plan | navy
Built | 30 | Shipped | green
```

## 4. Protocol: the stack

```stack
Application | L7 | LwM2M objects | green
Transport | L4 | CoAP over DTLS | blue
Network | L3 | IPv6 or NIDD | navy
Radio | L1-2 | NB-IoT | grey
side: Secured | 2-2 | red
```

## 5. Architecture: the rings

```target
Domain | Entities and rules | navy
Use cases | What the system does | blue
Adapters | Controllers and gateways | green
Infrastructure | Database and network | grey
```

## 6. The Sun: a cutaway

```cutaway type=sphere unit=" R☉"
Core | 0.25 | 15 million K | amber
Radiative zone | 0.7 | Light takes 170,000 years | red
Convective zone | 1 | Rising plasma | brown
```

## 7. The air: a column

```cutaway type=column unit=" km"
0 | 12 | Troposphere | Weather | blue
12 | 50 | Stratosphere | Ozone layer | navy
50 | 85 | Mesosphere | Meteors burn up | green
85 | 120 | Thermosphere | Aurora | amber
```

## 8. Mirrors: to scale

```sizes shape=hexagon
ELT | 39 | Extremely Large Telescope | navy
JWST | 6.5 | 18 segments | amber
Hubble | 2.4 | One mirror | blue
```

## 9. Coffee: in the cup

```vessels
Espresso | 30 ml Espresso (amber)
Cortado | 30 ml Espresso (amber) + 30 ml Milk (#f3e3c3)
Flat white | 60 ml Ristretto (amber) + 120 ml Microfoam (#f3e3c3)
```

## 10. Flash and RAM: the map

```memory
0x0800_0000 | 32 KB | Bootloader | navy
0x0800_8000 | 224 KB | Application | blue
0x2000_0000 | 8 KB | Heap | green | up
0x2000_E000 | 8 KB | Stack | amber | down
```

## 11. mRNA: the tape

```tape
cells: A U G G C U U A A
1-3 | Met (start) | green
4-6 | Ala | blue
7-9 | Stop | red
```

## 12. DMA: the ring buffer

```ring cells=16
fill: 3-9 | Waiting samples | blue
pointer: 3 | TAIL (read) | green
pointer: 10 | HEAD (write) | red
```

## 13. Water: the cycle

```cycle
Evaporation | Sun heats the sea | amber
Condensation | Clouds form | blue
Precipitation | Rain and snow | navy
Collection | Rivers and lakes | green
```

## 14. The grid: in balance

```balance unit=" GW"
left: Generation | 52 | green
right: Demand | 50 | red
right: Losses | 1.5 | grey
```

## 15. A product: the iceberg

```iceberg waterline="What the customer sees"
above: The app
below: Device management
below: Security and keys
below: Power budget
below: Firmware updates
```

## 16. A node: its layers

```onion
Cell | Lithium, 2.4 Ah | amber
Board | Sensor, controller and radio | blue
Case | IP65, wall mount | grey
```

## In short {.summary}

A shape is worth drawing when its form says something the words do not: how much, what wraps what, and what lies beneath.
