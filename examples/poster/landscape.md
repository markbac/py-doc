---
title: Commissioning an SN-100 network
subtitle: From an empty building to readings on the dashboard in one day
byline: Example Instruments field engineering
footer-left: Example Instruments
footer-right: Example landscape poster, py-doc poster poster/landscape.md
orientation: landscape
theme: brand/example-instruments.yml
paper: a1
---

## Stats

| Value | Label |
|---|---|
| 1 day | To commission 50 nodes |
| 3 | Gateways for a three-storey building |
| -95 dBm | Weakest signal accepted |
| 0 | Tools beyond a phone and a ladder |

## Abstract

A network of SN-100 nodes reports through gateways to an MQTT broker. Commissioning places the gateways, joins each node, checks its signal and readings, and records where it is. This poster is the checklist the field team follows.

## 1. Plan: survey the site

Walk the building with the survey app before fitting anything.

```cards cols=1 style=label
Gateways | One a floor, near the middle, away from metal cabinets
Nodes | At head height, out of sunlight and away from heaters
Records | A floor plan with every node's number and room
```

> Concrete floors stop the radio. Plan one gateway on every floor, even a small one.

## 2. Install: fit the hardware

```lanes
Gateway | *Mount | *Power | *Ethernet | Check light
Node | *Fix plate | *Insert cell | Clip on
```

Fit every gateway before the first node, so a node always has a gateway to join.

## 3. Join: add the node to the network

```flow
[Unjoined|slate] -button 3 s-> [Joining|sea] -key accepted-> [Joined|teal]
[Joining|sea] -no gateway-> [Retries every 10 min]
```

```mermaid
sequenceDiagram
  participant N as Node
  participant G as Gateway
  participant B as Broker
  N->>G: Join request
  G->>B: Is the key known?
  B-->>G: Yes
  G-->>N: Joined
```

Fig. 1 A node joins through the nearest gateway.

## 4. Verify: check each node

The display shows the result of the join, then the first reading.

```lcd
JOINED  GW-2
RSSI -71 dBm
-- Good signal

T  21.4 C
RH 48 %
-- First reading
```

## 5. Signal: what is good enough

```segments
title: Signal strength at the node (dBm)
3 | Excellent | -40 to -70 | teal
2 | Good | -70 to -85 | sea
2 | Weak | -85 to -95 | sand
1 | Move it | below -95 | coral
```

A weak node works, but it retries more and its cell lasts less.

## 6. Troubleshoot: when a node will not join

| Display | Do this |
|---|---|
| `NO GW` | Check the gateway light, then move the node nearer |
| `KEY ERR` | Scan the node's label again in the app |
| `LOW BAT` | Fit a new cell before joining |

## Summary

Plan the gateways, fit them first, join each node and record where it is.

### Survey first

The floor plan decides the gateways, not the other way round.

### One node at a time

Join, check the signal, read the display, write it down.

### Leave a record

The floor plan with node numbers is the handover document.
