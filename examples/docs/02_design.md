# Design

## Components

The gateway has three parts: a reader, a buffer and an uplink.

```dot
digraph gateway {
  rankdir=LR;
  node [shape=box, style=rounded];
  Meter -> Reader -> Buffer -> Uplink -> "Head-end";
}
```

[[CAPTION:Figure]] Data flow through the gateway

## Sequence

```mermaid
sequenceDiagram
    participant R as Reader
    participant B as Buffer
    participant U as Uplink
    R->>B: reading
    B->>U: batch of readings
    U-->>B: acknowledged
```

## Deployment sketch

```plantuml
@startuml
node "Gateway" {
  [Reader] --> [Buffer]
  [Buffer] --> [Uplink]
}
cloud "Head-end" as HE
[Uplink] --> HE : LwM2M over DTLS
@enduml
```

## Code

The reader loop, included from a file:

[[INCLUDE-CODE: includes/reader.c]]

## A wide table

[[LANDSCAPE]]

| Register | Address | Width | Description | Access | Reset |
|---|---|---|---|---|---|
| ENERGY | 0x0100 | 32 | Total active energy | R | 0 |
| POWER | 0x0104 | 32 | Instantaneous power | R | 0 |
| STATUS | 0x0108 | 16 | Meter status bits | R | 0 |

[[PORTRAIT]]
