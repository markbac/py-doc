# Requirements

The gateway shall meet the requirements in the table.

[[CAPTION:Table]] Gateway requirements

[[CAPTION:Table]] Requirements
| ID | Requirement | Priority |
|---|---|---|
| R1 | Read a meter every 15 minutes | Must |
| R2 | Buffer 7 days of readings | Must |
| R3 | Send readings over LwM2M | Must |
| R4 | Update firmware over the air | Should |

## Open points

- Confirm the buffer size with the meter vendor
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
