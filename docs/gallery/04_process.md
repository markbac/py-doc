# Processes, plans and comparisons

How work flows, what happens when, and how options compare.

## `flow`

A simple left-to-right flow of steps.

````markdown
```flow
[Unjoined|slate] -button 3 s-> [Joining|sea] -key accepted-> [Joined|teal]
[Joining|sea] -no gateway-> [Retries every 10 min]
```
````

```flow
[Unjoined|slate] -button 3 s-> [Joining|sea] -key accepted-> [Joined|teal]
[Joining|sea] -no gateway-> [Retries every 10 min]
```

## `steps`

Numbered steps with their detail.

````markdown
```steps
Upload the floor plan | From the app, with every node marked
Walk the dashboard | With the customer: every node, every room
Leave the spares | The spare cells and the support number, on site | coral
```
````

```steps
Upload the floor plan | From the app, with every node marked
Walk the dashboard | With the customer: every node, every room
Leave the spares | The spare cells and the support number, on site | coral
```

## `lanes`

Steps in swim lanes, one lane a role.

````markdown
```lanes
Gateway | *Mount | *Power | *Ethernet | Check light
Node | *Fix plate | *Insert cell | Clip on
```
````

```lanes
Gateway | *Mount | *Power | *Ethernet | Check light
Node | *Fix plate | *Insert cell | Clip on
```

## `timeline`

Dated events along a line.

````markdown
```timeline
Jan 2026 | Pilot | 200 nodes in two buildings | navy
Apr 2026 | Firmware 2.1 | Sends only what changed | blue
Jul 2026 | Display option | For installers | green
Oct 2026 | Ten-year cell | Twice the life | amber
```
````

```timeline
Jan 2026 | Pilot | 200 nodes in two buildings | navy
Apr 2026 | Firmware 2.1 | Sends only what changed | blue
Jul 2026 | Display option | For installers | green
Oct 2026 | Ten-year cell | Twice the life | amber
```

## `cycle`

Stages that repeat, around a circle.

````markdown
```cycle
Evaporation | Sun heats the sea | amber
Condensation | Clouds form | blue
Precipitation | Rain and snow | navy
Collection | Rivers and lakes | green
```
````

```cycle
Evaporation | Sun heats the sea | amber
Condensation | Clouds form | blue
Precipitation | Rain and snow | navy
Collection | Rivers and lakes | green
```

## `funnel`

Stages that narrow, with their counts.

````markdown
```funnel
Candidates | 4,000 | Transit signals | blue
Vetted | 1,200 | Not false positives | navy
Confirmed | 300 | Radial velocity | green
```
````

```funnel
Candidates | 4,000 | Transit signals | blue
Vetted | 1,200 | Not false positives | navy
Confirmed | 300 | Radial velocity | green
```

## `vsm`

A value stream map with process and wait times.

````markdown
```vsm
inventory: 5 days
process: Solder | C/T 40 s
inventory: 1 day
process: Pack | C/T 20 s
```
````

```vsm
inventory: 5 days
process: Solder | C/T 40 s
inventory: 1 day
process: Pack | C/T 20 s
```

## `idef0`

An IDEF0 function box with its inputs, controls, outputs and mechanisms.

````markdown
```idef0
box: A1 Measure
in: Air
out: Reading
box: A2 Send
in: Reading
out: Message
```
````

```idef0
box: A1 Measure
in: Air
out: Reading
box: A2 Send
in: Reading
out: Message
```

## `n2`

An N-squared chart of the interfaces between parts.

````markdown
```n2
Sensor -> Controller | Reading
Controller -> Radio | Message
```
````

```n2
Sensor -> Controller | Reading
Controller -> Radio | Message
```

## `structogram`

A Nassi-Shneiderman structogram of an algorithm.

````markdown
```structogram
Read the sensor
if Reading changed?
  Send it
else
  Sleep
```
````

```structogram
Read the sensor
if Reading changed?
  Send it
else
  Sleep
```

## `checklist`

A checklist with done, open and failed items.

````markdown
```checklist
[ ] Its signal is -95 dBm or better, in the app after the join
[ ] Its first reading reaches the dashboard within 2 minutes
[ ] Its reading is within 1 °C of the room thermometer
[ ] Its label photo and room are recorded in the app
```
````

```checklist
[ ] Its signal is -95 dBm or better, in the app after the join
[ ] Its first reading reaches the dashboard within 2 minutes
[ ] Its reading is within 1 °C of the room thermometer
[ ] Its label photo and room are recorded in the app
```

## `compare`

Options compared feature by feature.

````markdown
```compare
| 2.0 | 2.1
Typical join | 11 s | 4 s
Channels scanned | 8 | 3, or 1 when the last still works
Battery life | 5.0 years | 5.7 years
Firmware copies | 1 | 2
```
````

```compare
| 2.0 | 2.1
Typical join | 11 s | 4 s
Channels scanned | 8 | 3, or 1 when the last still works
Battery life | 5.0 years | 5.7 years
Firmware copies | 1 | 2
```

## `proscons`

Pros and cons side by side.

````markdown
```proscons
+ Ten-year battery with PSM
+ Reaches the meter cupboard
+ Runs on the operator's network
- Up to ten seconds to reach the node
- No voice, little bandwidth
```
````

```proscons
+ Ten-year battery with PSM
+ Reaches the meter cupboard
+ Runs on the operator's network
- Up to ten seconds to reach the node
- No voice, little bandwidth
```

## `people`

People and their roles, as cards with initials.

````markdown
```people cols=2
Lena Chen | Firmware release manager | sn100-firmware@example.com
Ruth Osei | Field support lead | +44 1632 960 100
```
````

```people cols=2
Lena Chen | Firmware release manager | sn100-firmware@example.com
Ruth Osei | Field support lead | +44 1632 960 100
```

## `cards`

A grid of cards, each a title, text and an icon.

````markdown
```cards cols=3 style=top
Sensor | Temperature and humidity on I2C | blue
Controller | Sleeps at 2 µA | navy
Radio | Sends one message, then sleeps | green
```
````

```cards cols=3 style=top
Sensor | Temperature and humidity on I2C | blue
Controller | Sleeps at 2 µA | navy
Radio | Sends one message, then sleeps | green
```
