---
title: Posters
---

# Posters

`py-doc poster` turns one Markdown file into one self-contained HTML poster: a header, a strip of figures, an introduction, two columns of sections and a summary. Pictures, diagrams and styles are all inside the page, so it can be sent or printed on its own.

```bash
py-doc poster g460.md                 # writes g460.html
py-doc poster g460.md -o out.html
```

A poster is not a document of `py-doc.yml`, but when the Markdown file is in a project, its `runtime` settings are used to draw the diagrams.

## Page structure

The front matter keys are `title`, `subtitle`, `byline`, `footer-left`, `footer-right`, `paper` (`a0` to `a4`, default `a1`, used for printing), `width` (the smallest layout width in pixels, default 1400) and `split` (the number of sections in the left column, default balanced by length).

| Heading | Becomes |
|---|---|
| `## Stats` | A table of value and label, shown as the strip of figures (the header row is ignored) |
| `## Abstract` | The blue introduction box |
| `## 1. Heading: accent` | A section. The text after the first colon is coloured |
| `## Summary` | The first paragraph is the banner, and each `###` is a block |

Section bodies are ordinary Markdown. A paragraph starting `Fig.` is a caption. Local pictures (`![alt](file.svg)`) are embedded. A quote (`> text`) is an amber callout.

## Diagram fences

Every diagram fence of a document works on a poster, drawn by the tool container and embedded as a PNG picture. Mermaid gets a theme that matches the poster unless the diagram has its own `%%{init`. A diagram that cannot be drawn is shown as code with a warning, and the poster is still written.

> **Note:** A diagram wider than the column (about 660 pixels) is scaled down and its text shrinks, so prefer compact layouts, such as Graphviz `dpi=80` or PlantUML `skinparam dpi 80`.

## Poster blocks

The colours are `navy`, `blue`, `amber`, `brown`, `red`, `grey` and `green`, or a hex value.

| Fence | Lines | Options |
|---|---|---|
| `cards` | `Heading \| Text \| colour`, the colour only for the `top` style | `cols=2`, `style=` `title` (default), `label`, `top` or `plain` |
| `lcd` | Screens separated by blank lines. A line starting `--` is the caption | |
| `segments` | `weight \| label \| detail \| colour`, and an optional `title:` and `height:` | |
| `flow` | `[Filled\|colour]` or `[Outlined]` boxes, joined by `->` or `-label->` arrows | |
| `lanes` | `Label \| *filled cell \| dashed cell` | |
| `figure` | Several of `segments`, `flow` and `lanes` in one box, split by `+++` lines, each starting `@segments`, `@flow` or `@lanes` | |

In `segments`, `flow` and `lanes`, the lines that are not part of the diagram become notes under it, written in Markdown.

````markdown
```flow
[OPEN|navy] -closure reason raised-> [CLOSED|red]
```

```lcd
C 0012.340m3
Gas ON
-- Credit, supply on
```
````

## Proportions and printing

The poster always has the proportions of A paper (1 : 1.4142). A script in the page finds the narrowest layout, no narrower than `width`, at which all the content fits, then scales the poster to the browser window. Adding or removing content needs no change of size.

To print, use the print dialogue of Chrome with no margins and background graphics on. The page size comes from `paper`, and the poster fills exactly one page. Text and shapes stay vector, and diagrams are PNG.
