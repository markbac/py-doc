---
title: Writing a slide deck
---

# Writing a slide deck

This chapter walks through writing a PowerPoint deck in Markdown, from planning the talk to a deck in the company template. It shows how headings become slides, how to lay out each kind of slide, and how to keep speaker notes beside the slides. [Outputs](04_outputs.md#powerpoint) is the reference for the PowerPoint settings.

A deck written in Markdown is quick to change, reviewed like any text, and shares diagrams, includes and variables with the documents. PowerPoint's own tools are better for a deck that is mostly pictures and animation. py-doc suits the decks engineers give: designs, reviews, plans and training.

## Plan the talk

Answer three questions before the first slide:

1. **What should the audience know or do at the end?** Write it as one sentence. The last slide says it again.
1. **How long is the talk?** Plan about one slide for every one or two minutes, so 10 to 15 slides for 20 minutes.
1. **What are the sections?** Three to five sections, each a part of the story, such as the problem, the design, the plan.

## Start the deck

Write a Markdown file with front matter, then build it:

```markdown
---
title: SN-100 Sensor Node
subtitle: Architecture and operation
author: A. Writer
date: 2026-10-20
version: "1.0"
---

# Introduction

## Why a sensor node

- Sensors speak I2C, the cloud speaks IP
- The node translates and buffers
```

```bash
py-doc slides talk.md -o talk.pptx
py-doc slides talk.md -t templates/Company.pptx      # in the company template
```

In a project, list it in `py-doc.yml` with a `pptx` output, and `py-doc build deck` builds it with the rest. `examples/docs/deck/slides.md` is a deck that uses every feature in this chapter.

## Headings make the slides

The front matter makes the title slide: the title, subtitle, author and date. After that:

| You write | It becomes |
|---|---|
| `# Introduction` | A section slide, in the Section Header layout |
| `## Why a sensor node` | A slide with that title, in the Title and Content layout |
| `[[PAGEBREAK]]` | A new slide without a title, for a picture or a quote |

A slide starts at each heading down to the `split_level`, which is 2 by default. With `--split-level 1`, every `#` heading is a slide and there are no section slides. Use the default unless the deck is short.

Write a slide title as the point the slide makes, not its topic. "Battery life is three years" says more than "Battery".

## One idea for each slide

Put one idea on a slide, with three to five bullets of a few words each. The audience reads a slide while you talk, so a slide with paragraphs competes with you.

```markdown
## Battery life is three years

- One 2400 mAh cell
- 90 uA on average
- Asleep 99 % of the time
```

py-doc warns about a slide of more than 16 lines, because it is too full to read, and nothing is shrunk to fit. Split it into two slides, or move detail to the speaker notes.

Bullets nest one level below another with two spaces. Use it for detail that belongs to one bullet, not for a second list.

## Two columns

Put two things side by side in a `columns` block, which uses the Two Content layout:

```markdown
## Before and after

:::: columns
::: column
**Before**

- Readings kept on the node
- Pulled by a gateway
:::
::: column
**After**

- Readings published over MQTT
- Pushed to the cloud
:::
::::
```

Use it to compare two options, or for text beside a picture.

## Pictures and diagrams

A picture or a diagram sits on its slide on its own, with its caption under it:

````markdown
## How a reading travels

[[CAPTION:Figure]] From sensor to cloud
```mermaid
flowchart LR
  Sensor --> Node --> Gateway --> Cloud
```
````

Draw diagrams in the Markdown, so they change with the design and match the documents. Keep a diagram on a slide simpler than one in a document: five to eight boxes, with labels the back row can read. A picture is `![What it shows](images/board.png)`, with alt text that says what it shows.

## Build a list one point at a time

An `incremental` block shows its points one at a time, one for each click:

```markdown
## How it works

::: incremental
1. Wake on a timer
1. Read the sensors
1. Publish over MQTT
:::
```

Use it when the order matters, or to stop the audience reading ahead. Do not use it on every slide.

## Speaker notes

Notes go to the notes page of the slide, for you and not the audience. A short note is an HTML comment, and a longer one is a `notes` block:

```markdown
<!-- notes: Keep this to one minute. The buffer is the main reason for the design. -->

::: notes
Each step appears on a click.

Ask who has replaced a battery in the field.
:::
```

Put the detail you would say in the notes, and keep the slide to its headline points.

## Tables, code and maths

A table works on a slide when it is small: four or five rows of two or three columns. A larger table belongs in a handout or the document.

Code is shown in a fixed-width font. Show only the lines you talk about, or include a short file with `[[INCLUDE-CODE: file.c]]`. Maths in `$...$` and `$$...$$` is typeset.

## Callouts

`> [!TIP]` and `> **Note:**` callouts work on slides. Use one for a warning the audience must remember, and not as decoration.

## Reuse and variants

A deck takes the same includes, conditions and variables as a document:

```markdown
[[INCLUDE: ../includes/audience.md]]

[[IF: internal]]
## Internal only

Field trial results, not for release.
[[ENDIF]]

This is version {{version}} of the deck.
```

So one source makes an internal and a customer deck, with `--condition internal=true` for the internal one.

## The template

The company template decides the fonts, colours, logo and layouts. py-doc uses the layouts by their standard names, such as Title Slide, Title and Content, Section Header and Two Content. So a template must start from pandoc's own reference deck, changed in PowerPoint:

```bash
py-doc init --templates                       # writes pandoc's reference documents to start from
py-doc template check templates/Company.pptx  # what the template lacks
```

`footer: "{title} v{version}"` under the `pptx` output puts the title and version in the footer of every slide. `{{VERSION}}` in a shape of the template is replaced by the version.

```yaml
documents:
  deck:
    sources: [docs/deck/slides.md]
    outputs:
      pptx: {template: templates/Company.pptx, footer: "{title} v{version}"}
```

## Before you present

1. Read only the slide titles. Do they tell the story on their own?
1. Check that no slide has a warning for being too long.
1. Read every diagram from the back of a room, or from a laptop at arm's length.
1. Read the speaker notes aloud once, against the clock.
1. Check the footer shows the right version.

## When something goes wrong

| Message or symptom | Cause and fix |
|---|---|
| A slide of more than 16 lines | Split it, or move the detail to the notes |
| The template gives an empty deck | The template was not made from pandoc's reference deck. Start from `py-doc init --templates` |
| A layout without a footer placeholder | The `footer` setting needs a footer placeholder in each layout. Add one in the slide master |
