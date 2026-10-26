---
title: Inside an LwM2M reading
subtitle: From the pins of the chip to the bytes on the air
byline: py-doc example poster for the protocol and embedded blocks
orientation: landscape
paper: a1
width: 1800
columns: 3
footer:
  left: Embedded blocks
  right: docs/guide/12_posters.md, Poster blocks
---

## Introduction {.abstract}

A temperature reading leaves the SN-100 as one CoAP message. Each section shows one step of its way with a block made for it: the pins, the bus, the code, the address and the bytes.

## 1. Chip: the pins that matter

```pinout package=qfn title="SN-100 controller, QFN-16"
1 | VDD | pwr
2 | PA0 | adc
3 | PA1 | gpio
4 | NRST | reset
5 | SDA | i2c
6 | SCL | i2c
7 | TX | uart
8 | RX | uart
9 | GND | gnd
10 | SWDIO | swd
11 | SWCLK | swd
12 | PB0 | pwm
13 | MOSI | spi
14 | MISO | spi
15 | SCK | spi
16 | VDDA | pwr
```

## 2. Bus: the sensor read

```instrument type=logic title="I2C read of the sensor"
SCL | 1101010101010101010101111
SDA | 1100110011110000110000111
```

```instrument type=scope vdiv=1 tdiv="10 µs" cursors=2,6 title="The rise of SDA on the scope"
SDA | | 0 0 0.4 1.6 2.6 3.1 3.3 3.3 3.3 3.3 3.3 2.4 1.1 0.3 0 0 0 0 0.4 1.6 2.6 3.1 3.3 3.3 3.3
```

## 3. Current: one reading, measured

```instrument type=meter value="2.41 µA" label="Asleep, between readings" min="2.38" max="2.47" avg="2.41"
```

## 4. Code: the copy that overflowed {.wide}

```code-compare
@bad Unsafe C
char uri[16];
strcpy(uri, path);          <1>
coap_set_uri(msg, uri);
@good Bounded C
char uri[16];
if (strlen(path) >= sizeof uri)  <2>
    return E_URI_TOO_LONG;
strcpy(uri, path);
coap_set_uri(msg, uri);
-- 1 | A path longer than 15 characters writes past the buffer
-- 2 | The length is checked against the buffer before the copy
```

## 5. Address: the resource of the reading

```syntax-anatomy
coaps://lwm2m.example.com:5684/3303/0/5700
coaps | Scheme: CoAP over DTLS | navy
lwm2m.example.com | Server | blue
5684 | Port | grey
3303 | Object: Temperature | green
0 | Instance | amber
5700 | Resource: Sensor Value | red
```

## 6. Bytes: the message on the air {.wide}

```hex-dissect title="A CoAP notification with the reading"
bytes: 54 45 7a 31 d2 ab 3c 01 c1 3c ff 32 31 2e 34
0 | Ver 1, type NON, token length 4 | 0x54 | navy
1 | Code | 2.05 Content | blue
2-3 | Message ID | 0x7a31 | green
4-7 | Token | d2 ab 3c 01 | amber
8-9 | Option | Content-Format: text/plain | purple
10 | Payload marker | 0xff | grey
11-14 | Payload | 21.4 | red
```

## 7. Trade-offs: NB-IoT for this node

```proscons
+ Ten-year battery with PSM
+ Reaches the meter cupboard
+ Runs on the operator's network
- Up to ten seconds to reach the node
- No voice, little bandwidth
```

The trend of a week's readings {spark 21.4,21.9,22.6,21.1,20.8,21.7,22.0} stays inside half a degree of its mean.

## 8. Board: where things are

```annotated cols=1
images/sn100-board.svg
30%, 40% | Sensor | Temperature and humidity on I2C | blue
60%, 45% | Controller | Wakes on its own timer | navy
82%, 55% | Antenna | 868 MHz, keep metal away | amber
```

## 9. Mounting: from the room to the node

```zoom-chain
images/mount-wall.svg | The wall | | 40%, 30%, 30%, 40%
images/mount-pipe.svg | The bracket | 4× | 30%, 30%, 40%, 40%
images/mount-ceiling.svg | The node | 10× |
```

## 10. Words: the terms used here

```glossary cols=2
CoAP | Constrained Application Protocol
DTLS | TLS over datagrams
LwM2M | Lightweight M2M device management
NON | A CoAP message that needs no reply
PSM | Power saving mode
QFN | Quad flat package with no leads
```

## In short {.summary}

From pin to packet, a reading is one small message: each block shows one step of its way.
