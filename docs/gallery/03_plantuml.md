# PlantUML

[PlantUML](https://plantuml.com) draws every UML diagram and many others from text between `@startuml` and `@enduml`, or the `@start` line of its kind, such as `@startmindmap`. The tool image has PlantUML 1.2025.4. `puml` is the same fence.

## Sequence diagram

Participants of each kind, groups, activations, delays and dividers.

```plantuml
@startuml
actor Installer
participant "Installer app" as App
participant "API" as API
database "Nodes" as DB
participant "Ingest" as Ingest
entity "Sensor node" as Node

Installer -> App : Scan the QR code
activate App
App -> API : POST /nodes {devEui, room}
activate API
API -> DB : INSERT node
API --> App : 201 Created
deactivate API
== Power on ==
Node -> Ingest : First reading (CoAP)
activate Ingest
Ingest -> API : node 42 is live
deactivate Ingest
API -> App : Push: live
App --> Installer : Shows a green tick
deactivate App
... 15 minutes later ...
group Normal running
  Node -> Ingest : Reading
end
@enduml
```

## Use case diagram

Actors, use cases in a system, and include and extend.

```plantuml
@startuml
left to right direction
actor Installer
actor "Site manager" as Manager
actor "Mobile operator" as Operator <<system>>
rectangle "SN-100 platform" {
  usecase "Commission a node" as UC1
  usecase "Scan the QR code" as UC2
  usecase "Watch the rooms" as UC3
  usecase "Acknowledge an alarm" as UC4
  usecase "Update firmware" as UC5
}
Installer --> UC1
UC1 .> UC2 : <<include>>
Manager --> UC3
UC4 .> UC3 : <<extend>>
Manager --> UC4
Operator --> UC5
@enduml
```

## Class diagram

Classes, interfaces, enums, packages and their relationships.

```plantuml
@startuml
package "Device model" {
  abstract class Device {
    +devEui : String
    +firmware : String
    #batteryMv : int
    +wake()
    +sleep(seconds : int)
  }
  class SensorNode {
    -threshold : float
    +measure() : Reading
  }
  class Gateway {
    +forward(r : Reading) : bool
  }
  interface Sensor {
    +read() : Reading
  }
  enum RadioState {
    ASLEEP
    ATTACHING
    CONNECTED
  }
}
class Reading <<value>> {
  +celsius : float
  +humidity : float
  +at : DateTime
}
Device <|-- SensorNode
Device <|-- Gateway
Gateway "1" o-- "0..200" SensorNode
SensorNode *-- Sensor
SensorNode --> RadioState
Sensor ..> Reading : makes
@enduml
```

## Object diagram

Objects and the values of their fields at one moment.

```plantuml
@startuml
object "leeds : Site" as site {
  postcode = "LS1 4AP"
}
object "gw1 : Gateway" as gw {
  firmware = "1.5.2"
}
object "node42 : SensorNode" as n42 {
  devEui = "70B3D57ED0051A2C"
  batteryMv = 3540
}
object "node43 : SensorNode" as n43 {
  devEui = "70B3D57ED0051A2D"
  batteryMv = 2380
}
map "Last reading" as last {
  celsius => 21.4
  humidity => 48
}
site --> gw
gw --> n42
gw --> n43
n42 --> last
@enduml
```

## Activity diagram

Actions, decisions, loops, forks and swim lanes.

```plantuml
@startuml
|Node|
start
:Wake on the timer;
:Read the sensor;
if (Changed?) then (yes)
  |Radio|
  :Attach to the network;
  repeat
    :Send the reading;
  repeat while (Acknowledged?) is (no) not (yes)
else (no)
  |Node|
  :Count the skip;
endif
|Node|
fork
  :Write the log;
fork again
  :Check the battery;
end fork
:Sleep;
stop
@enduml
```

## Component diagram

Components, interfaces, ports and the dependencies between them.

```plantuml
@startuml
package "Ingest" {
  [CoAP listener] as listener
  [Decoder] as decoder
  [Validator] as validator
  [Publisher] as publisher
  port "5684/udp" as coap
}
cloud "NB-IoT" as net
queue "MQTT broker" as broker
interface "CoAP" as icoap
net --> icoap
icoap - coap
coap --> listener
listener --> decoder
decoder --> validator
validator --> publisher
publisher --> broker : MQTT
@enduml
```

## Deployment diagram

Nodes, devices, artefacts and the links between them.

```plantuml
@startuml
node "Customer site" {
  node "SN-100 node" <<device>> {
    artifact "firmware-2.1.bin"
  }
}
cloud "Mobile operator" {
  node "NB-IoT cell" as cell
}
node "eu-west-2" <<cloud>> {
  node "Kubernetes" {
    component "Ingest x3" as ingest
    component "API x2" as api
  }
  database "TimescaleDB" as db
}
"SN-100 node" -- cell : NB-IoT
cell -- ingest : CoAP over DTLS
ingest --> db
api --> db
@enduml
```

## State diagram

States, composite states, choices and concurrent regions.

```plantuml
@startuml
[*] --> Provisioned
Provisioned --> Joining : power on
Joining --> Backoff : no answer
Backoff --> Joining : wait doubles
Joining --> Running : join accept
state Running {
  state Measure
  state Send
  [*] --> Asleep
  Asleep --> Measure : timer
  state changed <<choice>>
  Measure --> changed
  changed --> Send : [changed]
  changed --> Asleep : [unchanged]
  Send --> Asleep
  --
  [*] --> Watching
  Watching --> Alarm : battery < 2.4 V
}
Running --> Updating : firmware offered
Updating --> Running
@enduml
```

## Timing diagram

Robust and concise signals, clocks and binary lines, over time.

```plantuml
@startuml
scale 10 as 50 pixels
clock "RTC" as rtc with period 20
binary "Sensor power" as pwr
concise "Controller" as cpu
robust "Radio" as radio

@0
cpu is Asleep
radio is Off
pwr is low

@20
cpu is Measuring
pwr is high

@30
pwr is low
cpu is Sending
radio is Attaching

@50
radio is Connected

@70
radio is Off
cpu is Asleep
@enduml
```

## Entity relationship diagram

Entities with keys, in information engineering notation.

```plantuml
@startuml
hide circle
skinparam linetype ortho
entity Site {
  * id : int <<PK>>
  --
  name : text
  postcode : text
}
entity Node {
  * dev_eui : text <<PK>>
  --
  * site_id : int <<FK>>
  firmware : text
  battery_mv : int
}
entity Reading {
  * id : bigint <<PK>>
  --
  * dev_eui : text <<FK>>
  at : timestamptz
  celsius : real
}
Site ||--o{ Node
Node ||--o{ Reading
@enduml
```

## Chen ER diagram

Entities, relationships and attributes in Chen's notation.

```plantuml
@startchen
entity SITE {
  Id <<key>>
  Name
  Postcode
}
entity NODE {
  DevEui <<key>>
  Firmware
  Battery
}
entity READING <<weak>> {
  At <<key>>
  Celsius
}
relationship HOLDS {
}
relationship SENDS <<identifying>> {
}
SITE -1- HOLDS
HOLDS -N- NODE
NODE -1- SENDS
SENDS =N= READING
@endchen
```

## Network diagram

Networks, the nodes on each and their addresses, in nwdiag form.

```plantuml
@startuml
nwdiag {
  internet [shape = cloud];
  internet -- firewall;
  network dmz {
    address = "10.0.1.0/24"
    firewall [address = "10.0.1.1"];
    gateway [address = "10.0.1.10", description = "SN-100 gateway"];
  }
  network plant {
    address = "10.0.2.0/24"
    gateway [address = "10.0.2.1"];
    bms [address = "10.0.2.20", description = "Building management"];
    logger [address = "10.0.2.30"];
  }
}
@enduml
```

## Wireframe (Salt)

A user interface sketched from text.

```plantuml
@startsalt
{+
  <b>Commission a node
  ==
  Node ID   | "70B3D57ED0051A2C"
  Site      | ^Leeds, Wellington Place^
  Room      | "Plant room       "
  Interval  | ^15 minutes^
  [X] Send only changes
  [ ] Low-battery alarms by e-mail
  ==
  [Cancel] | [  Save and join  ]
}
@endsalt
```

## ArchiMate

Enterprise architecture layers with ArchiMate elements.

```plantuml
@startuml
!include <archimate/Archimate>
Business_Actor(manager, "Facilities manager")
Business_Service(comfort, "Room comfort reporting")
Application_Component(dash, "Dashboard")
Application_Service(api, "Readings API")
Technology_Node(cloud, "Cloud cluster")
Technology_Device(node, "SN-100 node")
Rel_Serving(comfort, manager)
Rel_Realization(dash, comfort)
Rel_Serving(api, dash)
Rel_Realization(cloud, api)
Rel_Flow(node, cloud, "Readings")
@enduml
```

## C4 with the PlantUML standard library

C4 diagrams from the C4-PlantUML macros that ship with PlantUML.

```plantuml
@startuml
!include <C4/C4_Container>
LAYOUT_LEFT_RIGHT()
Person(manager, "Site manager", "Watches the rooms")
System_Boundary(sn, "SN-100 platform") {
  Container(web, "Dashboard", "React", "Rooms, trends and alarms")
  Container(api, "API", "FastAPI", "Sites, nodes, readings")
  ContainerDb(db, "Readings", "TimescaleDB")
  Container(ingest, "Ingest", "Go", "Decodes CoAP")
}
System_Ext(nodes, "Sensor nodes", "NB-IoT")
Rel(manager, web, "Uses", "HTTPS")
Rel(web, api, "Calls", "JSON")
Rel(api, db, "Reads", "SQL")
Rel(nodes, ingest, "Send readings", "CoAP")
Rel(ingest, db, "Writes", "SQL")
SHOW_LEGEND()
@enduml
```

## Gantt chart

Tasks with durations, dependencies, milestones and closed days.

```plantuml
@startgantt
Project starts 2026-01-05
saturday are closed
sunday are closed
-- Firmware --
[Delta encoding] requires 15 days
[Channel memory] requires 10 days
[Channel memory] starts at [Delta encoding]'s end
[Code freeze] happens at [Channel memory]'s end
-- Test --
[Rig regression] requires 8 days
[Rig regression] starts at [Code freeze]'s end
[Field pilot] requires 20 days and is colored in #f3c6c0
[Field pilot] starts at [Rig regression]'s end
-- Release --
[Staged roll-out] requires 10 days
[Staged roll-out] starts at [Field pilot]'s end
[General availability] happens at [Staged roll-out]'s end
@endgantt
```

## Mind map

Ideas on both sides of a root.

```plantuml
@startmindmap
* Battery life
** Sleep
*** 2 µA sleep current
*** RTC wake only
** Radio
*** PSM and eDRX
*** Send only changes
left side
** Cell
*** Lithium thionyl chloride
*** Passivation on cold starts
** Firmware
*** No busy waits
*** Batched flash writes
@endmindmap
```

## Work breakdown structure

The parts of a project as a tree.

```plantuml
@startwbs
* SN-100 release 2.1
** Firmware
*** Delta encoding
*** Channel memory
*** RTC drift fix
** Test
*** Rig regression
*** Field pilot
**** Leeds, 120 nodes
**** Bristol, 80 nodes
** Documentation
*** Release notes
*** Installer guide
** Roll-out
*** Staged update
*** Support briefing
@endwbs
```

## JSON

The structure of a JSON document, with parts highlighted.

```plantuml
@startjson
#highlight "readings" / "0"
{
  "devEui": "70B3D57ED0051A2C",
  "site": "leeds",
  "firmware": "2.1.0",
  "battery": {"mv": 3540, "low": false},
  "readings": [
    {"at": "2026-10-27T09:00:00Z", "celsius": 21.4, "rh": 48},
    {"at": "2026-10-27T09:15:00Z", "celsius": 21.6, "rh": 47}
  ]
}
@endjson
```

## YAML

The structure of a YAML document.

```plantuml
@startyaml
node:
  devEui: 70B3D57ED0051A2C
  interval: 15 min
  threshold:
    celsius: 0.2
    rh: 2
  radio:
    band: 20
    psm: true
    edrx: 81.92 s
  alarms:
    - battery-low
    - tamper
@endyaml
```

## EBNF

A grammar drawn as railroad tracks.

```plantuml
@startebnf
command = verb, " ", target, { " ", option };
verb = "get" | "set" | "reset";
target = "interval" | "threshold" | "radio";
option = "--", name, [ "=", value ];
@endebnf
```

## Regular expression

A regular expression drawn as a railroad diagram.

```plantuml
@startregex
title Topic of a reading
sn100/[a-z]+/[0-9]{1,6}/(temp|rh|battery)(/raw)?
@endregex
```

## Chronology

Events on a dated line.

```plantuml
@startchronology
[First board] happens on 2024-07-15 09:00:00
[NB-IoT certified] happens on 2024-11-02 09:00:00
[Pilot, 200 nodes] happens on 2025-04-01 09:00:00
[Firmware 2.0] happens on 2025-10-20 09:00:00
[5,000 nodes] happens on 2026-02-10 09:00:00
[Firmware 2.1] happens on 2026-09-01 09:00:00
@endchronology
```

## Files

A tree of files and folders.

```plantuml
@startfiles
/sn100-firmware/src/main.c
/sn100-firmware/src/radio/bg77.c
/sn100-firmware/src/radio/coap.c
/sn100-firmware/src/sensor/sht40.c
/sn100-firmware/tests/test_coap.c
/sn100-firmware/CMakeLists.txt
/sn100-firmware/README.md
@endfiles
```

## Maths

A formula in AsciiMath or LaTeX.

```plantuml
@startmath
I_"avg" = (I_"sleep" t_"sleep" + I_"tx" t_"tx" + I_"rx" t_"rx") / (t_"sleep" + t_"tx" + t_"rx")
@endmath
```
