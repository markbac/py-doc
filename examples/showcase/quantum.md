---
title: The quantum world
subtitle: Waves of probability, energy in steps, and the uncertainty at the heart of nature
byline: Quanta Institute public lecture series
orientation: portrait
paper: a1
columns: 3
---

## Key figures {.stats style=plain}

| Value | Label |
|---|---|
| 6.626 × 10⁻³⁴ J s | Planck's constant, h |
| 1900 | Planck explains black-body light |
| 1925–27 | Quantum mechanics is written |
| 10⁻¹⁰ m | The size of an atom |

## Introduction {.abstract style=outline}

At the scale of atoms, energy comes in steps, light arrives in packets, and a particle has no definite place until it is measured. Quantum mechanics describes this world with a wave function, $\psi$, whose square gives the probability of finding the particle. It is the most precisely tested theory in science.

## 1. The equation: how a wave function changes

```equation cols=1
title: The time-independent Schrödinger equation
-\frac{\hbar^2}{2m}\frac{d^2\psi}{dx^2} + V(x)\,\psi = E\,\psi
\hbar | Planck's constant over 2π | J s
m | Mass of the particle | kg
V(x) | Potential energy at x | J
E | The particle's energy | J
\psi | The wave function | m^{-1/2}
---
title: Heisenberg's uncertainty principle
\Delta x \, \Delta p \geq \frac{\hbar}{2}
\Delta x | Uncertainty in position | m
\Delta p | Uncertainty in momentum | kg m/s
The better the place is known, the less the momentum can be, and the other way round.
```

## 2. A particle in a box: energy in steps

A particle trapped between two walls can only have wave functions that fit the box: a whole number of half-waves. So its energy can only take certain values, $E_n = n^2 h^2 / 8 m L^2$.

```plot type=function from=0 to=1 xtitle="Position in the box, x / L" ytitle="Probability density" title="Where the particle may be found"
curve: n = 1 | 2 * pow(sin(PI * x), 2)
curve: n = 2 | 2 * pow(sin(2 * PI * x), 2)
curve: n = 3 | 2 * pow(sin(3 * PI * x), 2)
```

> [!NOTE]
> Make the walls finite and the wave leaks through them: a particle can be found on the far side of a barrier it could never climb. This tunnelling powers the Sun and every flash memory chip.

## 3. Hydrogen: the same steps in an atom

```energy-levels
level: n=1 | -13.6
level: n=2 | -3.4
level: n=3 | -1.51
level: n=4 | -0.85
jump: n=1 | n=3 | UV in
jump: n=3 | n=2 | Hα
jump: n=4 | n=2 | Hβ
```

Hydrogen's levels: an electron falling from level 3 to level 2 gives out the red light of a nebula.

## 4. Light: a wave and a particle

```compare
| As a wave | As a particle
Shows | Interference and diffraction | The photoelectric effect
Carries | Energy spread over the wave | Packets of E = hf
Seen in | The double-slit pattern | Single clicks of a detector
Explained by | Young, 1801 | Einstein, 1905
```

## 5. Interference: light against itself

```interferometer type=michelson arm="12 cm"
```

Split a beam, send it two ways and bring it back: the bright and dark fringes show light interfering with itself, even one photon at a time.

## 6. History: from a fix to a theory

```timeline vertical
1900 | Planck | Energy comes in quanta, E = hf | brand
1905 | Einstein | Light as photons | second
1913 | Bohr | Electrons on fixed orbits | spark
1924 | de Broglie | Matter has a wavelength | brand
1925 | Heisenberg | Matrix mechanics | second
1926 | Schrödinger | The wave equation | spark
1927 | Heisenberg | The uncertainty principle | brand
1964 | Bell | Entanglement can be tested | second
```

## 7. The particles: what everything is made of

```standard-model highlight=e,γ
```

Twelve matter particles and the bosons that carry the forces between them. Every atom is made of up and down quarks, held together by gluons, with electrons around them.

## 8. Words: a short glossary {.wide}

```glossary cols=3
Quantum | The smallest amount of something, such as one photon of light
Wave function | ψ: its square is the probability of finding the particle at each place
Superposition | A state that is a mix of several, until it is measured
Entanglement | Two particles sharing one state, however far apart
Tunnelling | Passing through a barrier the particle has too little energy to climb
Photon | A quantum of light, with energy E = hf
```

## In short {.summary style=line}

Nature is grainy, and it is uncertain, but it is not random: the wave function follows an exact equation.

### Energy in steps

Atoms only absorb and give out the light that fits their levels.

### Waves and particles

Light and electrons are both, depending on how we look.

### Limits to knowing

Position and momentum cannot both be sharp.
