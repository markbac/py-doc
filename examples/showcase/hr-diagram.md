---
title: The Hertzsprung–Russell diagram
subtitle: One chart of brightness against temperature tells a star's whole life
byline: Northern Observatory, Thursday night lectures
orientation: landscape
paper: a1
columns: 3
---

## Key figures {.stats}

| Value | Label |
|---|---|
| 90 % | Of stars are on the main sequence |
| 3,000–40,000 K | Surface temperatures of stars |
| 10⁻⁴ – 10⁶ | Luminosity, in Suns |
| 1911–13 | Hertzsprung and Russell draw it |

## Introduction {.abstract}

Plot a star's luminosity against its surface temperature, hottest on the left, and the stars do not scatter: they fall on a few bands. The band a star is on, and where on it, tells its mass, its age and its fate. Here are the stars you can see tonight, on the diagram that made sense of them.

## 1. The diagram: tonight's stars {.wide}

```plot type=scatter xlog=yes ylog=yes xinvert=yes labels=yes width=2500 height=720 xtitle="Surface temperature (K), hottest on the left" ytitle="Luminosity (Suns)" title="Bright and nearby stars"
Rigel | 12100 | 120000 | 9 | Supergiants
Betelgeuse | 3600 | 120000 | 9 | Supergiants
Deneb | 8500 | 200000 | 9 | Supergiants
Antares | 3500 | 75000 | 9 | Supergiants
Aldebaran | 3900 | 440 | 6 | Giants
Arcturus | 4300 | 170 | 6 | Giants
Capella | 4970 | 79 | 6 | Giants
Pollux | 4600 | 33 | 6 | Giants
Spica | 22400 | 20500 | 4 | Main sequence
Regulus | 12500 | 290 | 4 | Main sequence
Vega | 9600 | 40 | 4 | Main sequence
Sirius A | 9940 | 25 | 4 | Main sequence
Altair | 7700 | 10.6 | 4 | Main sequence
Procyon A | 6530 | 6.9 | 4 | Main sequence
Sun | 5772 | 1 | 4 | Main sequence
Alpha Cen B | 5260 | 0.5 | 4 | Main sequence
61 Cygni A | 4400 | 0.15 | 4 | Main sequence
Barnard's Star | 3130 | 0.0035 | 4 | Main sequence
Proxima Cen | 3040 | 0.0017 | 4 | Main sequence
Sirius B | 25000 | 0.056 | 3 | White dwarfs
Procyon B | 7740 | 0.00049 | 3 | White dwarfs
40 Eridani B | 16500 | 0.013 | 3 | White dwarfs
```

## 2. Life: a star moves across the diagram

```flow
[Nebula|grey] -collapse-> [Main sequence|brand] -hydrogen gone-> [Red giant|amber] -outer layers drift off-> [White dwarf|second]
[Red giant|amber] -above 8 Suns-> [Supergiant|red] -core collapses-> [Supernova|spark]
[Supernova|spark] -> [Neutron star or black hole]
```

## 3. Inside a star like the Sun

```cutaway type=sphere unit=" R☉"
Core | 0.25 | Hydrogen fuses to helium at 15 million K | spark
Radiative zone | 0.7 | Light takes 170,000 years to cross | amber
Convective zone | 1 | Hot plasma rises and sinks | red
```

On the main sequence, the core's fusion pushes out as hard as gravity pulls in. When the hydrogen runs out, the balance fails and the star leaves the sequence.

## 4. Sizes: the Sun among the stars

```sizes shape=circle nested=yes unit=" R☉"
Betelgeuse | 760 | Red supergiant | red
Aldebaran | 45 | Red giant | amber
Sirius A | 1.7 | Main sequence | blue
Sun | 1 | Main sequence | spark
```

Betelgeuse placed at the Sun would swallow the orbit of Jupiter; Sirius B, a white dwarf, is the size of the Earth.

## 5. What stars make

```elements cols=8
H He C N O Ne Si Fe
```

Hydrogen and helium come from the Big Bang. Stars fuse them into carbon, oxygen and the rest, up to iron; heavier elements come from supernovae and colliding neutron stars.

## 6. Colour is temperature

```spectrum mode=stellar
```

A star's colour gives its temperature: blue O stars above 30,000 K, our yellow Sun at 5,800 K, red M dwarfs below 3,500 K. The letters run O B A F G K M.

```equation
title: Stefan–Boltzmann: why giants are bright
L = 4 \pi R^2 \sigma T^4
L | Luminosity | W
R | Radius of the star | m
\sigma | Stefan–Boltzmann constant | W m^{-2} K^{-4}
T | Surface temperature | K
A cool star can only be very bright by being very large.
```

## 7. Distance: how far their light has come

```logscale from=1e-5 to=1e4 unit=" light years"
0.0000016 | Sun: 8 minutes | spark
4.2 | Proxima Centauri | red
8.6 | Sirius | blue
25 | Vega | second
640 | Betelgeuse | red
2600 | Deneb | brand
```

The light of Deneb left it before the pyramids were built: the diagram shows each star as it was when its light set out.

## In short {.summary}

Where a star sits on the diagram says what it is now, and where it is going.

### The main sequence

Stars burning hydrogen, from hot blue giants to cool red dwarfs.

### Giants and supergiants

Old stars, cool but huge, in the top right.

### White dwarfs

The hot, faint embers of stars like the Sun, bottom left.
