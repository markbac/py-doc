---
title: Safety and structure on one page
subtitle: Bow-ties, fault trees, safety cases, logic, ladders and flows
byline: py-doc example poster for the engineering blocks
orientation: landscape
paper: a1
width: 1800
columns: 3
footer:
  left: Engineering blocks
  right: docs/guide/12_posters.md, Engineering structure diagrams
---

## Introduction {.abstract}

Each section is one engineering block. Each keeps the symbols of its notation, so a safety engineer or a controls engineer reads it at a glance.

## 1. Risk: the bow-tie

```bowtie
hazard: Lithium cell
top: Thermal runaway
threat: Overcharge | Charger cut-off, Cell monitor
threat: Crush | Steel enclosure
consequence: Fire | Vent path, Fire wall
consequence: Toxic smoke | Smoke alarm
```

## 2. Causes: the fault tree

```fault-tree
or: Node stops reporting
  and: No power
    basic: Cell flat | 1e-3
    basic: Backup fails | 0.05
  basic: Radio fault | 2e-4
  undeveloped: Gateway down
```

## 3. Argument: the safety case

```gsn
goal G1: The node is safe to install
  context C1: Indoor use, 0 to 40 °C
  strategy S1: Argue over each hazard
    goal G2: Overheating is prevented
      solution Sn1: Thermal test report
    goal G3: Venting is contained | undeveloped
```

## 4. Logic: the Karnaugh map

```kmap name=Alarm
vars: A B C D
ones: 0 2 5 7 8 10 13 15
dont: 6
```

## 5. Control: the ladder

```plc-ladder
rung: Start and stop the pump
NO Start | NC Stop | COIL Pump
branch: NO Pump
rung: Run the pump for 30 s at most
NO Pump | TON T1 PT=30s
rung: Stop it after that
NO T1 | RESET Pump
```

## 6. Firmware: the structogram

```structogram
Wake on the timer
Read the sensor
if Reading changed?
  Send it
else
  Count the skip
while Queue not empty
  Send the next message
Sleep
```

## 7. Interfaces: the N-squared chart

```n2
items: Sensor, Controller, Radio, Cloud
Sensor -> Controller | Reading over I2C
Controller -> Radio | Message
Radio -> Cloud | MQTT publish
Cloud -> Controller | New settings
```

## 8. Functions: IDEF0

```idef0
box: A1 Measure the air
in: Air
control: Sample interval
out: Reading
mech: Sensor
box: A2 Send the reading
in: Reading
control: Radio settings
out: Message
mech: Radio
```

## 9. Production: the value stream

```vsm
supplier: Cell maker | Weekly
customer: Installer | 400 a day
inventory: 5 days
process: Solder | C/T 40 s | Uptime 92 %
inventory: 2 days
process: Test | C/T 30 s | 1 operator
inventory: 1 day
process: Pack | C/T 20 s
```

## In short {.summary}

Use the notation your readers already know: its symbols carry meaning that boxes and arrows do not.
