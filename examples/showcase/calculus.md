---
title: Differentiation and integration
subtitle: "Two halves of calculus: how fast things change, and how much they add up to"
byline: Euler Academy mathematics department, Year 12
orientation: landscape
paper: a1
columns: 3
---

## Key figures {.stats style=tiles colour=brand}

| Value | Label |
|---|---|
| dy/dx | The gradient: a rate of change |
| ∫ y dx | The area: an accumulation |
| 1666 | Newton's "fluxions" |
| 1684 | Leibniz publishes d and ∫ |

## Introduction {.abstract style=quote}

Differentiation finds the gradient of a curve at a point: how fast one quantity changes with another. Integration finds the area under a curve: how much a changing quantity adds up to. The fundamental theorem of calculus says each undoes the other.

## 1. The derivative: a gradient at a point

```equation
title: From first principles
f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}
f'(x) | The gradient of f at x |
h | A small step along the curve |
The gradient of a chord, as the chord shrinks to a point.
```

```plot type=function from=-1 to=3 xtitle="x" ytitle="y" title="y = x² and its tangent at x = 1"
curve: y = x² | x * x
curve: Tangent, gradient 2 | 2 * x - 1
curve: Gradient function, y' = 2x | 2 * x
rule: 1 | x = 1
```

The tangent at $x = 1$ touches the curve with gradient $2$, the value of $y' = 2x$ there.

Leibniz wrote the gradient as $\frac{dy}{dx}$: a tiny change in $y$ over a tiny change in $x$. Newton wrote $\dot{y}$ and thought of it as a speed. Both mean the limit above, and A-level uses Leibniz's notation because the chain rule then reads like cancelling fractions.

## 2. The rules: differentiating quickly

| Function $f(x)$ | Derivative $f'(x)$ |
|---|---|
| $x^n$ | $n x^{n-1}$ |
| $e^{x}$ | $e^{x}$ |
| $\ln x$ | $\frac{1}{x}$ |
| $\sin x$ | $\cos x$ |
| $\cos x$ | $-\sin x$ |

```equation cols=1
title: The chain rule
\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx}
u | The inner function of x |
For a function of a function, such as $\sin(x^2)$, whose derivative is $2x \cos(x^2)$.
---
title: The product rule
\frac{d}{dx}(uv) = u\frac{dv}{dx} + v\frac{du}{dx}
```

## 3. Stationary points: where the gradient is zero

```steps
Differentiate | Find $f'(x)$
Solve f'(x) = 0 | The $x$ of each stationary point
Differentiate again | Find $f''(x)$
Classify | $f'' > 0$: a minimum. $f'' < 0$: a maximum | brand
```

```plot type=function from=-2.5 to=2.5 xtitle="x" ytitle="y" title="y = x³ − 3x: a maximum at x = −1, a minimum at x = 1"
curve: y = x³ − 3x | x * x * x - 3 * x
curve: y' = 3x² − 3 | 3 * x * x - 3
rule: -1 | Maximum
rule: 1 | Minimum
```

## 4. Motion: round the cycle

```cycle
Displacement s | Where it is | brand
Velocity v | ds/dt | second
Acceleration a | dv/dt | spark
```

Differentiate to go round the cycle; integrate to come back.

## 5. The integral: an area under a curve

```plot type=function from=0 to=3 xtitle="x" ytitle="y" title="The area under y = x² from 1 to 2 is 7/3"
curve: y = x² | x * x
area: 1 | 2 | Area = 7/3
```

```equation
title: The fundamental theorem of calculus
\int_a^b f(x)\,dx = F(b) - F(a), \quad F'(x) = f(x)
F | An antiderivative of f |
a, b | The limits of the area |
So $\int_1^2 x^2\,dx = \left[\frac{x^3}{3}\right]_1^2 = \frac{8}{3} - \frac{1}{3} = \frac{7}{3}$.
```

## 6. Integrating: the rules run backwards

| $f(x)$ | $\int f(x)\,dx$ |
|---|---|
| $x^n$, $n \neq -1$ | $\frac{x^{n+1}}{n+1} + c$ |
| $\frac{1}{x}$ | $\ln \lvert x \rvert + c$ |
| $e^{kx}$ | $\frac{1}{k}e^{kx} + c$ |
| $\cos kx$ | $\frac{1}{k}\sin kx + c$ |

> [!TIP]
> Never forget $+\,c$: every function has infinitely many antiderivatives, one for each constant.

## 7. Two sides of one idea

```compare
| Differentiation | Integration
Finds | A gradient | An area
Asks | How fast is it changing? | How much has built up?
Speed and distance | Distance gives speed | Speed gives distance
Notation | $\frac{dy}{dx}$, $f'(x)$ | $\int f(x)\,dx$
```

## In short {.summary style=line}

Differentiation and integration are inverses, and between them they describe anything that changes.

### Gradient

The derivative is the limit of a chord's gradient.

### Area

The integral is the limit of a sum of thin strips.

### One theorem

Integrating a derivative gives back the function.
