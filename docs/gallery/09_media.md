# Pictures, codes and text blocks

Blocks that frame pictures, codes and text.

## `figure`

A picture with a caption and credit.

````markdown
```figure
@segments
title: The test plan, by time in the chambers
10 | Damp heat | 85 °C, 85 % RH, 1,000 h | navy
6 | Thermal cycling | -20 to +60 °C, 300 cycles | blue
4 | Drop, vibration | IEC 60068-2-6, -27 | amber
+++
@flow
[Screen|navy] -120 nodes-> [Stress|blue] -failed-> [Teardown|green]
[Stress|blue] -passed-> [Next stage]
+++
@lanes
Chamber A | *Damp heat | *Cycling | Teardown
Chamber B | *Cycling | *Damp heat | Teardown
The two chambers run the stages in opposite orders, so an effect of the order shows up.
```
````

```figure
@segments
title: The test plan, by time in the chambers
10 | Damp heat | 85 °C, 85 % RH, 1,000 h | navy
6 | Thermal cycling | -20 to +60 °C, 300 cycles | blue
4 | Drop, vibration | IEC 60068-2-6, -27 | amber
+++
@flow
[Screen|navy] -120 nodes-> [Stress|blue] -failed-> [Teardown|green]
[Stress|blue] -passed-> [Next stage]
+++
@lanes
Chamber A | *Damp heat | *Cycling | Teardown
Chamber B | *Cycling | *Damp heat | Teardown
The two chambers run the stages in opposite orders, so an effect of the order shows up.
```

## `gallery`

Pictures in a grid, each with a caption.

````markdown
```gallery cols=3
images/mount-wall.svg | On a wall: head height, out of sunlight
images/mount-ceiling.svg | On a ceiling: away from lights and vents
images/mount-pipe.svg | On a pipe: two clamps, never a hot pipe
```
````

```gallery cols=3
images/mount-wall.svg | On a wall: head height, out of sunlight
images/mount-ceiling.svg | On a ceiling: away from lights and vents
images/mount-pipe.svg | On a pipe: two clamps, never a hot pipe
```

## `annotated`

A picture with numbered callouts.

````markdown
```annotated cols=1
images/sn100-board.svg
30%, 40% | Sensor | Temperature and humidity on I2C | blue
60%, 45% | Controller | Wakes on its own timer | navy
82%, 55% | Antenna | 868 MHz, keep metal away | amber
```
````

```annotated cols=1
images/sn100-board.svg
30%, 40% | Sensor | Temperature and humidity on I2C | blue
60%, 45% | Controller | Wakes on its own timer | navy
82%, 55% | Antenna | 868 MHz, keep metal away | amber
```

## `highlight`

A highlighted statement or key figure.

````markdown
```highlight
β 1.78 | Shape | Above 1: cells wear out, with no early failures | navy
18.4 years | Characteristic life (η) | 160,889 h, when 63 % have failed | blue
5.2 years | B10 life | Nine cells in ten last longer | green
```
````

```highlight
β 1.78 | Shape | Above 1: cells wear out, with no early failures | navy
18.4 years | Characteristic life (η) | 160,889 h, when 63 % have failed | blue
5.2 years | B10 life | Nine cells in ten last longer | green
```

## `glossary`

Terms and their meanings.

````markdown
```glossary cols=2
CoAP | Constrained Application Protocol
DTLS | TLS over datagrams
LwM2M | Lightweight M2M device management
NON | A CoAP message that needs no reply
PSM | Power saving mode
QFN | Quad flat package with no leads
```
````

```glossary cols=2
CoAP | Constrained Application Protocol
DTLS | TLS over datagrams
LwM2M | Lightweight M2M device management
NON | A CoAP message that needs no reply
PSM | Power saving mode
QFN | Quad flat package with no leads
```

## `qr`

A QR code of a link or text.

````markdown
```qr size=130 label="Upload the floor plan"
https://example.com/commissioning/upload
```
````

```qr size=130 label="Upload the floor plan"
https://example.com/commissioning/upload
```

## `barcode`

A barcode: EAN, UPC, Code 128 and others.

````markdown
```barcode label="Serial, on the back of the case"
SN-100-0042
```
````

```barcode label="Serial, on the back of the case"
SN-100-0042
```
