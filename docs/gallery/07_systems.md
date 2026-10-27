# Safety and systems engineering

The notations of safety cases, reliability and systems engineering, drawn with their own symbols.

## `fault-tree`

A top event and its causes, indented two spaces a level. Gates are `or:`, `and:`, `xor:`, `pand:`, `inhibit:` and `k/n:`; causes are `basic:`, `undeveloped:`, `house:` and `transfer:`, each with an optional probability.

````markdown
```fault-tree
or: Node stops reporting
  and: No power
    basic: Cell flat | 1e-3
    basic: Supercap backup fails | 0.05
  or: Radio cannot send
    basic: Modem fault | 2e-4
    inhibit: Signal lost | | Node in a metal cupboard
      basic: Operator re-farms the band | 1e-3
    undeveloped: Operator outage
  2/3: Firmware hangs
    basic: Watchdog disabled | 1e-4
    basic: Flash full | 5e-4
    basic: RTC drift misses the wake | 3e-4
  house: Node in transport mode
  transfer: Gateway down (tree G2)
```
````

```fault-tree
or: Node stops reporting
  and: No power
    basic: Cell flat | 1e-3
    basic: Supercap backup fails | 0.05
  or: Radio cannot send
    basic: Modem fault | 2e-4
    inhibit: Signal lost | | Node in a metal cupboard
      basic: Operator re-farms the band | 1e-3
    undeveloped: Operator outage
  2/3: Firmware hangs
    basic: Watchdog disabled | 1e-4
    basic: Flash full | 5e-4
    basic: RTC drift misses the wake | 3e-4
  house: Node in transport mode
  transfer: Gateway down (tree G2)
```

## `bowtie`

Threats on the left with their preventive barriers, consequences on the right with their mitigating barriers, and the top event and hazard between.

````markdown
```bowtie
hazard: Lithium thionyl chloride cell
top: Thermal runaway
threat: Charged by mistake | Diode in series, Cell monitor
threat: Crushed in the wall | Steel back plate
threat: Short across the terminals | Fuse, Insulating sleeve
threat: Stored above 85 °C | Warning label, Training
consequence: Fire in the room | Vent path, Fire-rated case
consequence: Toxic smoke | Smoke alarm, Evacuation plan
consequence: Node lost | Spare stock, Remote monitoring
```
````

```bowtie
hazard: Lithium thionyl chloride cell
top: Thermal runaway
threat: Charged by mistake | Diode in series, Cell monitor
threat: Crushed in the wall | Steel back plate
threat: Short across the terminals | Fuse, Insulating sleeve
threat: Stored above 85 °C | Warning label, Training
consequence: Fire in the room | Vent path, Fire-rated case
consequence: Toxic smoke | Smoke alarm, Evacuation plan
consequence: Node lost | Spare stock, Remote monitoring
```

## `gsn`

A Goal Structuring Notation argument. Goals, strategies and solutions support the line above them; context, assumptions and justifications sit beside it.

````markdown
```gsn
goal G1: The SN-100 is safe to install in occupied buildings
  context C1: Indoor use, 0 to 40 °C, wall or pipe mounted
  assumption A1: Installed by trained installers
  strategy S1: Argue over each identified hazard
    justification J1: Hazard log HL-07 is complete, reviewed 2026-06
    goal G2: Thermal runaway of the cell is prevented
      solution Sn1: Abuse test report TR-221
      solution Sn2: Cell monitor design review
    goal G3: The enclosure contains a cell fire
      solution Sn3: UL 94 V-0 test of the enclosure
    goal G4: Radio exposure is within limits
      solution Sn4: RF exposure assessment
    goal G5: Mounting does not fail | undeveloped
```
````

```gsn
goal G1: The SN-100 is safe to install in occupied buildings
  context C1: Indoor use, 0 to 40 °C, wall or pipe mounted
  assumption A1: Installed by trained installers
  strategy S1: Argue over each identified hazard
    justification J1: Hazard log HL-07 is complete, reviewed 2026-06
    goal G2: Thermal runaway of the cell is prevented
      solution Sn1: Abuse test report TR-221
      solution Sn2: Cell monitor design review
    goal G3: The enclosure contains a cell fire
      solution Sn3: UL 94 V-0 test of the enclosure
    goal G4: Radio exposure is within limits
      solution Sn4: RF exposure assessment
    goal G5: Mounting does not fail | undeveloped
```

## `n2`

An N² chart: the items on the diagonal, each interface in the row of its source and the column of its destination. Feedback, below the diagonal, is shaded.

````markdown
```n2
items: Sensor, Controller, Radio, Cloud, App
Sensor -> Controller | Reading over I2C
Controller -> Sensor | Power on, configure
Controller -> Radio | AT commands over UART
Radio -> Controller | Network time, status
Radio -> Cloud | CoAP over NB-IoT
Cloud -> Radio | Firmware, settings
Cloud -> App | Readings, alarms
App -> Cloud | Commissioning
```
````

```n2
items: Sensor, Controller, Radio, Cloud, App
Sensor -> Controller | Reading over I2C
Controller -> Sensor | Power on, configure
Controller -> Radio | AT commands over UART
Radio -> Controller | Network time, status
Radio -> Cloud | CoAP over NB-IoT
Cloud -> Radio | Firmware, settings
Cloud -> App | Readings, alarms
App -> Cloud | Commissioning
```

## `idef0`

Integration Definition for Function Modelling (IDEF0) boxes with inputs from the left, controls from the top, outputs to the right and mechanisms from below.

````markdown
```idef0
box: A1 Measure the room
in: Air
control: Sample interval, Threshold
out: Reading
mech: SHT40 sensor
box: A2 Decide what to send
in: Reading
control: Last sent value
out: Changed reading
mech: Controller
box: A3 Send the reading
in: Changed reading
control: Radio settings, Network time
out: CoAP message
mech: BG77 modem
box: A4 Store and show it
in: CoAP message
control: Retention policy
out: Dashboard, Alarms
mech: SN-100 platform
```
````

```idef0
box: A1 Measure the room
in: Air
control: Sample interval, Threshold
out: Reading
mech: SHT40 sensor
box: A2 Decide what to send
in: Reading
control: Last sent value
out: Changed reading
mech: Controller
box: A3 Send the reading
in: Changed reading
control: Radio settings, Network time
out: CoAP message
mech: BG77 modem
box: A4 Store and show it
in: CoAP message
control: Retention policy
out: Dashboard, Alarms
mech: SN-100 platform
```

## `vsm`

A value stream map: supplier and customer, processes and inventory in order, and the timeline of waits and work under them.

````markdown
```vsm
supplier: Cell maker | Weekly, 5,000 cells
customer: Installers | 400 nodes a day
inventory: 5 days
process: Solder | C/T 40 s | Uptime 92 % | 2 operators
inventory: 2 days
process: Flash and test | C/T 30 s | 1 operator | Yield 98.5 %
inventory: 1 day
process: Coat | C/T 25 s | Cure 2 h
inventory: 0.5 days
process: Pack | C/T 20 s
inventory: 3 days
```
````

```vsm
supplier: Cell maker | Weekly, 5,000 cells
customer: Installers | 400 nodes a day
inventory: 5 days
process: Solder | C/T 40 s | Uptime 92 % | 2 operators
inventory: 2 days
process: Flash and test | C/T 30 s | 1 operator | Yield 98.5 %
inventory: 1 day
process: Coat | C/T 25 s | Cure 2 h
inventory: 0.5 days
process: Pack | C/T 20 s
inventory: 3 days
```

## `structogram`

A Nassi-Shneiderman structogram: steps, decisions, loops and cases, by indentation.

````markdown
```structogram
Wake on the timer
Read the sensor
if Reading changed by more than the threshold?
  Queue it
else
  Count the skip
  if 24 h since the last send?
    Queue a keep-alive
for Each queued message
  repeat
    Send it
  until Acknowledged or three tries
case Battery level
  when Above 2.8 V
    Keep the interval
  when 2.4 to 2.8 V
    Double the interval
  else
    Send the low-battery alarm
Sleep
```
````

```structogram
Wake on the timer
Read the sensor
if Reading changed by more than the threshold?
  Queue it
else
  Count the skip
  if 24 h since the last send?
    Queue a keep-alive
for Each queued message
  repeat
    Send it
  until Acknowledged or three tries
case Battery level
  when Above 2.8 V
    Keep the interval
  when 2.4 to 2.8 V
    Double the interval
  else
    Send the low-battery alarm
Sleep
```
