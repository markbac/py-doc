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

A rich table holds paragraphs, lists, merged cells and diagrams in its cells. `<br>` starts a new paragraph, `- ` a bullet and `1. ` a numbered item, and two spaces put an item inside the one above. A cell of `<` joins the cell on its left, and `^` the cell above.

[[CAPTION:Table]] Commissioning steps

[[LISTTABLE: header, widths=8,52,40]]
| Step | What to do | Check |
| 1 | [Prepare the node:]{.underline}<br>Fit the batteries and close the enclosure.<br>Before you go to site:<br>- The firmware is version {{version}}<br>- The node is registered on the broker<br>  - with its own client certificate | The light flashes green once. |
| 2 | Pair the node over Bluetooth:<br>1. Hold the button for five seconds.<br>2. Choose the node in the app. | ^ |
| 3 | The first reading goes this way:<br>[[BLOCK: reading]] | < |
| 4 | [Report a node that publishes nothing to support.]{custom-style="Highlight Yellow"} | < |

[[BLOCK: reading]]
```dot
digraph reading {
  rankdir=LR;
  node [shape=box, style=rounded];
  Sensor -> Gateway -> Broker -> Dashboard;
}
```
[[ENDBLOCK]]

## Glossary

[[INCLUDE: ../includes/glossary.md]]

> [!IMPORTANT]
> Always check the version before updating. An update to the wrong version cannot be undone.

[[PAGEBREAK]]

## Contacts

[[INCLUDE: ../includes/support.md]]
