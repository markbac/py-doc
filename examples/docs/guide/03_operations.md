---
title: Operations
---

# Operations

The node is {{status_text}}.

[[IF: audience == staff]]
## Staff notes

Staff can reach the console on the service port.
[[ENDIF]]

[[NOT: internal]]
Customers see only the public build.
[[ENDIF]]

[[IF: audience != staff]]
This paragraph is shown to everyone except staff.
[[ENDIF]]

## Commissioning

A rich table holds several paragraphs and a bullet list in a cell. `<br>` starts a new paragraph and `- ` a bullet.

[[CAPTION:Table]] Commissioning steps

[[LISTTABLE: widths=6,94]]
| 1 | [Prepare the node:]{.underline}<br>Fit the batteries and close the enclosure.<br>Check before you go to site:<br>- The firmware is version {{version}}<br>- The node is registered on the broker |
| 2 | Pair the node over Bluetooth:<br>Hold the button for five seconds, until the light flashes blue. |
| 3 | Check the first reading:<br>- The temperature is published within one minute<br>- [Report a node that publishes nothing to support]{custom-style="Highlight Yellow"} |

## Glossary

[[INCLUDE: ../includes/glossary.md]]

> [!IMPORTANT]
> Always check the version before updating. An update to the wrong version cannot be undone.

[[PAGEBREAK]]

## Contacts

[[INCLUDE: ../includes/support.md]]
