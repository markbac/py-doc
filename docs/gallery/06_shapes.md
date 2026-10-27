# Concept shapes

Shapes that carry an idea: layers, levels, parts and proportions.

## `pyramid`

Tiers from the top, labelled inside with detail beside.

````markdown
```pyramid
End-to-end | 5 % | Real network and hardware | red
Hardware in the loop | 20 % | Automated rig, RF attenuators | amber
Integration | 25 % | Simulated peripherals | blue
Unit tests | 50 % | Off target, under a second | green
```
````

```pyramid
End-to-end | 5 % | Real network and hardware | red
Hardware in the loop | 20 % | Automated rig, RF attenuators | amber
Integration | 25 % | Simulated peripherals | blue
Unit tests | 50 % | Off target, under a second | green
```

## `cone`

Tiers as a cone, widest at the top.

````markdown
```cone
Ideas | 400 | Every request | blue
Scoped | 120 | Fits the plan | navy
Built | 30 | Shipped | green
```
````

```cone
Ideas | 400 | Every request | blue
Scoped | 120 | Fits the plan | navy
Built | 30 | Shipped | green
```

## `stack`

A layer stack, such as a protocol stack.

````markdown
```stack
Application | L7 | LwM2M objects | green
Transport | L4 | CoAP over DTLS | blue
Network | L3 | IPv6 or NIDD | navy
Radio | L1-2 | NB-IoT | grey
side: Secured | 2-2 | red
```
````

```stack
Application | L7 | LwM2M objects | green
Transport | L4 | CoAP over DTLS | blue
Network | L3 | IPv6 or NIDD | navy
Radio | L1-2 | NB-IoT | grey
side: Secured | 2-2 | red
```

## `target`

Rings around a centre, from the inside out.

````markdown
```target
Domain | Entities and rules | navy
Use cases | What the system does | blue
Adapters | Controllers and gateways | green
Infrastructure | Database and network | grey
```
````

```target
Domain | Entities and rules | navy
Use cases | What the system does | blue
Adapters | Controllers and gateways | green
Infrastructure | Database and network | grey
```

## `onion`

Nested layers, each inside the last.

````markdown
```onion
Cell | Lithium, 2.4 Ah | amber
Board | Sensor, controller and radio | blue
Case | IP65, wall mount | grey
```
````

```onion
Cell | Lithium, 2.4 Ah | amber
Board | Sensor, controller and radio | blue
Case | IP65, wall mount | grey
```

## `iceberg`

What shows above the line and what lies below.

````markdown
```iceberg waterline="What the customer sees"
above: The app
below: Device management
below: Security and keys
below: Power budget
below: Firmware updates
```
````

```iceberg waterline="What the customer sees"
above: The app
below: Device management
below: Security and keys
below: Power budget
below: Firmware updates
```

## `ring`

Parts of a whole around a ring.

````markdown
```ring cells=16
fill: 3-9 | Waiting samples | blue
pointer: 3 | TAIL (read) | green
pointer: 10 | HEAD (write) | red
```
````

```ring cells=16
fill: 3-9 | Waiting samples | blue
pointer: 3 | TAIL (read) | green
pointer: 10 | HEAD (write) | red
```

## `vessels`

Containers filled to their levels.

````markdown
```vessels
Espresso | 30 ml Espresso (amber)
Cortado | 30 ml Espresso (amber) + 30 ml Milk (#f3e3c3)
Flat white | 60 ml Ristretto (amber) + 120 ml Microfoam (#f3e3c3)
```
````

```vessels
Espresso | 30 ml Espresso (amber)
Cortado | 30 ml Espresso (amber) + 30 ml Milk (#f3e3c3)
Flat white | 60 ml Ristretto (amber) + 120 ml Microfoam (#f3e3c3)
```

## `balance`

Two sides weighed on a balance.

````markdown
```balance unit=" GW"
left: Generation | 52 | green
right: Demand | 50 | red
right: Losses | 1.5 | grey
```
````

```balance unit=" GW"
left: Generation | 52 | green
right: Demand | 50 | red
right: Losses | 1.5 | grey
```

## `cutaway`

A cut-away of layers with their labels.

````markdown
```cutaway type=sphere unit=" R☉"
Core | 0.25 | 15 million K | amber
Radiative zone | 0.7 | Light takes 170,000 years | red
Convective zone | 1 | Rising plasma | brown
```
````

```cutaway type=sphere unit=" R☉"
Core | 0.25 | 15 million K | amber
Radiative zone | 0.7 | Light takes 170,000 years | red
Convective zone | 1 | Rising plasma | brown
```

## `zoom-chain`

Zooming in, step by step, from the whole to a detail.

````markdown
```zoom-chain
images/mount-wall.svg | The wall | | 40%, 30%, 30%, 40%
images/mount-pipe.svg | The bracket | 4× | 30%, 30%, 40%, 40%
images/mount-ceiling.svg | The node | 10× |
```
````

```zoom-chain
images/mount-wall.svg | The wall | | 40%, 30%, 30%, 40%
images/mount-pipe.svg | The bracket | 4× | 30%, 30%, 40%, 40%
images/mount-ceiling.svg | The node | 10× |
```
