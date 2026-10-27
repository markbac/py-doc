# Safety and reliability

The diagrams of safety and reliability cases.

## `fault-tree`

A fault tree with AND and OR gates.

````markdown
```fault-tree
or: Node stops reporting
  and: No power
    basic: Cell flat | 1e-3
    basic: Backup fails | 0.05
  basic: Radio fault | 2e-4
```
````

```fault-tree
or: Node stops reporting
  and: No power
    basic: Cell flat | 1e-3
    basic: Backup fails | 0.05
  basic: Radio fault | 2e-4
```

## `bowtie`

A bow-tie: threats, barriers, the event and its consequences.

````markdown
```bowtie
top: Thermal runaway
threat: Overcharge | Charger cut-off
consequence: Fire | Fire wall
```
````

```bowtie
top: Thermal runaway
threat: Overcharge | Charger cut-off
consequence: Fire | Fire wall
```

## `gsn`

A Goal Structuring Notation argument.

````markdown
```gsn
goal G1: The node is safe to install
  context C1: Indoor use
  solution Sn1: Test report
```
````

```gsn
goal G1: The node is safe to install
  context C1: Indoor use
  solution Sn1: Test report
```
