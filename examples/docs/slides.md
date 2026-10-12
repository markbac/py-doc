---
title: Meter Gateway
author: A. Writer
version: "1.0"
---

## Why a gateway

- Meters speak serial, the head-end speaks IP
- The gateway translates and buffers

<!-- notes: Keep this to one minute. -->

## How it works

1. Read the meter
1. Buffer the reading
1. Send it over LwM2M

::: {.pagebreak}
:::

## Next steps

| Step | Owner |
|---|---|
| Confirm buffer size | Firmware |
| Write test plan | Test |
