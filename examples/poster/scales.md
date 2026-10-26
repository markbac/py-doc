---
title: Smart prepayment, in numbers
subtitle: Credit, the grid and the light that carries the readings
byline: py-doc example poster for the scale blocks
orientation: landscape
paper: a1
width: 1800
columns: 3
footer:
  left: Scale blocks
  right: docs/guide/12_posters.md, Poster blocks
---

## Introduction {.abstract}

Prepayment counts credit down to a cut-off, borrows emergency credit, and keeps the supply on in friendly hours. The grid it hangs on runs inside a narrow frequency band. Each section shows one of those with a scale block.

## 1. Credit: counting down to cut-off {.wide}

```threshold title="Smart prepayment credit lifecycle"
span: Normal credit | £20.00 to £2.00 | Everyday use, supply on | green | 4
pin: £2.00 Low credit alert, emergency credit can be armed | amber
span: Low credit | £2.00 to £0.00 | The customer can arm emergency credit | amber | 2
pin: £0.00 Credit exhausted | red
span: Emergency credit | A £10.00 pool | Borrowed, the supply stays on | purple | 3
pin: -£10.00 Hard cut-off, the valve closes | red
span: Disconnected | A top-up repays the £10.00 first | grey | 2
```

## 2. Top-up: where £25.00 goes

```chart type=waterfall title="A £25.00 top-up after emergency credit" unit="£"
Top-up | +25.00 | blue | By app or at a shop
Repay emergency | -10.00 | purple | Re-arms the pool
Friendly hours | -3.50 | red | Overnight use
Arrears | -2.50 | amber | 10 % recovery
Standing charge | -0.60 | grey | One day
Credit | =8.40 | green | On the meter
```

## 3. Pools: what is left

```buckets unit="£"
Emergency credit | 10 | 10 | amber
Normal credit | 8.4 | 30 | green | 2 Low credit
Debt | 6 | 50 | red | 25 Recovery limit
```

## 4. Friendly hours: when the supply stays on

```dial24 title="A weekday"
18:00 | 09:00 | Friendly hours, no cut-off | green
00:00 | 05:00 | Off-peak tariff | blue
16:00 | 19:00 | Peak demand | red
```

## 5. The grid: inside its band {.wide}

```threshold title="Grid frequency operating envelope" target="50.00 Hz nominal"
span: Below 48.8 Hz | Emergency | Demand disconnection | red | 2
pin: 48.8 Hz Automatic load shedding | red
span: 49.5 to 49.8 Hz | Containment | Fast battery response | amber | 2
pin: 49.8 Hz | green
span: 49.8 to 50.2 Hz | Balanced | The normal operating band | green | 4
pin: 50.2 Hz | green
span: Above 50.5 Hz | Over-speed | Generators curtail | amber | 2
```

## 6. Frequency now

```gauge value=49.93 min=48.5 max=51.5 unit=" Hz" label="Grid frequency"
48.5 | 49.5 | red
49.5 | 49.8 | amber
49.8 | 50.2 | green
50.2 | 50.5 | amber
50.5 | 51.5 | red
```

## 7. Homes: their energy rating

```rating current=D potential=B
A | 92+
B | 81-91
C | 69-80
D | 55-68
E | 39-54
F | 21-38
G | 1-20
```

## 8. Heat: what happens when

```gradient-scale from=0 to=200 unit=" °C" colours=blue,green,amber,red
65 | Eggs set
100 | Water boils
150 | Browning starts
170 | Sugar caramelises
```

## 9. Latency: orders of magnitude {.wide}

```logscale unit=" s"
1e-9 | Cache read
1e-7 | Memory read
1.5e-4 | Flash read
1e-2 | Disk seek
1.5e-1 | Across an ocean
2 | NB-IoT wake and send
```

## 10. Light: what the eye sees

```spectrum mode=absorption title="The Sun's dark lines"
656.3 | Hα
589 | Na D
527 | Fe
486.1 | Hβ
430.8 | G band
```

## 11. Radio: the 2.4 GHz band

```spectrum mode=channels title="Wi-Fi and BLE advertising channels" from=2400 to=2485
Wi-Fi 1 | 2412 | 20 | blue
Wi-Fi 6 | 2437 | 20 | blue
Wi-Fi 11 | 2462 | 20 | blue
BLE 37 | 2402 | 2 | amber
BLE 38 | 2426 | 2 | amber
BLE 39 | 2480 | 2 | amber
```

## 12. Stars: their colours

```spectrum mode=stellar
```

## 13. All of it: the electromagnetic spectrum {.wide}

```spectrum mode=em
5e-7 | Visible light
1.2e-1 | Wi-Fi
3.4e-1 | NB-IoT (868 MHz)
```

## In short {.summary}

A scale block draws numbers along a line, so a reader sees where a value sits and what happens next.
