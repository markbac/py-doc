# Requirements

The node shall meet the requirements in the table.

[[CAPTION:Table]] Node requirements

| ID | Requirement | Priority |
|---|---|---|
| R1 | Measure temperature every 5 minutes | Must |
| R2 | Buffer 7 days of readings | Must |
| R3 | Publish readings over MQTT with TLS | Must |
| R4 | Update firmware over the air | Should |
| R5 | Run for 3 years on one battery | Should |

## Open points

- Confirm the buffer size with the flash vendor
  - Flash wear needs checking
  - Compression may help
- Agree the reporting interval

The order of work:

1. First, settle the buffer size.
1. Then, agree the reporting interval.
1. Last, write the test plan.

The review state:

- [x] Requirements reviewed
- [ ] Requirements approved
