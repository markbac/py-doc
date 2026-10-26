---
title: Plots without the JSON
subtitle: Statistical, quality and scientific charts in a few lines each
byline: py-doc example poster for the plot presets
orientation: landscape
paper: a1
width: 1800
columns: 4
footer:
  left: Plot presets
  right: docs/guide/12_posters.md, Plots
---

## Introduction {.abstract}

Each section is one `plot` preset. py-doc writes the Vega-Lite (or Vega) for it and the tool container draws it, in the poster's theme. For anything a preset cannot say, write a `vega-lite` fence.

## 1. Returns: Pareto

```plot type=pareto title="Why nodes came back"
Condensation | 31
Self-discharge | 23
Cracked enclosure | 18
Will not join | 9
Other | 8
```

## 2. Sensor drift: control chart

```plot type=spc title="Daily calibration offset" ytitle="°C"
1 | 0.02
2 | 0.05
3 | -0.01
4 | 0.03
5 | 0.00
6 | 0.04
7 | 0.21
8 | 0.01
9 | -0.02
10 | 0.03
```

## 3. Join time: boxplot

```plot type=boxplot ytitle="Seconds" points=yes
2.0 | 9 11 12 10 14 13 11 15 10 12
2.1 | 3 4 4 5 3 6 4 4 5 3
```

## 4. Battery life: violin

```plot type=violin ytitle="Years"
Office | 4.8 5.1 5.3 5.0 5.6 4.9 5.2 5.4 5.1 5.0
Cold store | 3.1 3.6 3.9 3.3 4.1 3.5 3.8 3.4 3.7 3.2
```

## 5. Radios: scatter

```plot type=scatter xlog=yes xtitle="Range (km)" ytitle="Battery (years)" labels=yes
NB-IoT | 15 | 10 | 8 | Cellular
LTE-M | 11 | 7 | 8 | Cellular
LoRaWAN | 12 | 9 | 6 | Unlicensed
BLE | 0.05 | 3 | 4 | Unlicensed
Wi-Fi | 0.1 | 0.5 | 4 | Unlicensed
```

## 6. Distribution: the normal curve

```plot type=function preset=normal title="Within one, two and three sigma"
```

## 7. Response: a function

```plot type=function from=0 to=10 xtitle="Time (s)" ytitle="Output"
curve: Step response | 1 - exp(-0.6 * x) * cos(2 * x)
rule: 2.1 | Settled
```

## 8. Risk: the matrix

```plot type=heatmap preset=risk
4 | 5 | R1
2 | 4 | R2
3 | 2 | R3
```

## 9. Demand: a heatmap

```plot type=heatmap unit="GW"
| Mon | Tue | Wed | Thu | Fri
Morning | 31 | 32 | 32 | 31 | 30
Evening | 38 | 39 | 37 | 38 | 35
Night | 22 | 23 | 22 | 22 | 24
```

## 10. Wind: a rose

```plot type=polar
N | 12
NE | 8
E | 5
SE | 4
S | 9
SW | 18
W | 22
NW | 15
```

## 11. Before and after: slope

```plot type=slope ytitle="Messages a day"
| 2.0 | 2.1
Office | 1440 | 610
Warehouse | 1440 | 980
Cold store | 1440 | 1210
```

## 12. Trade-offs: parallel axes

```plot type=parallel
| Range km | Battery yrs | Bitrate kbps | Cost £
NB-IoT | 15 | 10 | 60 | 8
LTE-M | 11 | 7 | 1000 | 10
LoRaWAN | 12 | 9 | 5 | 6
```

## 13. Demand: a forecast fan

```plot type=fan ytitle="TWh"
history: 2022 | 280
history: 2023 | 285
history: 2024 | 292
forecast: 2025 | 298 | 294 | 302 | 290 | 306 | 285 | 311
forecast: 2026 | 305 | 298 | 312 | 291 | 319 | 283 | 327
```

## 14. Flash: a sunburst

```plot type=sunburst
Crypto / X.509 | 52
Crypto / ECDSA | 38
Crypto / AES-GCM | 28
Network / CoAP and DTLS | 44
Network / Modem | 26
RTOS / Kernel | 18
RTOS / Drivers | 22
App | 28
```

## 15. Flash: an icicle

```plot type=icicle
Crypto / X.509 | 52
Crypto / ECDSA | 38
Network / CoAP and DTLS | 44
Network / Modem | 26
App | 28
```

## 16. Flash: circles

```plot type=pack
Crypto / X.509 | 52
Crypto / ECDSA | 38
Network / CoAP and DTLS | 44
Network / Modem | 26
App | 28
```

## In short {.summary}

A preset says what the chart shows; py-doc writes the Vega for it.
