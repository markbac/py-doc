---
title: Skyward WS-7 weather station
subtitle: Seven instruments on one mast, reporting every minute from the hilltop
byline: Skyward Instruments field science team
orientation: landscape
paper: a1
columns: 4
---

## Key figures {.stats style=tiles colour=brand}

| Value | Label |
|---|---|
| 7 | Instruments on the mast |
| 1 min | Between reports |
| ±0.1 °C | Air temperature |
| 0 W | From the grid: solar and a cell |

## Introduction {.abstract style=quote}

The WS-7 stands on Cairn Hill at 412 m. It measures the air, the wind, the rain and the sun, and sends a report every minute over LoRaWAN to the school's server, where the class sees the weather of the last hour, day and year.

## 1. The mast: what each instrument measures

```cards cols=2 style=top
Thermometer | Air temperature, in a ventilated screen 1.5 m up | brand | icon=tabler:temperature
Hygrometer | Relative humidity, from which the dew point | second | icon=tabler:droplet
Barometer | Pressure, corrected to sea level | grey | icon=tabler:gauge
Anemometer | Wind speed, three cups at 10 m | spark | icon=tabler:wind
Wind vane | Wind direction, in 16 points | amber | icon=tabler:compass
Rain gauge | A tipping bucket: 0.2 mm a tip | blue | icon=tabler:cloud-rain
Pyranometer | Sunshine, in W/m² | spark | icon=tabler:sun
```

## 2. Today: temperature and dew point

```chart type=line title="Cairn Hill, 21 March" unit=" °C" axis="°C" min=-2 max=14 area=yes values=last
series: Air, Dew point
00:00 | 3.1 | 1.2
03:00 | 1.8 | 0.9
06:00 | 1.2 | 0.6
09:00 | 5.6 | 1.8
12:00 | 10.4 | 2.9
15:00 | 12.1 | 3.4
18:00 | 8.2 | 3.6
21:00 | 5.0 | 3.1
```

When the air cools to the dew point, the humidity reaches 100 % and fog or frost forms. At dawn the gap was only 0.6 °C.

## 3. Wind: where it came from this month

```plot type=polar title="Hours of wind from each direction, March"
N | 42
NE | 31
E | 18
SE | 22
S | 57
SW | 148
W | 121
NW | 63
```

## 4. Gusts: the wind right now

```gauge value=38 min=0 max=120 unit=" km/h" label="Gust now"
0 | 39 | green
39 | 62 | amber
62 | 88 | brown
88 | 120 | red
```

Above 62 km/h the school's outdoor lessons move inside; above 88 km/h the mast is checked after the storm.

## 5. The sky: layers above the station

```cutaway type=column unit=" km"
0 | 2 | Boundary layer | Where the station measures, and fog forms | green
2 | 12 | Troposphere | Clouds and weather; 6.5 °C colder a kilometre | brand
12 | 50 | Stratosphere | The ozone layer, warmer with height | second
50 | 85 | Mesosphere | Meteors burn up | spark
```

## 6. Pressure: why the weather changes

```threshold
span: Stormy | Below 970 hPa: deep lows, gales | red | 1
pin: 970 hPa | red
span: Rain | Fronts and showers | amber | 2
pin: 1000 hPa | amber
span: Change | Unsettled, then improving | grey | 2
pin: 1020 hPa | green
span: Fair | Highs: settled and dry | green | 2
pin: 1040 hPa | blue
span: Very dry | Cold and clear in winter | blue | 1
```

Falling pressure brings cloud and rain; rising pressure brings clear skies. The WS-7 warns when it falls 3 hPa in three hours.

## 7. Report: one minute on the air

```syntax-anatomy
WS7,0412,T+0563,H081,P10123,W038S,R0002,S0412
WS7 | Station type | brand
0412 | Height (m) | grey
T+0563 | Temperature 5.63 °C | red
H081 | Humidity 81 % | blue
P10123 | Pressure 1012.3 hPa | second
W038S | Gust 38 km/h from the south | spark
R0002 | Rain 0.2 mm | blue
S0412 | Sun 412 W/m² | amber
```

## 8. A day of power: the sun pays for the night

```dial24 title="21 March"
06:15 | 18:10 | Solar charging | spark
18:10 | 06:15 | On the cell | brand
00:00 | 24:00 | Reporting every minute | green
```

## 9. The energy budget: a sunny day

```balance unit=" Wh"
left: Solar | 9.6 | spark
right: Sensors | 2.9 | brand
right: Radio | 0.6 | second
right: Heater | 3.0 | grey
```

On a bright day the panel makes 9.6 Wh, three times what the sensors, radio and the rain gauge heater use; the spare charge carries it through cloudy days.

## In short {.summary}

The weather of a hilltop, measured every minute and powered by the sun.

### Seven instruments

Air, wind, rain and sun, from one mast.

### Every minute

A 46-character report, over LoRaWAN, to the classroom.

### Off grid

A 10 W panel and a cell carry it through the night.
