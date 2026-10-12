---
title: SN-100 Sensor Node
author: A. Writer
version: "1.0"
---

## Why a sensor node

- Sensors speak I2C, the cloud speaks IP
- The node translates and buffers

<!-- notes: Keep this to one minute. -->

## How it works

1. Wake on a timer
1. Read the sensors
1. Publish over MQTT

<!-- notes: Mention that the buffer covers network outages. -->

::: {.pagebreak}
:::

## Data flow

[[CAPTION:Figure]] From sensor to cloud
```dot
digraph flow {
  rankdir=LR;
  Sensors -> Device -> Cloud;
}
```

## Next steps

[[CAPTION:Table]] Next steps

| Step | Owner |
|---|---|
| Confirm buffer size | Firmware |
| Write test plan | Test |
