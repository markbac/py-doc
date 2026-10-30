# Concept shapes

Shapes that carry an idea: levels, layers, what is hidden, and what lies inside what.

## `pyramid`

Tiers from the top, labelled inside, with their detail beside.

````markdown
```pyramid
End-to-end | 5 % | Real network and hardware, nightly | red
Hardware in the loop | 15 % | Automated rig with RF attenuators | amber
Integration | 25 % | Simulated peripherals, on every merge | blue
Unit | 55 % | Off target, under a second each | green
```
````

```pyramid
End-to-end | 5 % | Real network and hardware, nightly | red
Hardware in the loop | 15 % | Automated rig with RF attenuators | amber
Integration | 25 % | Simulated peripherals, on every merge | blue
Unit | 55 % | Off target, under a second each | green
```

## `pyramid`: upside down

`direction=down` puts the widest tier at the top: still flat, where a `cone` is round.

````markdown
```pyramid direction=down
Every reading | 96 a day | Measured on the node | navy
Changed readings | 21 a day | Sent over the radio | blue
Alarms | 1 a week | Shown to the site manager | amber
Site visits | 1 a year | Booked by support | red
```
````

```pyramid direction=down
Every reading | 96 a day | Measured on the node | navy
Changed readings | 21 a day | Sent over the radio | blue
Alarms | 1 a week | Shown to the site manager | amber
Site visits | 1 a year | Booked by support | red
```

## `cone`

Tiers as bands of a solid cone, round and widest at the top: here, ideas narrowing to what was built.

````markdown
```cone
Requests | 400 | From customers, support and the field | blue
Scoped | 120 | Fits the platform and the year | navy
Planned | 45 | In a release | green
Built | 30 | Shipped in 2026 | amber
```
````

```cone
Requests | 400 | From customers, support and the field | blue
Scoped | 120 | Fits the platform and the year | navy
Planned | 45 | In a release | green
Built | 30 | Shipped in 2026 | amber
```

## `stack`

Layers from the top, full width, with brackets beside the layers they span.

````markdown
```stack
Application | L7 | LwM2M objects: temperature, battery, firmware | green
Session | L5-6 | CoAP, with block-wise transfer for firmware | blue
Security | | DTLS 1.2, certificates in the secure element | red
Transport | L4 | UDP | navy
Network | L3 | IPv6, or non-IP data delivery | navy
Radio | L1-2 | NB-IoT, band 20 | grey
side: Secured end to end | 1-3 | red
side: Operator's network | 5-6 | grey
```
````

```stack
Application | L7 | LwM2M objects: temperature, battery, firmware | green
Session | L5-6 | CoAP, with block-wise transfer for firmware | blue
Security | | DTLS 1.2, certificates in the secure element | red
Transport | L4 | UDP | navy
Network | L3 | IPv6, or non-IP data delivery | navy
Radio | L1-2 | NB-IoT, band 20 | grey
side: Secured end to end | 1-3 | red
side: Operator's network | 5-6 | grey
```

## `target`

Rings from the core outwards, each with a callout.

````markdown
```target
Domain | Readings, nodes, sites and their rules | navy
Use cases | Commission, alarm, update, report | blue
Adapters | CoAP listener, REST API, MQTT, SQL | green
Infrastructure | Kubernetes, TimescaleDB, the operator's network | grey
```
````

```target
Domain | Readings, nodes, sites and their rules | navy
Use cases | Commission, alarm, update, report | blue
Adapters | CoAP listener, REST API, MQTT, SQL | green
Infrastructure | Kubernetes, TimescaleDB, the operator's network | grey
```

## `onion`

Nested layers, each inside the last.

````markdown
```onion
Cell | Lithium thionyl chloride, 2.4 Ah | amber
Board | Sensor, controller and radio | green
Potting | Over the cell and the radio | grey
Enclosure | IP65 polycarbonate | blue
Wall plate | Steel, four screws | navy
```
````

```onion
Cell | Lithium thionyl chloride, 2.4 Ah | amber
Board | Sensor, controller and radio | green
Potting | Over the cell and the radio | grey
Enclosure | IP65 polycarbonate | blue
Wall plate | Steel, four screws | navy
```

## `iceberg`

What shows above the waterline and the larger body below it.

````markdown
```iceberg waterline="What the customer sees"
above: A reading on the dashboard
above: An alarm by e-mail
below: Device management and LwM2M
below: Certificates and key rotation
below: The power budget of every message
below: Over-the-air updates with roll-back
below: Operator contracts and roaming
below: Returns, root causes and fixes
```
````

```iceberg waterline="What the customer sees"
above: A reading on the dashboard
above: An alarm by e-mail
below: Device management and LwM2M
below: Certificates and key rotation
below: The power budget of every message
below: Over-the-air updates with roll-back
below: Operator contracts and roaming
below: Returns, root causes and fixes
```

## `cutaway`: sphere

Shells from the core, shown in a quarter cut out of the sphere.

````markdown
```cutaway type=sphere unit=" km"
Inner core | 1220 | Solid iron and nickel, 5,400 °C | amber
Outer core | 3480 | Liquid iron: the magnetic field | red
Lower mantle | 5700 | Solid rock under pressure | brown
Upper mantle | 6340 | Slowly flowing rock | navy
Crust | 6371 | 5 to 70 km thick | green
```
````

```cutaway type=sphere unit=" km"
Inner core | 1220 | Solid iron and nickel, 5,400 °C | amber
Outer core | 3480 | Liquid iron: the magnetic field | red
Lower mantle | 5700 | Solid rock under pressure | brown
Upper mantle | 6340 | Slowly flowing rock | navy
Crust | 6371 | 5 to 70 km thick | green
```

## `cutaway`: column

Bands of altitude with their edges marked; `direction=down` measures depth instead.

````markdown
```cutaway type=column unit=" km"
0 | 12 | Troposphere | Weather, aircraft | blue
12 | 50 | Stratosphere | Ozone layer, balloons | navy
50 | 85 | Mesosphere | Meteors burn up | green
85 | 120 | Thermosphere | Aurora starts here | amber
```
````

```cutaway type=column unit=" km"
0 | 12 | Troposphere | Weather, aircraft | blue
12 | 50 | Stratosphere | Ozone layer, balloons | navy
50 | 85 | Mesosphere | Meteors burn up | green
85 | 120 | Thermosphere | Aurora starts here | amber
```
