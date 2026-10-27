# Electronics, embedded and code

Boards, signals, memory, logic and code.

## `circuit`

A circuit schematic from a list of parts and where they go.

````markdown
```circuit
V1: battery 3 V | up
R1: resistor 100 kΩ | right
R2: resistor 100 kΩ | down
line | to V1.start
dot | at R1.end
```
````

```circuit
V1: battery 3 V | up
R1: resistor 100 kΩ | right
R2: resistor 100 kΩ | down
line | to V1.start
dot | at R1.end
```

## `wavedrom`

Digital timing waveforms.

````markdown
```wavedrom
{ signal: [
  { name: "SCL", wave: "p....." },
  { name: "SDA", wave: "x345x.", data: ["addr", "data", "ack"] }
]}
```
````

```wavedrom
{ signal: [
  { name: "SCL", wave: "p....." },
  { name: "SDA", wave: "x345x.", data: ["addr", "data", "ack"] }
]}
```

## `bytefield-svg`

The bytes and fields of a register or a message.

````markdown
```bytefield-svg
(def boxes-per-row 8)
(draw-column-headers)
(draw-box "Version" {:span 2})
(draw-box "Type" {:span 2})
(draw-box "Length" {:span 4})
(draw-box "Payload" {:span 8})
```
````

```bytefield-svg
(def boxes-per-row 8)
(draw-column-headers)
(draw-box "Version" {:span 2})
(draw-box "Type" {:span 2})
(draw-box "Length" {:span 4})
(draw-box "Payload" {:span 8})
```

## `wireviz`

A wiring harness: connectors, cables and pins.

````markdown
```wireviz
connectors:
  X1:
    pincount: 2
  X2:
    pincount: 2
cables:
  W1:
    wirecount: 2
    colors: [RD, BK]
connections:
  -
    - X1: [1, 2]
    - W1: [1, 2]
    - X2: [1, 2]
```
````

```wireviz
connectors:
  X1:
    pincount: 2
  X2:
    pincount: 2
cables:
  W1:
    wirecount: 2
    colors: [RD, BK]
connections:
  -
    - X1: [1, 2]
    - W1: [1, 2]
    - X2: [1, 2]
```

## `pinout`

The pins of a chip or a connector, with their functions.

````markdown
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
````

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

## `instrument`

An instrument face, such as a meter or a scope.

````markdown
```instrument type=logic title="I2C read of the sensor"
SCL | 1101010101010101010101111
SDA | 1100110011110000110000111
```
````

```instrument type=logic title="I2C read of the sensor"
SCL | 1101010101010101010101111
SDA | 1100110011110000110000111
```

## `lcd`

Text on a character LCD.

````markdown
```lcd
JOINED  GW-2
RSSI -71 dBm
-- Good signal

T  21.4 C
RH 48 %
-- First reading
```
````

```lcd
JOINED  GW-2
RSSI -71 dBm
-- Good signal

T  21.4 C
RH 48 %
-- First reading
```

## `segments`

Digits on a seven-segment display.

````markdown
```segments
title: Signal strength at the node (dBm)
3 | Excellent | -40 to -70 | teal
2 | Good | -70 to -85 | sea
2 | Weak | -85 to -95 | sand
1 | Move it | below -95 | coral
```
````

```segments
title: Signal strength at the node (dBm)
3 | Excellent | -40 to -70 | teal
2 | Good | -70 to -85 | sea
2 | Weak | -85 to -95 | sand
1 | Move it | below -95 | coral
```

## `hex-dissect`

A hex dump with its fields marked.

````markdown
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
````

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

## `memory`

A memory map of regions and their addresses.

````markdown
```memory
0x0800_0000 | 32 KB | Bootloader | navy
0x0800_8000 | 224 KB | Application | blue
0x2000_0000 | 8 KB | Heap | green | up
0x2000_E000 | 8 KB | Stack | amber | down
```
````

```memory
0x0800_0000 | 32 KB | Bootloader | navy
0x0800_8000 | 224 KB | Application | blue
0x2000_0000 | 8 KB | Heap | green | up
0x2000_E000 | 8 KB | Stack | amber | down
```

## `plc-ladder`

A PLC ladder diagram of contacts and coils.

````markdown
```plc-ladder
rung: Start and stop the pump
NO Start | NC Stop | COIL Pump
branch: NO Pump
```
````

```plc-ladder
rung: Start and stop the pump
NO Start | NC Stop | COIL Pump
branch: NO Pump
```

## `kmap`

A Karnaugh map with its minimal cover.

````markdown
```kmap name=Alarm
vars: A B C
ones: 1 3 5 7
```
````

```kmap name=Alarm
vars: A B C
ones: 1 3 5 7
```

## `terminal`

A terminal session, commands and output.

````markdown
```terminal title="sn100-cli"
$ sn100 update --site leeds --firmware 2.1
# 48 nodes, 2 skipped (battery below 2.4 V)
queued   48
updated  48 / 48, 0 failed
-- An update of one site, from the field tool
```
````

```terminal title="sn100-cli"
$ sn100 update --site leeds --firmware 2.1
# 48 nodes, 2 skipped (battery below 2.4 V)
queued   48
updated  48 / 48, 0 failed
-- An update of one site, from the field tool
```

## `syntax-anatomy`

A line of code or syntax with its parts named.

````markdown
```syntax-anatomy
coaps://lwm2m.example.com:5684/3303/0/5700
coaps | Scheme: CoAP over DTLS | navy
lwm2m.example.com | Server | blue
5684 | Port | grey
3303 | Object: Temperature | green
0 | Instance | amber
5700 | Resource: Sensor Value | red
```
````

```syntax-anatomy
coaps://lwm2m.example.com:5684/3303/0/5700
coaps | Scheme: CoAP over DTLS | navy
lwm2m.example.com | Server | blue
5684 | Port | grey
3303 | Object: Temperature | green
0 | Instance | amber
5700 | Resource: Sensor Value | red
```

## `code-compare`

Two versions of code side by side.

````markdown
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
````

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
