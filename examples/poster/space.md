---
title: From orbits to quarks
subtitle: Space, light, atoms and particles, each in its own diagram
byline: py-doc example poster for the space and particle blocks
orientation: landscape
paper: a1
width: 1800
columns: 3
footer:
  left: Space and particle blocks
  right: docs/guide/12_posters.md, Poster blocks
---

## Introduction {.abstract}

Each section is one block for physics posters. There are orbits with a transfer to Mars, two telescopes, an interferometer and spacetime drawn three ways. Then come the energy levels of hydrogen, Feynman diagrams, the standard model, element tiles and a corner of the chart of nuclides.

## 1. Orbits: Earth to Mars

```orbits star=Sun unit=" AU" habitable=0.95-1.67
orbit: Earth | 1 | blue
orbit: Mars | 1.52 | red | e=0.09
transfer: 1 | 1.52 | Hohmann transfer
lagrange: Earth
```

## 2. Telescopes: where the light goes

```optics type=cassegrain title="Cassegrain"
```

```optics type=newtonian title="Newtonian"
```

## 3. Gravitational waves: the interferometer

```interferometer type=michelson arm="4 km"
```

## 4. Spacetime: the light cone

```spacetime mode=lightcone
worldline: At rest | 0 | navy
worldline: Half light speed | 0.5 | blue
event: 1.5 | 0.6 | Outside the cone: nothing here can reach it
```

## 5. Gravity: how deep the well

```spacetime mode=well scale=log
Sun | 2 | amber
White dwarf | 200 | blue
Neutron star | 100000 | navy
Black hole | 10000000 | red
```

## 6. A black hole: the Penrose diagram

```spacetime mode=penrose blackhole=yes
```

## 7. Hydrogen: its energy levels

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

## 8. Scattering: e⁻ e⁺ to μ⁻ μ⁺

```feynman topology=s-channel
in1: e⁻
in2: e⁺
mid: γ
out1: μ⁻
out2: μ⁺
```

## 9. Beta decay: a neutron becomes a proton

```feynman topology=beta-decay
in1: d
out1: u
mid: W⁻
out2: e⁻
out3: ν̄ₑ
```

## 10. The particles: the standard model

```standard-model highlight=t,H
```

## 11. Stars: what they make

```elements cols=8
H He C O Si Fe Au U
```

## 12. Light nuclei: the chart of nuclides

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

## In short {.summary}

The diagram a physicist would draw on a board, drawn the same way each time.
