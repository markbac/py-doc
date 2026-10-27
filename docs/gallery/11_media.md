# Pictures, QR codes and barcodes

Blocks that frame pictures, and codes a phone or a scanner reads. A picture's path is relative to the Markdown file.

## `gallery`

Pictures in a grid, each with a caption, cropped to one height.

````markdown
```gallery cols=3 height=160
images/mount-wall.svg | On a wall: head height, out of sunlight
images/mount-ceiling.svg | On a ceiling: away from lights and vents
images/mount-pipe.svg | On a pipe: two clamps, never a hot pipe
```
````

```gallery cols=3 height=160
images/mount-wall.svg | On a wall: head height, out of sunlight
images/mount-ceiling.svg | On a ceiling: away from lights and vents
images/mount-pipe.svg | On a pipe: two clamps, never a hot pipe
```

## `annotated`

A picture with numbered pins and a legend of what each marks.

````markdown
```annotated cols=2 alt="The SN-100 board, top side"
images/sn100-board.svg
30%, 40% | Sensor | Temperature and humidity on I2C | blue
60%, 45% | Controller | Wakes on its own timer | navy
82%, 55% | Antenna | 868 MHz, keep metal away | amber
15%, 75% | Cell holder | Lithium side down | red
```
````

```annotated cols=2 alt="The SN-100 board, top side"
images/sn100-board.svg
30%, 40% | Sensor | Temperature and humidity on I2C | blue
60%, 45% | Controller | Wakes on its own timer | navy
82%, 55% | Antenna | 868 MHz, keep metal away | amber
15%, 75% | Cell holder | Lithium side down | red
```

## `zoom-chain`

Pictures that zoom in step by step, each box marking the part the next one shows.

````markdown
```zoom-chain
images/mount-wall.svg | The wall | | 40%, 30%, 30%, 40%
images/mount-pipe.svg | The bracket | 4× | 30%, 30%, 40%, 40%
images/sn100-board.svg | The board inside | 10× |
```
````

```zoom-chain
images/mount-wall.svg | The wall | | 40%, 30%, 30%, 40%
images/mount-pipe.svg | The bracket | 4× | 30%, 30%, 40%, 40%
images/sn100-board.svg | The board inside | 10× |
```

## `qr`: a link

The address or text to encode, with a label.

````markdown
```qr size=150 label="The installer guide"
https://example.com/sn100/install
```
````

```qr size=150 label="The installer guide"
https://example.com/sn100/install
```

## `qr`: a contact

`type=vcard` writes a contact a phone offers to save.

````markdown
```qr type=vcard size=170 label="Field support"
name: Ruth Osei
org: Example Instruments
title: Field support lead
tel: +44 1632 960 100
email: support@example.com
url: https://example.com/support
```
````

```qr type=vcard size=170 label="Field support"
name: Ruth Osei
org: Example Instruments
title: Field support lead
tel: +44 1632 960 100
email: support@example.com
url: https://example.com/support
```

## `qr`: an event

`type=event` writes a calendar event.

````markdown
```qr type=event size=170 label="Commissioning training"
title: SN-100 commissioning training
start: 2026-11-03 09:00
end: 2026-11-03 16:30
location: Leeds test lab
description: Bring a phone with the installer app
```
````

```qr type=event size=170 label="Commissioning training"
title: SN-100 commissioning training
start: 2026-11-03 09:00
end: 2026-11-03 16:30
location: Leeds test lab
description: Bring a phone with the installer app
```

## `qr`: Wi-Fi

`type=wifi` joins a network.

````markdown
```qr type=wifi size=150 label="Site survey network"
ssid: SN100-Survey
password: sensor-node-2026
security: WPA
```
````

```qr type=wifi size=150 label="Site survey network"
ssid: SN100-Survey
password: sensor-node-2026
security: WPA
```

## `qr`: a place

`type=geo` shows a place on a map.

````markdown
```qr type=geo size=150 label="The Leeds site"
lat: 53.7965
lon: -1.5478
```
````

```qr type=geo size=150 label="The Leeds site"
lat: 53.7965
lon: -1.5478
```

## `qr`: an e-mail

`type=email` starts an e-mail with its subject and body.

````markdown
```qr type=email size=150 label="Report a fault"
to: support@example.com
subject: Node fault
body: Site, node number and what the light shows:
```
````

```qr type=email size=150 label="Report a fault"
to: support@example.com
subject: Node fault
body: Site, node number and what the light shows:
```

## `barcode`: Code 128

The default: serial numbers and any short text.

````markdown
```barcode width=320 label="Serial"
SN-100-0042-26W44
```
````

```barcode width=320 label="Serial"
SN-100-0042-26W44
```

## `barcode`: Code 39

Older equipment and labels, with an optional check character.

````markdown
```barcode type=code39 check=yes width=360 label="Asset tag"
SN100-0042
```
````

```barcode type=code39 check=yes width=360 label="Asset tag"
SN100-0042
```

## `barcode`: EAN-13

Retail products. The check digit is worked out when it is left out.

````markdown
```barcode type=ean13 label="Retail box"
501234567890
```
````

```barcode type=ean13 label="Retail box"
501234567890
```

## `barcode`: EAN-8

Small retail products.

````markdown
```barcode type=ean8 label="Spare cell"
9638507
```
````

```barcode type=ean8 label="Spare cell"
9638507
```

## `barcode`: UPC-A

Retail products in North America.

````markdown
```barcode type=upca label="US retail box"
03600029145
```
````

```barcode type=upca label="US retail box"
03600029145
```

## `barcode`: ITF-14

Cartons and outer cases, with bearer bars.

````markdown
```barcode type=itf14 width=400 label="Carton of 20"
1501234567890
```
````

```barcode type=itf14 width=400 label="Carton of 20"
1501234567890
```
