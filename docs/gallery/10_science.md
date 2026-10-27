# Science, maths, music and games

Physics, astronomy, chemistry, biology, maths, music and chess. The poster blocks are drawn by py-doc, and `chess` and `music` by libraries in the tool image. The last eleven are drawn by the optional science image, which `py-doc tools build --science` builds, as does the first document that uses one.

## `equation`

Formula cards in LaTeX, each with a legend of its symbols and units.

````markdown
```equation cols=2
title: Average current
I_{avg} = \frac{I_{s} t_{s} + I_{m} t_{m} + I_{tx} t_{tx}}{t_{s} + t_{m} + t_{tx}}
I_{s} | Sleep current | µA
I_{m} | Current while measuring | mA
I_{tx} | Current while sending | mA
t | Time spent in each state, a day | s
---
title: Battery life
L = \frac{C \, (1 - d)}{24 \, I_{avg}}
L | Battery life | days
C | Cell capacity | mAh
d | Derating for temperature and age |
I_{avg} | Average current | mA
---
title: Weibull reliability
R(t) = e^{-(t/\eta)^{\beta}}
R(t) | Share of cells still working at age $t$ |
\eta | Characteristic life: 63 % have failed | h
\beta | Shape: above 1, the cells wear out |
---
title: Free-space path loss
L_{fs} = 20 \log_{10}(d) + 20 \log_{10}(f) + 32.45
d | Distance | km
f | Frequency | MHz
L_{fs} | Loss | dB
```
````

```equation cols=2
title: Average current
I_{avg} = \frac{I_{s} t_{s} + I_{m} t_{m} + I_{tx} t_{tx}}{t_{s} + t_{m} + t_{tx}}
I_{s} | Sleep current | µA
I_{m} | Current while measuring | mA
I_{tx} | Current while sending | mA
t | Time spent in each state, a day | s
---
title: Battery life
L = \frac{C \, (1 - d)}{24 \, I_{avg}}
L | Battery life | days
C | Cell capacity | mAh
d | Derating for temperature and age |
I_{avg} | Average current | mA
---
title: Weibull reliability
R(t) = e^{-(t/\eta)^{\beta}}
R(t) | Share of cells still working at age $t$ |
\eta | Characteristic life: 63 % have failed | h
\beta | Shape: above 1, the cells wear out |
---
title: Free-space path loss
L_{fs} = 20 \log_{10}(d) + 20 \log_{10}(f) + 32.45
d | Distance | km
f | Frequency | MHz
L_{fs} | Loss | dB
```

## `orbits`

Orbits round a star, with an ellipse, a Hohmann transfer, Lagrange points, a comet and a habitable zone.

````markdown
```orbits star=Sun unit=" AU" habitable=0.95-1.67
orbit: Venus | 0.72 | amber
orbit: Earth | 1 | blue
orbit: Mars | 1.52 | red | e=0.09
transfer: 1 | 1.52 | Hohmann transfer to Mars
lagrange: Earth
```
````

```orbits star=Sun unit=" AU" habitable=0.95-1.67
orbit: Venus | 0.72 | amber
orbit: Earth | 1 | blue
orbit: Mars | 1.52 | red | e=0.09
transfer: 1 | 1.52 | Hohmann transfer to Mars
lagrange: Earth
```

````markdown
```orbits star=Sun unit=" AU"
orbit: Earth | 1 | blue
orbit: Jupiter | 5.2 | brown | e=0.05
comet: 3.1 | 0.85 | A short-period comet
```
````

```orbits star=Sun unit=" AU"
orbit: Earth | 1 | blue
orbit: Jupiter | 5.2 | brown | e=0.05
comet: 3.1 | 0.85 | A short-period comet
```

## `optics`: refractor

The ray path of a telescope with its parts labelled.

````markdown
```optics type=refractor title="Refractor"
```
````

```optics type=refractor title="Refractor"
```

## `optics`: Newtonian

````markdown
```optics type=newtonian title="Newtonian reflector"
```
````

```optics type=newtonian title="Newtonian reflector"
```

## `optics`: Cassegrain

````markdown
```optics type=cassegrain title="Cassegrain"
```
````

```optics type=cassegrain title="Cassegrain"
```

## `optics`: three-mirror anastigmat

````markdown
```optics type=tma title="Three-mirror anastigmat"
```
````

```optics type=tma title="Three-mirror anastigmat"
```

## `interferometer`: Michelson

The beam paths of an interferometer, with the arms named.

````markdown
```interferometer type=michelson arm="4 km" title="Michelson, as in a gravitational-wave detector"
```
````

```interferometer type=michelson arm="4 km" title="Michelson, as in a gravitational-wave detector"
```

## `interferometer`: Fabry-Pérot

````markdown
```interferometer type=fabry-perot title="Fabry-Pérot cavity"
```
````

```interferometer type=fabry-perot title="Fabry-Pérot cavity"
```

## `spacetime`: light cone

World lines at fractions of the speed of light, and events inside and outside the cone.

````markdown
```spacetime mode=lightcone
worldline: At rest | 0 | navy
worldline: Half light speed | 0.5 | blue
worldline: 0.9 c, the other way | -0.9 | amber
event: 1.5 | 0.6 | Outside the cone: nothing here can reach it
event: 0.3 | 1.2 | Inside: in the future of the origin
```
````

```spacetime mode=lightcone
worldline: At rest | 0 | navy
worldline: Half light speed | 0.5 | blue
worldline: 0.9 c, the other way | -0.9 | amber
event: 1.5 | 0.6 | Outside the cone: nothing here can reach it
event: 0.3 | 1.2 | Inside: in the future of the origin
```

## `spacetime`: gravity wells

Bodies as potential wells side by side, on a log scale.

````markdown
```spacetime mode=well scale=log
Earth | 1 | blue
Jupiter | 318 | brown
Sun | 333000 | amber
Neutron star | 466000 | purple
```
````

```spacetime mode=well scale=log
Earth | 1 | blue
Jupiter | 318 | brown
Sun | 333000 | amber
Neutron star | 466000 | purple
```

## `spacetime`: Penrose diagram

A conformal diagram of all of spacetime, here with a black hole's horizon and singularity.

````markdown
```spacetime mode=penrose blackhole=yes
```
````

```spacetime mode=penrose blackhole=yes
```

## `energy-levels`

Energy levels and the jumps between them, each in the colour of its light.

````markdown
```energy-levels
level: n=1 | -13.6
level: n=2 | -3.4
level: n=3 | -1.51
level: n=4 | -0.85
jump: n=3 | n=2 | Hα
jump: n=4 | n=2 | Hβ
jump: n=1 | n=3 | Lyman β, absorbed
jump: n=2 | n=1 | Lyman α, emitted
```
````

```energy-levels
level: n=1 | -13.6
level: n=2 | -3.4
level: n=3 | -1.51
level: n=4 | -0.85
jump: n=3 | n=2 | Hα
jump: n=4 | n=2 | Hβ
jump: n=1 | n=3 | Lyman β, absorbed
jump: n=2 | n=1 | Lyman α, emitted
```

## `feynman`: s-channel

A Feynman diagram from a preset topology, each slot named with its particle and, optionally, its line kind.

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

## `feynman`: t-channel

````markdown
```feynman topology=t-channel
in1: e⁻
in2: e⁻
mid: γ
out1: e⁻
out2: e⁻
```
````

```feynman topology=t-channel
in1: e⁻
in2: e⁻
mid: γ
out1: e⁻
out2: e⁻
```

## `feynman`: u-channel

````markdown
```feynman topology=u-channel
in1: e⁻
in2: e⁻
mid: γ
out1: e⁻
out2: e⁻
```
````

```feynman topology=u-channel
in1: e⁻
in2: e⁻
mid: γ
out1: e⁻
out2: e⁻
```

## `feynman`: decay

````markdown
```feynman topology=decay
in1: H
out1: b
out2: b̄
```
````

```feynman topology=decay
in1: H
out1: b
out2: b̄
```

## `feynman`: beta decay

````markdown
```feynman topology=beta-decay
in1: d
out1: u
mid: W⁻
out2: e⁻
out3: ν̄ₑ
```
````

```feynman topology=beta-decay
in1: d
out1: u
mid: W⁻
out2: e⁻
out3: ν̄ₑ
```

## `feynman`: Compton scattering

````markdown
```feynman topology=compton
in1: e⁻
in2: γ
mid: e⁻
out1: e⁻
out2: γ
```
````

```feynman topology=compton
in1: e⁻
in2: γ
mid: e⁻
out1: e⁻
out2: γ
```

## `feynman`: annihilation

````markdown
```feynman topology=annihilation
in1: e⁻
in2: e⁺
mid: e⁻
out1: γ
out2: γ
```
````

```feynman topology=annihilation
in1: e⁻
in2: e⁺
mid: e⁻
out1: γ
out2: γ
```

## `feynman`: loop

````markdown
```feynman topology=loop
in1: γ
mid: e⁻ e⁺ loop
out1: γ
```
````

```feynman topology=loop
in1: γ
mid: e⁻ e⁺ loop
out1: γ
```

## `feynman`: penguin

````markdown
```feynman topology=penguin
in1: b
mid: t
out1: s
loop1: W⁻
loop2: W⁻
out2: g | gluon
```
````

```feynman topology=penguin
in1: b
mid: t
out1: s
loop1: W⁻
loop2: W⁻
out2: g | gluon
```

## `feynman`: box

````markdown
```feynman topology=box
in1: s
in2: d̄
top: W
bottom: W
left: u
right: u
out1: d
out2: s̄
```
````

```feynman topology=box
in1: s
in2: d̄
top: W
bottom: W
left: u
right: u
out1: d
out2: s̄
```

## `standard-model`

The 17 particles of the Standard Model with their mass, charge and spin, some highlighted.

````markdown
```standard-model highlight=t,H,W,Z
```
````

```standard-model highlight=t,H,W,Z
```

## `elements`

Tiles from the periodic table, coloured by category.

````markdown
```elements cols=8
H Li C N O Na Mg Al Si S Cl Ca Fe Cu Zn Ag Sn Au Pb U
```
````

```elements cols=8
H Li C N O Na Mg Al Si S Cl Ca Fe Cu Zn Ag Sn Au Pb U
```

## `nuclide-chart`

Nuclides by protons and neutrons, coloured by how they decay, with the magic numbers, the valley of stability and a reaction path.

````markdown
```nuclide-chart magic=yes valley=yes
1 | 0 | ¹H | stable
1 | 1 | ²H | stable
1 | 2 | ³H | beta-
2 | 1 | ³He | stable
2 | 2 | ⁴He | stable
3 | 3 | ⁶Li | stable
3 | 4 | ⁷Li | stable
4 | 3 | ⁷Be | beta+
4 | 5 | ⁹Be | stable
5 | 5 | ¹⁰B | stable
5 | 6 | ¹¹B | stable
6 | 5 | ¹¹C | beta+
6 | 6 | ¹²C | stable
6 | 7 | ¹³C | stable
6 | 8 | ¹⁴C | beta-
7 | 7 | ¹⁴N | stable
7 | 8 | ¹⁵N | stable
8 | 8 | ¹⁶O | stable
path: 6,6 7,6 6,7 7,7 8,7 7,8 6,6 | CNO cycle | red
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
4 | 3 | ⁷Be | beta+
4 | 5 | ⁹Be | stable
5 | 5 | ¹⁰B | stable
5 | 6 | ¹¹B | stable
6 | 5 | ¹¹C | beta+
6 | 6 | ¹²C | stable
6 | 7 | ¹³C | stable
6 | 8 | ¹⁴C | beta-
7 | 7 | ¹⁴N | stable
7 | 8 | ¹⁵N | stable
8 | 8 | ¹⁶O | stable
path: 6,6 7,6 6,7 7,7 8,7 7,8 6,6 | CNO cycle | red
```

## `chess`

A position from its Forsyth-Edwards Notation (FEN), with squares highlighted and moves drawn as arrows.

````markdown
```chess
fen: r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
highlight: c4 f7
arrow: c4 f7 | #a3322b
arrow: f3 g5 | #2f5d9c
arrow: f8 c5 | #2e7d32
```
````

```chess
fen: r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
highlight: c4 f7
arrow: c4 f7 | #a3322b
arrow: f3 g5 | #2f5d9c
arrow: f8 c5 | #2e7d32
```

## `music`

Music in ABC notation (a text format for tunes), drawn as a score. `abc` is the same fence.

````markdown
```music
X:1
T:Scarborough Fair
M:3/4
L:1/4
K:Dm
D2 D | A2 A | E3/2 F/ E | D3 |
z A c | d2 c | A B G | A3 |
z2 d | d2 d | c2 A | A G F |
E D C | D3 | D3 |]
```
````

```music
X:1
T:Scarborough Fair
M:3/4
L:1/4
K:Dm
D2 D | A2 A | E3/2 F/ E | D3 |
z A c | d2 c | A B G | A3 |
z2 d | d2 d | c2 A | A G F |
E D C | D3 | D3 |]
```

## `molecule`

Molecules from their Simplified Molecular Input Line Entry System (SMILES) strings, in a grid.

````markdown
```molecule
Caffeine | CN1C=NC2=C1C(=O)N(C(=O)N2C)C
Aspirin | CC(=O)OC1=CC=CC=C1C(=O)O
Paracetamol | CC(=O)NC1=CC=C(C=C1)O
Ibuprofen | CC(C)CC1=CC=C(C=C1)C(C)C(=O)O
```
````

```molecule
Caffeine | CN1C=NC2=C1C(=O)N(C(=O)N2C)C
Aspirin | CC(=O)OC1=CC=CC=C1C(=O)O
Paracetamol | CC(=O)NC1=CC=C(C=C1)O
Ibuprofen | CC(C)CC1=CC=C(C=C1)C(C)C(=O)O
```

## `phylogeny`

A tree in Newick form, with branch lengths.

````markdown
```phylogeny
(((Human:0.006,Chimpanzee:0.007):0.002,Gorilla:0.009):0.009,(Orangutan:0.018,(Gibbon:0.02,Siamang:0.021):0.004):0.003);
```
````

```phylogeny
(((Human:0.006,Chimpanzee:0.007):0.002,Gorilla:0.009):0.009,(Orangutan:0.018,(Gibbon:0.02,Siamang:0.021):0.004):0.003);
```

## `ternary`

Points of three parts on a ternary plot.

````markdown
```ternary
axes: Sand | Silt | Clay
Loam | 40 | 40 | 20
Clay loam | 30 | 35 | 35
Sandy loam | 65 | 25 | 10
Silty clay | 7 | 48 | 45
Sand | 90 | 5 | 5
Silt loam | 20 | 65 | 15
```
````

```ternary
axes: Sand | Silt | Clay
Loam | 40 | 40 | 20
Clay loam | 30 | 35 | 35
Sandy loam | 65 | 25 | 10
Silty clay | 7 | 48 | 45
Sand | 90 | 5 | 5
Silt loam | 20 | 65 | 15
```

## `seq-logo`

A sequence logo from aligned sequences.

````markdown
```seq-logo
TATAAAAG
TATAAATG
TATTAAAG
TATAAAAC
CATAAAAG
TATAAGAG
TATATAAG
TACAAAAG
```
````

```seq-logo
TATAAAAG
TATAAATG
TATTAAAG
TATAAAAC
CATAAAAG
TATAAGAG
TATATAAG
TACAAAAG
```

## `upset`

An UpSet plot: how many items are in exactly each combination of sets.

````markdown
```upset
Condensation | 31
Low battery | 18
Cracked case | 14
Condensation, Low battery | 12
Cracked case, Condensation | 7
Low battery, Weak signal | 6
Weak signal | 9
Condensation, Low battery, Weak signal | 3
```
````

```upset
Condensation | 31
Low battery | 18
Cracked case | 14
Condensation, Low battery | 12
Cracked case, Condensation | 7
Low battery, Weak signal | 6
Weak signal | 9
Condensation, Low battery, Weak signal | 3
```

## `smith`

Impedances on a Smith chart.

````markdown
```smith
z0: 50
Antenna at 830 MHz | 32+18j
After the match | 49+2j
Open feed | 200-80j
Short stub | 5+40j
```
````

```smith
z0: 50
Antenna at 830 MHz | 32+18j
After the match | 49+2j
Open feed | 200-80j
Short stub | 5+40j
```

## `plasmid`

A circular map of a plasmid's features.

````markdown
```plasmid
size: 5400
ori | 100..780 | + | grey
AmpR | 950..1810 | - | #b4540a
Promoter | 2100..2350 | + | #0f7b7b
Cas9 | 2400..4600 | + | #a3322b
NLS | 4600..4700 | + | #2e7d32
Terminator | 4800..4950 | + | #555555
```
````

```plasmid
size: 5400
ori | 100..780 | + | grey
AmpR | 950..1810 | - | #b4540a
Promoter | 2100..2350 | + | #0f7b7b
Cas9 | 2400..4600 | + | #a3322b
NLS | 4600..4700 | + | #2e7d32
Terminator | 4800..4950 | + | #555555
```

## `gene-locus`

Genes along a locus, on their strands.

````markdown
```gene-locus
size: 5200
lacI | 1..1080 | + | #6b46c1
Promoter | 1150..1350 | + | #0f7b7b
lacZ | 1400..4470 | + | #3b6fb6
lacY | 4520..5100 | + | #2e7d32
```
````

```gene-locus
size: 5200
lacI | 1..1080 | + | #6b46c1
Promoter | 1150..1350 | + | #0f7b7b
lacZ | 1400..4470 | + | #3b6fb6
lacY | 4520..5100 | + | #2e7d32
```

## `cie`

Colour gamuts and points on the chromaticity diagram of the International Commission on Illumination (CIE), from 1931.

````markdown
```cie
gamut: sRGB
gamut: Display P3
gamut: ITU-R BT.2020
D65 white | 0.3127 | 0.3290
Status LED, green | 0.17 | 0.70
Status LED, amber | 0.57 | 0.42
```
````

```cie
gamut: sRGB
gamut: Display P3
gamut: ITU-R BT.2020
D65 white | 0.3127 | 0.3290
Status LED, green | 0.17 | 0.70
Status LED, amber | 0.57 | 0.42
```

## `sun-path`

The sun's path across the sky for a place, on chosen days.

````markdown
```sun-path
lat: 53.8
lon: -1.55
timezone: Europe/London
day: Midsummer | 2026-06-21
day: Equinox | 2026-03-20
day: Midwinter | 2026-12-21
```
````

```sun-path
lat: 53.8
lon: -1.55
timezone: Europe/London
day: Midsummer | 2026-06-21
day: Equinox | 2026-03-20
day: Midwinter | 2026-12-21
```

## `thermo-cycle`

A thermodynamic cycle on the temperature-entropy diagram, with the saturation dome.

````markdown
```thermo-cycle
fluid: Water
state: 1 | 10 | 40
state: 2 | 8000 | 42
state: 3 Turbine in | 8000 | 500
state: 4 Condenser in | 10 | 46
```
````

```thermo-cycle
fluid: Water
state: 1 | 10 | 40
state: 2 | 8000 | 42
state: 3 Turbine in | 8000 | 500
state: 4 Condenser in | 10 | 46
```
