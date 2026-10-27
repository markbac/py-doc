# Science, maths and games

Physics, chemistry, maths, music and chess.

## `equation`

An equation with its terms explained.

````markdown
```equation
title: Weibull reliability
R(t) = e^{-(t/\eta)^{\beta}}
R(t) | Share of cells still working at age $t$ |
\eta | Characteristic life: 63 % have failed | h
\beta | Shape: above 1, the cells wear out |
```
````

```equation
title: Weibull reliability
R(t) = e^{-(t/\eta)^{\beta}}
R(t) | Share of cells still working at age $t$ |
\eta | Characteristic life: 63 % have failed | h
\beta | Shape: above 1, the cells wear out |
```

## `orbits`

Bodies in their orbits.

````markdown
```orbits star=Sun unit=" AU" habitable=0.95-1.67
orbit: Earth | 1 | blue
orbit: Mars | 1.52 | red | e=0.09
transfer: 1 | 1.52 | Hohmann transfer
lagrange: Earth
```
````

```orbits star=Sun unit=" AU" habitable=0.95-1.67
orbit: Earth | 1 | blue
orbit: Mars | 1.52 | red | e=0.09
transfer: 1 | 1.52 | Hohmann transfer
lagrange: Earth
```

## `optics`

Rays through lenses and mirrors.

````markdown
```optics type=cassegrain title="Cassegrain"
```
````

```optics type=cassegrain title="Cassegrain"
```

## `interferometer`

An interferometer's beams and paths.

````markdown
```interferometer type=michelson arm="4 km"
```
````

```interferometer type=michelson arm="4 km"
```

## `spacetime`

A spacetime diagram of world lines.

````markdown
```spacetime mode=lightcone
worldline: At rest | 0 | navy
worldline: Half light speed | 0.5 | blue
event: 1.5 | 0.6 | Outside the cone: nothing here can reach it
```
````

```spacetime mode=lightcone
worldline: At rest | 0 | navy
worldline: Half light speed | 0.5 | blue
event: 1.5 | 0.6 | Outside the cone: nothing here can reach it
```

## `energy-levels`

Energy levels and the transitions between them.

````markdown
```energy-levels
level: n=1 | -13.6
level: n=2 | -3.4
level: n=3 | -1.51
level: n=4 | -0.85
level: n=5 | -0.54
jump: n=3 | n=2 | Hα
jump: n=4 | n=2 | Hβ
jump: n=5 | n=2 | Hγ
jump: n=1 | n=2 | Lyman α
```
````

```energy-levels
level: n=1 | -13.6
level: n=2 | -3.4
level: n=3 | -1.51
level: n=4 | -0.85
level: n=5 | -0.54
jump: n=3 | n=2 | Hα
jump: n=4 | n=2 | Hβ
jump: n=5 | n=2 | Hγ
jump: n=1 | n=2 | Lyman α
```

## `feynman`

A Feynman diagram of particles and their interactions.

````markdown
```feynman topology=s-channel
in1: e⁻
in2: e⁺
mid: γ
out1: μ⁻
out2: μ⁺
```
````

```feynman topology=s-channel
in1: e⁻
in2: e⁺
mid: γ
out1: μ⁻
out2: μ⁺
```

## `standard-model`

The particles of the Standard Model.

````markdown
```standard-model highlight=t,H
```
````

```standard-model highlight=t,H
```

## `elements`

Elements of the periodic table.

````markdown
```elements cols=8
H He C O Si Fe Au U
```
````

```elements cols=8
H He C O Si Fe Au U
```

## `nuclide-chart`

A chart of nuclides.

````markdown
```nuclide-chart magic=yes valley=yes
1 | 0 | ¹H | stable
1 | 1 | ²H | stable
1 | 2 | ³H | beta-
2 | 1 | ³He | stable
2 | 2 | ⁴He | stable
3 | 3 | ⁶Li | stable
3 | 4 | ⁷Li | stable
4 | 5 | ⁹Be | stable
5 | 5 | ¹⁰B | stable
5 | 6 | ¹¹B | stable
6 | 6 | ¹²C | stable
6 | 7 | ¹³C | stable
6 | 8 | ¹⁴C | beta-
7 | 7 | ¹⁴N | stable
8 | 8 | ¹⁶O | stable
6 | 5 | ¹¹C | beta+
```
````

```nuclide-chart magic=yes valley=yes
1 | 0 | ¹H | stable
1 | 1 | ²H | stable
1 | 2 | ³H | beta-
2 | 1 | ³He | stable
2 | 2 | ⁴He | stable
3 | 3 | ⁶Li | stable
3 | 4 | ⁷Li | stable
4 | 5 | ⁹Be | stable
5 | 5 | ¹⁰B | stable
5 | 6 | ¹¹B | stable
6 | 6 | ¹²C | stable
6 | 7 | ¹³C | stable
6 | 8 | ¹⁴C | beta-
7 | 7 | ¹⁴N | stable
8 | 8 | ¹⁶O | stable
6 | 5 | ¹¹C | beta+
```

## `chess`

A chess position, with highlights and arrows.

````markdown
```chess
fen: r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
highlight: c4 e4
arrow: f8 c5 | #a3322b
```
````

```chess
fen: r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
highlight: c4 e4
arrow: f8 c5 | #a3322b
```

## `music`

Music in ABC notation, as a score. `abc` is the same fence.

````markdown
```music
T:Joined
L:1/8
C E G c2 z G c4
```
````

```music
T:Joined
L:1/8
C E G c2 z G c4
```

## `molecule`

A molecule from its SMILES string. It needs the science image (`py-doc tools build --science`).

````markdown
```molecule
Caffeine | CN1C=NC2=C1C(=O)N(C(=O)N2C)C
```
````

```molecule
Caffeine | CN1C=NC2=C1C(=O)N(C(=O)N2C)C
```

## `phylogeny`

A phylogenetic tree. It needs the science image (`py-doc tools build --science`).

````markdown
```phylogeny
(((Human,Chimpanzee),Gorilla),Orangutan);
```
````

```phylogeny
(((Human,Chimpanzee),Gorilla),Orangutan);
```

## `ternary`

Points on a ternary plot. It needs the science image (`py-doc tools build --science`).

````markdown
```ternary
axes: Sand | Silt | Clay
Loam | 40 | 40 | 20
Clay loam | 30 | 35 | 35
Sandy loam | 65 | 25 | 10
```
````

```ternary
axes: Sand | Silt | Clay
Loam | 40 | 40 | 20
Clay loam | 30 | 35 | 35
Sandy loam | 65 | 25 | 10
```

## `seq-logo`

A sequence logo. It needs the science image (`py-doc tools build --science`).

````markdown
```seq-logo
TATAAA
TATAAT
TATTAA
TATAAA
CATAAA
```
````

```seq-logo
TATAAA
TATAAT
TATTAA
TATAAA
CATAAA
```

## `upset`

An UpSet plot of set intersections. It needs the science image (`py-doc tools build --science`).

````markdown
```upset
Condensation | 31
Condensation, Low battery | 12
Low battery | 18
Cracked case, Condensation | 7
```
````

```upset
Condensation | 31
Condensation, Low battery | 12
Low battery | 18
Cracked case, Condensation | 7
```

## `smith`

Points on a Smith chart. It needs the science image (`py-doc tools build --science`).

````markdown
```smith
z0: 50
Load | 25+15j
Matched | 50+0j
Open-ish | 200-80j
```
````

```smith
z0: 50
Load | 25+15j
Matched | 50+0j
Open-ish | 200-80j
```

## `plasmid`

A plasmid map. It needs the science image (`py-doc tools build --science`).

````markdown
```plasmid
size: 5400
ori | 100..780 | + | grey
AmpR | 950..1810 | - | #b4540a
Promoter | 2100..2350 | + | #0f7b7b
Cas9 | 2400..5100 | + | #a3322b
```
````

```plasmid
size: 5400
ori | 100..780 | + | grey
AmpR | 950..1810 | - | #b4540a
Promoter | 2100..2350 | + | #0f7b7b
Cas9 | 2400..5100 | + | #a3322b
```

## `gene-locus`

Genes along a locus. It needs the science image (`py-doc tools build --science`).

````markdown
```gene-locus
size: 4000
Promoter | 50..300 | + | #0f7b7b
lacZ | 400..2100 | + | #3b6fb6
lacY | 2200..3400 | + | #2e7d32
Terminator | 3500..3600 | - | grey
```
````

```gene-locus
size: 4000
Promoter | 50..300 | + | #0f7b7b
lacZ | 400..2100 | + | #3b6fb6
lacY | 2200..3400 | + | #2e7d32
Terminator | 3500..3600 | - | grey
```

## `cie`

Colours on the CIE chromaticity diagram. It needs the science image (`py-doc tools build --science`).

````markdown
```cie
gamut: sRGB
gamut: ITU-R BT.2020
D65 | 0.3127 | 0.3290
```
````

```cie
gamut: sRGB
gamut: ITU-R BT.2020
D65 | 0.3127 | 0.3290
```

## `sun-path`

The sun's path across the sky. It needs the science image (`py-doc tools build --science`).

````markdown
```sun-path
lat: 51.5
lon: -0.1
timezone: Europe/London
```
````

```sun-path
lat: 51.5
lon: -0.1
timezone: Europe/London
```

## `thermo-cycle`

A thermodynamic cycle. It needs the science image (`py-doc tools build --science`).

````markdown
```thermo-cycle
fluid: Water
state: Pump in | 10 | 40
state: Boiler in | 8000 | 42
state: Turbine in | 8000 | 500
state: Condenser in | 10 | 46
```
````

```thermo-cycle
fluid: Water
state: Pump in | 10 | 40
state: Boiler in | 8000 | 42
state: Turbine in | 8000 | 500
state: Condenser in | 10 | 46
```
