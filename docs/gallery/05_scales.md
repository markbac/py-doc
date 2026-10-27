# Scales, measures and proportions

Blocks that place values on a scale, show a reading against its limits, or compare sizes and amounts. Each is drawn by py-doc itself.

## `gauge`

A dial with coloured zones and its needle at the value.

````markdown
```gauge value=49.93 min=48.5 max=51.5 unit=" Hz" label="Grid frequency"
48.5 | 49.5 | red
49.5 | 49.8 | amber
49.8 | 50.2 | green
50.2 | 50.5 | amber
50.5 | 51.5 | red
```
````

```gauge value=49.93 min=48.5 max=51.5 unit=" Hz" label="Grid frequency"
48.5 | 49.5 | red
49.5 | 49.8 | amber
49.8 | 50.2 | green
50.2 | 50.5 | amber
50.5 | 51.5 | red
```

## `progress`

Bars towards a target, coloured when met, with a ceiling for values where lower is better.

````markdown
```progress unit=" nodes"
New cells for lot 24-11 | 1,240 | 3,100
Cold-store nodes with a coated sensor | 410 | 6,300
Gateways on 1.5 or later | 2,860 | 2,860
Sites signed off this quarter | 38 | 45
```
````

```progress unit=" nodes"
New cells for lot 24-11 | 1,240 | 3,100
Cold-store nodes with a coated sensor | 410 | 6,300
Gateways on 1.5 or later | 2,860 | 2,860
Sites signed off this quarter | 38 | 45
```

## `rating`

An energy-label style scale with the current and potential ratings marked.

````markdown
```rating current=D potential=B current-label="Today, 61" potential-label="With the upgrades, 84"
A | 92+
B | 81-91
C | 69-80
D | 55-68
E | 39-54
F | 21-38
G | 1-20
```
````

```rating current=D potential=B current-label="Today, 61" potential-label="With the upgrades, 84"
A | 92+
B | 81-91
C | 69-80
D | 55-68
E | 39-54
F | 21-38
G | 1-20
```

## `threshold`

Bands in proportion to their weights, with the exact points where something changes pinned between them.

````markdown
```threshold title="Smart prepayment credit"
span: Normal credit | £20.00 to £2.00 | Everyday use, supply on | green | 4
pin: £2.00 Low credit alert, emergency credit can be armed | amber
span: Low credit | £2.00 to £0.00 | The customer can arm emergency credit | amber | 2
pin: £0.00 Credit exhausted | red
span: Emergency credit | A £10.00 pool | Borrowed, the supply stays on | purple | 3
pin: -£10.00 Hard cut-off, the valve closes | red
span: Disconnected | A top-up repays the £10.00 first | grey | 2
```
````

```threshold title="Smart prepayment credit"
span: Normal credit | £20.00 to £2.00 | Everyday use, supply on | green | 4
pin: £2.00 Low credit alert, emergency credit can be armed | amber
span: Low credit | £2.00 to £0.00 | The customer can arm emergency credit | amber | 2
pin: £0.00 Credit exhausted | red
span: Emergency credit | A £10.00 pool | Borrowed, the supply stays on | purple | 3
pin: -£10.00 Hard cut-off, the valve closes | red
span: Disconnected | A top-up repays the £10.00 first | grey | 2
```

## `buckets`

Tanks filled to their share of capacity, with dashed lines at their thresholds.

````markdown
```buckets unit=" MB"
Flash log | 3.1 | 4 | blue | 3.5 Rotate
Message queue | 0.6 | 1 | amber | 0.8 Throttle
Firmware slot B | 0.9 | 1 | green
Certificates | 0.02 | 0.25 | grey
```
````

```buckets unit=" MB"
Flash log | 3.1 | 4 | blue | 3.5 Rotate
Message queue | 0.6 | 1 | amber | 0.8 Throttle
Firmware slot B | 0.9 | 1 | green
Certificates | 0.02 | 0.25 | grey
```

## `dial24`

Times of day on a 24-hour clock, a ring each.

````markdown
```dial24 title="A weekday on the cold-store site"
06:00 | 18:00 | Doors open, more readings | amber
22:00 | 05:00 | Defrost cycles | blue
00:00 | 24:00 | Compressor monitoring | green
12:00 | 13:00 | Daily report sent | red
```
````

```dial24 title="A weekday on the cold-store site"
06:00 | 18:00 | Doors open, more readings | amber
22:00 | 05:00 | Defrost cycles | blue
00:00 | 24:00 | Compressor monitoring | green
12:00 | 13:00 | Daily report sent | red
```

## `gradient-scale`

Benchmarks above and below a bar shading from colour to colour.

````markdown
```gradient-scale from=-40 to=85 unit=" °C" colours=blue,green,amber,red step=25
-40 | Cell rating, low
-18 | Cold store
5 | Chiller
21 | Office
35 | Plant room
60 | Enclosure in sun
85 | Cell rating, high
```
````

```gradient-scale from=-40 to=85 unit=" °C" colours=blue,green,amber,red step=25
-40 | Cell rating, low
-18 | Cold store
5 | Chiller
21 | Office
35 | Plant room
60 | Enclosure in sun
85 | Cell rating, high
```

## `logscale`

Values on a ruler where each power of ten is the same distance apart.

````markdown
```logscale unit=" A" from=1e-7 to=1
2e-6 | Sleep | navy
5e-5 | RTC and sensor idle | blue
1.5e-3 | Measuring | green
8e-3 | Radio receiving | amber
2.2e-1 | Radio sending at full power | red
```
````

```logscale unit=" A" from=1e-7 to=1
2e-6 | Sleep | navy
5e-5 | RTC and sensor idle | blue
1.5e-3 | Measuring | green
8e-3 | Radio receiving | amber
2.2e-1 | Radio sending at full power | red
```

## `spectrum`: visible

Lines on the visible spectrum, here the Balmer lines of hydrogen, with a redshifted copy.

````markdown
```spectrum mode=visible shift=0.05 title="Balmer lines of hydrogen"
656.3 | Hα
486.1 | Hβ
434.0 | Hγ
410.2 | Hδ
```
````

```spectrum mode=visible shift=0.05 title="Balmer lines of hydrogen"
656.3 | Hα
486.1 | Hβ
434.0 | Hγ
410.2 | Hδ
```

## `spectrum`: absorption

Dark lines on a continuous spectrum.

````markdown
```spectrum mode=absorption title="Fraunhofer lines of the Sun"
393.4 | K (Ca)
430.8 | G (Fe, CH)
486.1 | F (Hβ)
518.4 | b (Mg)
589.3 | D (Na)
656.3 | C (Hα)
```
````

```spectrum mode=absorption title="Fraunhofer lines of the Sun"
393.4 | K (Ca)
430.8 | G (Fe, CH)
486.1 | F (Hβ)
518.4 | b (Mg)
589.3 | D (Na)
656.3 | C (Hα)
```

## `spectrum`: emission

Bright lines on black.

````markdown
```spectrum mode=emission title="A neon lamp"
585.2 | 585
614.3 | 614
640.2 | 640
650.7 | 651
703.2 | 703
```
````

```spectrum mode=emission title="A neon lamp"
585.2 | 585
614.3 | 614
640.2 | 640
650.7 | 651
703.2 | 703
```

## `spectrum`: electromagnetic

The whole spectrum on a log scale, with the visible band opened out.

````markdown
```spectrum mode=em title="Where the node's radio sits"
3.6e-1 | NB-IoT, 830 MHz
1.25e-1 | Bluetooth, 2.4 GHz
5.5e-7 | Status LED
1e-10 | X-ray inspection
```
````

```spectrum mode=em title="Where the node's radio sits"
3.6e-1 | NB-IoT, 830 MHz
1.25e-1 | Bluetooth, 2.4 GHz
5.5e-7 | Status LED
1e-10 | X-ray inspection
```

## `spectrum`: stellar classes

The colours of the star classes O to M.

````markdown
```spectrum mode=stellar title="Star classes"
```
````

```spectrum mode=stellar title="Star classes"
```

## `spectrum`: radio channels

Channels as lobes over a band.

````markdown
```spectrum mode=channels title="Wi-Fi and BLE advertising channels" from=2400 to=2485
Wi-Fi 1 | 2412 | 20 | blue
Wi-Fi 6 | 2437 | 20 | blue
Wi-Fi 11 | 2462 | 20 | blue
BLE 37 | 2402 | 2 | amber
BLE 38 | 2426 | 2 | amber
BLE 39 | 2480 | 2 | amber
```
````

```spectrum mode=channels title="Wi-Fi and BLE advertising channels" from=2400 to=2485
Wi-Fi 1 | 2412 | 20 | blue
Wi-Fi 6 | 2437 | 20 | blue
Wi-Fi 11 | 2462 | 20 | blue
BLE 37 | 2402 | 2 | amber
BLE 38 | 2426 | 2 | amber
BLE 39 | 2480 | 2 | amber
```

## `sizes`: circles

Sizes drawn to one scale side by side.

````markdown
```sizes shape=circle unit=" mm"
Coin cell CR2032 | 20 | 225 mAh | grey
AA lithium | 14.5 | 3,000 mAh | blue
C lithium | 26 | 8,500 mAh | navy
D lithium | 33 | 19,000 mAh | green
```
````

```sizes shape=circle unit=" mm"
Coin cell CR2032 | 20 | 225 mAh | grey
AA lithium | 14.5 | 3,000 mAh | blue
C lithium | 26 | 8,500 mAh | navy
D lithium | 33 | 19,000 mAh | green
```

## `sizes`: hexagons

The same, as hexagons, which suit mirror segments and cells.

````markdown
```sizes shape=hexagon
ELT | 39 | Extremely Large Telescope, 798 segments | navy
GMT | 25.4 | Giant Magellan, seven mirrors | blue
JWST | 6.5 | 18 segments | amber
Hubble | 2.4 | One mirror | grey
```
````

```sizes shape=hexagon
ELT | 39 | Extremely Large Telescope, 798 segments | navy
GMT | 25.4 | Giant Magellan, seven mirrors | blue
JWST | 6.5 | 18 segments | amber
Hubble | 2.4 | One mirror | grey
```

## `sizes`: nested squares

`nested=yes` puts them one inside the other.

````markdown
```sizes shape=square nested=yes unit=" mm"
Enclosure | 86 | 86 by 86 mm | grey
PCB | 62 | 62 by 62 mm | green
Radio module | 17.7 | BG77, 14.9 by 12.9 mm | blue
Controller | 5 | QFN-32 | navy
```
````

```sizes shape=square nested=yes unit=" mm"
Enclosure | 86 | 86 by 86 mm | grey
PCB | 62 | 62 by 62 mm | green
Radio module | 17.7 | BG77, 14.9 by 12.9 mm | blue
Controller | 5 | QFN-32 | navy
```

## `vessels`: glasses

Containers on one scale, each filled with its layers from the bottom.

````markdown
```vessels shape=glass
Espresso | 30 ml Espresso (amber)
Macchiato | 30 ml Espresso (amber) + 15 ml Foam (#f6eddc)
Cortado | 30 ml Espresso (amber) + 30 ml Milk (#f3e3c3)
Flat white | 60 ml Ristretto (amber) + 120 ml Microfoam (#f3e3c3)
Latte | 30 ml Espresso (amber) + 200 ml Milk (#f3e3c3) + 20 ml Foam (#f6eddc)
```
````

```vessels shape=glass
Espresso | 30 ml Espresso (amber)
Macchiato | 30 ml Espresso (amber) + 15 ml Foam (#f6eddc)
Cortado | 30 ml Espresso (amber) + 30 ml Milk (#f3e3c3)
Flat white | 60 ml Ristretto (amber) + 120 ml Microfoam (#f3e3c3)
Latte | 30 ml Espresso (amber) + 200 ml Milk (#f3e3c3) + 20 ml Foam (#f6eddc)
```

## `vessels`: cups

````markdown
```vessels shape=cup
Morning | 120 ml Coffee (brown) + 30 ml Milk (#f3e3c3)
Afternoon | 180 ml Tea (#b4540a) + 20 ml Milk (#f3e3c3)
Night shift | 220 ml Coffee (brown)
```
````

```vessels shape=cup
Morning | 120 ml Coffee (brown) + 30 ml Milk (#f3e3c3)
Afternoon | 180 ml Tea (#b4540a) + 20 ml Milk (#f3e3c3)
Night shift | 220 ml Coffee (brown)
```

## `vessels`: beakers

````markdown
```vessels shape=beaker cols=3
Electrolyte | 40 ml Thionyl chloride (#e8d36a) + 10 ml Lithium salt (grey)
Conformal coat | 60 ml Acrylic (#cfe3f7) + 15 ml Thinner (#eeeeee)
Potting | 80 ml Epoxy resin (amber) + 20 ml Hardener (brown)
```
````

```vessels shape=beaker cols=3
Electrolyte | 40 ml Thionyl chloride (#e8d36a) + 10 ml Lithium salt (grey)
Conformal coat | 60 ml Acrylic (#cfe3f7) + 15 ml Thinner (#eeeeee)
Potting | 80 ml Epoxy resin (amber) + 20 ml Hardener (brown)
```

## `tape`

A row of cells with groups bracketed and labelled.

````markdown
```tape
cells: A U G G C U A A A G A U U G A
1-3 | Met (start) | green
4-6 | Ala | blue
7-9 | Lys | navy
10-12 | Asp | amber
13-15 | Stop | red
```
````

```tape
cells: A U G G C U A A A G A U U G A
1-3 | Met (start) | green
4-6 | Ala | blue
7-9 | Lys | navy
10-12 | Asp | amber
13-15 | Stop | red
```

## `ring`

A ring buffer of numbered cells, with filled ranges and pointers.

````markdown
```ring cells=16
fill: 3-9 | Waiting readings | blue
fill: 14-1 | Being sent | amber
pointer: 3 | TAIL (read) | green
pointer: 10 | HEAD (write) | red
```
````

```ring cells=16
fill: 3-9 | Waiting readings | blue
fill: 14-1 | Being sent | amber
pointer: 3 | TAIL (read) | green
pointer: 10 | HEAD (write) | red
```

## `balance`

A beam that tips to the heavier side, each side's weights stacked on its pan.

````markdown
```balance unit=" µA"
left: Budget | 54 | green
right: Sleep | 2 | grey
right: Measuring | 4.4 | blue
right: Radio | 39 | red
right: Self-discharge | 6 | purple
```
````

```balance unit=" µA"
left: Budget | 54 | green
right: Sleep | 2 | grey
right: Measuring | 4.4 | blue
right: Radio | 39 | red
right: Self-discharge | 6 | purple
```
