---
title: Drawn by the experts
subtitle: Circuits, chess, music and science, each by the library made for it
byline: py-doc example poster for the specialist fences (it needs the science image)
orientation: landscape
paper: a1
width: 1800
columns: 4
footer:
  left: Specialist fences
  right: docs/guide/03_writing.md, Circuits, chess and science
---

## Introduction {.abstract}

Each section is drawn by an open-source library in the tool image, from a short written form that py-doc reads. The scientific ones come from the optional science image, built the first time it is needed.

## 1. Electronics: a voltage divider

```circuit
V1: source 5 V | up
R1: resistor 10 kΩ | right
R2: resistor 10 kΩ | down
line | to V1.start
dot | at R1.end
```

## 2. Chess: the Italian game

```chess
fen: r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
highlight: c4 e4
arrow: f8 c5 | #a3322b
```

## 3. Music: a scale

```music
T:C major
M:4/4
L:1/4
CDEF|GABc|
```

## 4. Chemistry: caffeine

```molecule
Caffeine | CN1C=NC2=C1C(=O)N(C(=O)N2C)C
```

## 5. Evolution: the great apes

```phylogeny
(((Human,Chimpanzee),Gorilla),Orangutan);
```

## 6. Soil: its texture

```ternary
axes: Sand | Silt | Clay
Loam | 40 | 40 | 20
Clay loam | 30 | 35 | 35
Sandy loam | 65 | 25 | 10
```

## 7. Binding site: a logo

```seq-logo
TATAAA
TATAAT
TATTAA
TATAAA
CATAAA
```

## 8. Faults: which came together

```upset
Condensation | 31
Condensation, Low battery | 12
Low battery | 18
Cracked case, Condensation | 7
```

## 9. Antennas: on the Smith chart

```smith
z0: 50
Load | 25+15j
Matched | 50+0j
Open-ish | 200-80j
```

## 10. A plasmid: its map

```plasmid
size: 5400
ori | 100..780 | + | grey
AmpR | 950..1810 | - | #b4540a
Promoter | 2100..2350 | + | #0f7b7b
Cas9 | 2400..5100 | + | #a3322b
```

## 11. Colour: what screens show

```cie
gamut: sRGB
gamut: ITU-R BT.2020
D65 | 0.3127 | 0.3290
```

## 12. The sun over London

```sun-path
lat: 51.5
lon: -0.1
timezone: Europe/London
```

## 13. A steam cycle

```thermo-cycle
fluid: Water
state: Pump in | 10 | 40
state: Boiler in | 8000 | 42
state: Turbine in | 8000 | 500
state: Condenser in | 10 | 46
```

## 14. A gene: its locus

```gene-locus
size: 4000
Promoter | 50..300 | + | #0f7b7b
lacZ | 400..2100 | + | #3b6fb6
lacY | 2200..3400 | + | #2e7d32
Terminator | 3500..3600 | - | grey
```

## In short {.summary}

Let each library draw what it was made for; py-doc only reads what you wrote.
