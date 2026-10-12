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

## Glossary

[[INCLUDE: ../includes/glossary.md]]

> [!IMPORTANT]
> Always check the version before updating. An update to the wrong version cannot be undone.

::: {.pagebreak}
:::

## Contacts

[[INCLUDE: ../includes/support.md]]
