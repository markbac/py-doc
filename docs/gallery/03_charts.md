# Charts, scales and measures

Numbers drawn as charts, gauges and scales.

## `chart`

Column, bar, line, pie and other charts from a table of values.

````markdown
```chart type=column unit=" msg"
series: 2.0, 2.1
Office | 1440 | 610
Warehouse | 1440 | 980
```
````

```chart type=column unit=" msg"
series: 2.0, 2.1
Office | 1440 | 610
Warehouse | 1440 | 980
```

## `vega-lite`

A Vega-Lite chart specification, for any chart Vega-Lite draws.

````markdown
```vega-lite
{
  "data": {"values": [
    {"month": "Jan", "temp": 4}, {"month": "Feb", "temp": 5},
    {"month": "Mar", "temp": 9}, {"month": "Apr", "temp": 13}
  ]},
  "mark": "line",
  "encoding": {
    "x": {"field": "month", "type": "ordinal", "sort": null},
    "y": {"field": "temp", "type": "quantitative"}
  }
}
```
````

```vega-lite
{
  "data": {"values": [
    {"month": "Jan", "temp": 4}, {"month": "Feb", "temp": 5},
    {"month": "Mar", "temp": 9}, {"month": "Apr", "temp": 13}
  ]},
  "mark": "line",
  "encoding": {
    "x": {"field": "month", "type": "ordinal", "sort": null},
    "y": {"field": "temp", "type": "quantitative"}
  }
}
```

## `vega`

A full Vega specification.

````markdown
```vega
{
  "width": 300, "height": 150, "padding": 5,
  "data": [{"name": "table", "values": [{"c": "A", "a": 4}, {"c": "B", "a": 7}, {"c": "C", "a": 2}]}],
  "scales": [
    {"name": "x", "type": "band", "domain": {"data": "table", "field": "c"}, "range": "width", "padding": 0.1},
    {"name": "y", "type": "linear", "domain": {"data": "table", "field": "a"}, "nice": true, "range": "height"}
  ],
  "axes": [{"orient": "bottom", "scale": "x"}, {"orient": "left", "scale": "y"}],
  "marks": [{"type": "rect", "from": {"data": "table"}, "encode": {"enter": {
    "x": {"scale": "x", "field": "c"}, "width": {"scale": "x", "band": 1},
    "y": {"scale": "y", "field": "a"}, "y2": {"scale": "y", "value": 0}}}}]
}
```
````

```vega
{
  "width": 300, "height": 150, "padding": 5,
  "data": [{"name": "table", "values": [{"c": "A", "a": 4}, {"c": "B", "a": 7}, {"c": "C", "a": 2}]}],
  "scales": [
    {"name": "x", "type": "band", "domain": {"data": "table", "field": "c"}, "range": "width", "padding": 0.1},
    {"name": "y", "type": "linear", "domain": {"data": "table", "field": "a"}, "nice": true, "range": "height"}
  ],
  "axes": [{"orient": "bottom", "scale": "x"}, {"orient": "left", "scale": "y"}],
  "marks": [{"type": "rect", "from": {"data": "table"}, "encode": {"enter": {
    "x": {"scale": "x", "field": "c"}, "width": {"scale": "x", "band": 1},
    "y": {"scale": "y", "field": "a"}, "y2": {"scale": "y", "value": 0}}}}]
}
```

## `gauge`

A dial showing one value against its range and bands.

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

Progress bars, one a line.

````markdown
```progress unit=" nodes"
New cells for lot 24-11 | 1,240 | 3,100
Cold-store nodes with a coated sensor | 410 | 6,300
Gateways on 1.5 or later | 2,860 | 2,860
```
````

```progress unit=" nodes"
New cells for lot 24-11 | 1,240 | 3,100
Cold-store nodes with a coated sensor | 410 | 6,300
Gateways on 1.5 or later | 2,860 | 2,860
```

## `rating`

Scores out of a maximum, as stars or dots.

````markdown
```rating current=D potential=B
A | 92+
B | 81-91
C | 69-80
D | 55-68
E | 39-54
F | 21-38
G | 1-20
```
````

```rating current=D potential=B
A | 92+
B | 81-91
C | 69-80
D | 55-68
E | 39-54
F | 21-38
G | 1-20
```

## `threshold`

A value against warning and alarm thresholds.

````markdown
```threshold title="Smart prepayment credit lifecycle"
span: Normal credit | £20.00 to £2.00 | Everyday use, supply on | green | 4
pin: £2.00 Low credit alert, emergency credit can be armed | amber
span: Low credit | £2.00 to £0.00 | The customer can arm emergency credit | amber | 2
pin: £0.00 Credit exhausted | red
span: Emergency credit | A £10.00 pool | Borrowed, the supply stays on | purple | 3
pin: -£10.00 Hard cut-off, the valve closes | red
span: Disconnected | A top-up repays the £10.00 first | grey | 2
```
````

```threshold title="Smart prepayment credit lifecycle"
span: Normal credit | £20.00 to £2.00 | Everyday use, supply on | green | 4
pin: £2.00 Low credit alert, emergency credit can be armed | amber
span: Low credit | £2.00 to £0.00 | The customer can arm emergency credit | amber | 2
pin: £0.00 Credit exhausted | red
span: Emergency credit | A £10.00 pool | Borrowed, the supply stays on | purple | 3
pin: -£10.00 Hard cut-off, the valve closes | red
span: Disconnected | A top-up repays the £10.00 first | grey | 2
```

## `buckets`

Counts in bands, such as a histogram of ranges.

````markdown
```buckets unit="£"
Emergency credit | 10 | 10 | amber
Normal credit | 8.4 | 30 | green | 2 Low credit
Debt | 6 | 50 | red | 25 Recovery limit
```
````

```buckets unit="£"
Emergency credit | 10 | 10 | amber
Normal credit | 8.4 | 30 | green | 2 Low credit
Debt | 6 | 50 | red | 25 Recovery limit
```

## `dial24`

Events around a 24-hour clock.

````markdown
```dial24 title="A weekday"
18:00 | 09:00 | Friendly hours, no cut-off | green
00:00 | 05:00 | Off-peak tariff | blue
16:00 | 19:00 | Peak demand | red
```
````

```dial24 title="A weekday"
18:00 | 09:00 | Friendly hours, no cut-off | green
00:00 | 05:00 | Off-peak tariff | blue
16:00 | 19:00 | Peak demand | red
```

## `gradient-scale`

A colour scale with labelled stops.

````markdown
```gradient-scale from=0 to=200 unit=" °C" colours=blue,green,amber,red
65 | Eggs set
100 | Water boils
150 | Browning starts
170 | Sugar caramelises
```
````

```gradient-scale from=0 to=200 unit=" °C" colours=blue,green,amber,red
65 | Eggs set
100 | Water boils
150 | Browning starts
170 | Sugar caramelises
```

## `logscale`

Things placed on a logarithmic scale.

````markdown
```logscale unit=" s"
1e-9 | Cache read
1e-7 | Memory read
1.5e-4 | Flash read
1e-2 | Disk seek
1.5e-1 | Across an ocean
2 | NB-IoT wake and send
```
````

```logscale unit=" s"
1e-9 | Cache read
1e-7 | Memory read
1.5e-4 | Flash read
1e-2 | Disk seek
1.5e-1 | Across an ocean
2 | NB-IoT wake and send
```

## `spectrum`

Bands along a spectrum, such as radio or light.

````markdown
```spectrum mode=absorption title="The Sun's dark lines"
656.3 | Hα
589 | Na D
527 | Fe
486.1 | Hβ
430.8 | G band
```
````

```spectrum mode=absorption title="The Sun's dark lines"
656.3 | Hα
589 | Na D
527 | Fe
486.1 | Hβ
430.8 | G band
```

## `sizes`

Sizes drawn to one scale side by side.

````markdown
```sizes shape=hexagon
ELT | 39 | Extremely Large Telescope | navy
JWST | 6.5 | 18 segments | amber
Hubble | 2.4 | One mirror | blue
```
````

```sizes shape=hexagon
ELT | 39 | Extremely Large Telescope | navy
JWST | 6.5 | 18 segments | amber
Hubble | 2.4 | One mirror | blue
```

## `tape`

A row of cells with labelled groups, such as a sequence.

````markdown
```tape
cells: A U G G C U U A A
1-3 | Met (start) | green
4-6 | Ala | blue
7-9 | Stop | red
```
````

```tape
cells: A U G G C U U A A
1-3 | Met (start) | green
4-6 | Ala | blue
7-9 | Stop | red
```
