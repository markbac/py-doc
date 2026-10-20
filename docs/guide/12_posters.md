---
title: Posters
---

# Posters

`py-doc poster` turns one Markdown file into one self-contained HTML poster: a header, a strip of figures, an introduction, columns of sections and a summary. Pictures, diagrams, the logo and the styles are all inside the page, so it can be sent or printed on its own.

```bash
py-doc poster g460.md                     # writes g460.html
py-doc poster g460.md -o out.html
py-doc poster g460.md --theme dark        # a built-in theme
py-doc poster g460.md --theme brand.yml   # a theme file
```

A poster is not a document of `py-doc.yml`, but when the Markdown file is in a project, its `runtime` settings are used to draw the diagrams and its `poster.theme` is the default theme.

The examples in `examples/poster/` show the three kinds: `poster.md` is portrait with the default theme, `landscape.md` is landscape in the theme of a made-up company, and `release.md` uses the dark theme.

## Page structure

| Heading | Becomes |
|---|---|
| `## Stats` | A table of value and label, shown as the strip of figures (the header row is ignored) |
| `## Abstract` | The introduction box |
| `## 1. Heading: accent` | A section. The text after the first colon is coloured |
| `## Summary` | The first paragraph is the banner, and each `###` is a block |

Section bodies are ordinary Markdown. A paragraph starting `Fig.` is a caption. Local pictures (`![alt](file.svg)`) are embedded. A quote (`> text`) is a callout.

## Front matter

| Key | Default | What it sets |
|---|---|---|
| `title`, `subtitle`, `byline` | The first `#` heading, else the file name | The header |
| `footer-left`, `footer-right` | Empty | The footer |
| `orientation` | `portrait` | `portrait` or `landscape` |
| `columns` | 2 for portrait, 3 for landscape | How many columns the sections are in |
| `split` | Balanced by length | How many sections go in each column but the last, such as `3` for two columns or `2, 3` for three |
| `paper` | `a1` | `a0` to `a4`, the page size for printing |
| `width` | 1400 for portrait, 1800 for landscape | The narrowest layout in pixels. Smaller makes text larger on the page |
| `theme` | `default`, or the project's `poster.theme` | A built-in theme or a theme file, relative to the Markdown file |
| `logo` | The theme's | A picture for the left of the header, relative to the Markdown file |

## Proportions and printing

A portrait poster has the proportions of portrait A paper (1 : 1.4142), and a landscape poster those of landscape A paper (1.4142 : 1). A script in the page finds the narrowest layout, no narrower than `width`, at which all the content fits, then scales the poster to the browser window. Adding or removing content needs no change of size. When a poster has little content there is space above the footer: lower `width` to make everything larger.

To print, use the print dialogue of Chrome with no margins and background graphics on. The page size and its orientation come from `paper` and `orientation`, and the poster fills exactly one page. Text and shapes stay vector, and diagrams are PNG.

## Diagram fences

Every diagram fence of a document works on a poster, drawn by the tool container and embedded as a PNG picture. Mermaid gets the colours and body font of the theme unless the diagram has its own `%%{init`. A diagram that cannot be drawn is shown as code with a warning, and the poster is still written.

> **Note:** A diagram wider than its column is scaled down and its text shrinks, so prefer compact layouts, such as Graphviz `dpi=80` or PlantUML `skinparam dpi 80`.

## Poster blocks

A block colour is a name from the theme's palette (`navy`, `blue`, `amber`, `brown`, `red`, `grey` and `green` in every theme, and the theme's own), a theme colour name such as `primary` or `accent`, or a colour value such as `#2a3150`.

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

## Themes

A theme sets the colours, the fonts, the block palette and the logo. The built-in themes are:

| Theme | What it is |
|---|---|
| `default` | A dark grey header, navy headings and blue boxes on a light page, in Source Serif 4 |
| `dark` | A dark page with amber accents, for screens |
| `print` | A white page and header with light boxes, in fonts every computer has, for printing with less ink |

The theme comes from `--theme` on the command line, else the poster's `theme`, else `poster.theme` in `py-doc.yml`, else `default`. A relative path is from the working folder for `--theme`, from the Markdown file for the front matter, and from `py-doc.yml` for the project.

```yaml
# py-doc.yml: every poster in the project is in the company's colours
poster:
  theme: brand/poster-theme.yml
```

### Theme files

A theme file starts from a built-in theme and changes only what it names. `examples/poster/brand/example-instruments.yml` is a complete one.

```yaml
extends: default                 # default, dark or print
colours:
  primary: "#0f5e5e"
  accent: "#e8684a"
palette:                         # names for block colours, beside the built-in ones
  teal: "#0f5e5e"
  coral: "#e8684a"
fonts:
  heading: "'Montserrat', Arial, sans-serif"
  body: "'Source Sans 3', Arial, sans-serif"
  mono: "'JetBrains Mono', Consolas, monospace"
  stylesheet: "https://fonts.googleapis.com/css2?family=Montserrat:wght@700&family=Source+Sans+3:wght@400;700&display=swap"
logo: logo.svg                   # relative to the theme file
```

A colour is a hex value, a CSS colour name, or an `rgb()` or `hsl()` value. A font is a CSS font list: name the fallbacks after the brand font, because the poster uses them on a computer without it.

`fonts.stylesheet` is a web address the page loads the fonts from. Set it to `null` to load nothing and use the fonts installed on the computer. A font that is not installed and not loaded is replaced by its fallback, so a brand font with no web version must be installed on every computer that shows or prints the poster.

> **Important:** The page loads `fonts.stylesheet` when it opens, so the default theme needs an internet connection to show its fonts. Without one the fallback fonts are used, the layout fits itself again, and nothing else changes. The `print` theme loads no fonts.

A mistake in a theme file, such as an unknown colour name or a value that is not a colour, stops the build with the file and the key.

### Theme colours

| Colour | What it paints |
|---|---|
| `backdrop` | Around the poster in the browser |
| `page` | The poster background |
| `surface` | Cards, figures, tables and the stats strip |
| `border` | The edges of those boxes and the footer rule |
| `text` | Body text |
| `muted` | Captions, labels and the right footer text |
| `header` | The header background |
| `header-text` | The title |
| `subtitle` | The subtitle |
| `byline` | The byline |
| `accent` | The rule under the header, between the stats and beside the summary blocks |
| `accent-text` | Arrow labels and card labels |
| `primary` | Behind section headings and table headings, and the default block colour |
| `on-primary` | Text on `primary` and on block colours |
| `secondary` | The introduction box, the banner and filled lane cells |
| `on-secondary` | Text on `secondary` |
| `highlight` | The heading text after a colon |
| `strong` | Stat values, card and block headings, lane labels and the left footer text |
| `code` | Behind inline code |
| `callout`, `callout-border` | A quote |
| `lcd`, `lcd-text`, `lcd-border` | The display screen |
| `diagram-fill` | Mermaid boxes |
