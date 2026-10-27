---
title: py-doc diagram gallery
subtitle: Every diagram and block py-doc draws, with the Markdown that draws it
author: Mark Bacon
version: "0.1"
status: Draft
document_number: PD-DG-001
description: One worked example of every diagram type and poster block, each shown as its Markdown and as the picture it makes.
keywords: [py-doc, diagrams, Mermaid, PlantUML, Graphviz, Vega-Lite, poster blocks]
---

# Introduction

This gallery shows every kind of diagram py-doc draws. Each example is the Markdown you write, in a grey block, followed by the picture that Markdown makes. Copy the Markdown into a document, a slide deck, a poster or a site page and it draws the same picture there.

The examples come from one made-up product, the SN-100 sensor node, so they read as the diagrams of a real project rather than as tests.

## How a diagram is written

A diagram is a fenced code block whose language names the diagram type. Options follow the name on the same line:

````markdown
```gauge value=49.93 min=48.5 max=51.5 unit=" Hz" label="Grid frequency"
48.5 | 49.8 | amber
49.8 | 50.2 | green
50.2 | 51.5 | amber
```
````

- **Diagram tools.** Mermaid, PlantUML, Graphviz, ditaa, the blockdiag family, WaveDrom, bytefield-svg, Pikchr, railroad, WireViz, Vega and Vega-Lite run in the tool container. The fence is the tool's own language.
- **Poster blocks.** Charts, scales, shapes, engineering notations, science blocks, pictures and codes are drawn by py-doc itself, from short `label | value | detail | colour` lines.
- **Science fences.** The eleven scientific diagrams, from `molecule` to `thermo-cycle`, are drawn by the optional science image. It is built with `py-doc tools build --science`, or the first time a document uses one.

## Where they work

Every type in this gallery works in every output:

| Output | How it is drawn |
|---|---|
| Word, PowerPoint and PDF | A picture, PNG at 192 dpi, shrunk to the page or slide |
| HTML documents and sites | SVG where the tool writes it, else PNG |
| HTML decks | The blocks as they are on a poster, with sharp text, and diagrams as SVG |
| Posters | In the poster's theme: the blocks natively, the diagrams as SVG |

In documents and sites, the blocks are drawn in the `print` theme, which suits a white page. `diagrams.theme` in `py-doc.yml` names another. A colour in a block is a theme colour, such as `primary` or `accent`, a palette name (`navy`, `blue`, `amber`, `brown`, `red`, `grey` and `green` in every theme), or a CSS colour.

## The chapters

1. **Graphviz, ditaa, blockdiag and Pikchr**: graphs, ASCII art, block, sequence, network, packet and rack diagrams.
2. **Mermaid**: all of its kinds, from flowcharts to Wardley maps.
3. **PlantUML**: every Unified Modeling Language (UML) diagram, and its other kinds, from Gantt charts to regular expressions.
4. **Charts and plots**: `chart`, every `plot` type, Vega-Lite and Vega.
5. **Scales, measures and proportions**: gauges, thresholds, spectra, sizes and amounts.
6. **Processes, plans and comparisons**: flows, steps, timelines, cards and comparisons.
7. **Safety and systems engineering**: fault trees, bow-ties, Goal Structuring Notation (GSN), N² charts, Integration Definition for Function Modelling (IDEF0), value streams and structograms.
8. **Concept shapes**: pyramids, stacks, rings, icebergs and cut-aways.
9. **Electronics, embedded and code**: circuits, timing, wiring, pinouts, instruments, memory, logic and code.
10. **Science, maths, music and games**: equations, astronomy, physics, chemistry, biology, music and chess.
11. **Pictures, QR codes and barcodes**.

`py-doc diagram --list` lists every type, and `py-doc diagram --help-type NAME` shows the syntax of one. The [user guide](../guide/03_writing.md#diagrams) has the options of each.
