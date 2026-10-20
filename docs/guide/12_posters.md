---
title: Posters
---

# Posters

`py-doc poster` turns a Markdown file into one self-contained HTML poster: a header, a strip of figures, an introduction, columns of sections, a summary and a footer. Pictures, diagrams, charts, QR codes, logos and styles are all inside the page, so it can be sent or printed on its own.

```bash
py-doc poster                             # every poster under posters: in py-doc.yml
py-doc poster commissioning               # one of them, by name
py-doc poster g460.md                     # a Markdown file: writes g460.html
py-doc poster g460.md -o out.html --theme dark
py-doc poster g460.md --var version=2.1 --condition internal=true
py-doc poster --pdf                       # every poster, and a one-page PDF of each
```

`py-doc build` builds the posters of `py-doc.yml` too, after the documents, with their PDFs when they have `pdf: true`. `py-doc build NAME` builds one poster or document, and `py-doc build -f poster` builds only the posters. `--var` and `--condition` reach the posters as they reach the documents.

For a step-by-step introduction, read [Writing a poster](13_writing_posters.md) first. This chapter is the reference.

The examples in `examples/poster/` show three kinds, and `examples/py-doc.yml` lists them under `posters:`:

| Example | What it shows |
|---|---|
| `poster.md` | Portrait in the default theme, with every kind of block, a trend, a chart, a timeline and a full-width section. A QR code is in the footer. Every setting is in its front matter |
| `landscape.md` | Landscape in three columns, in the theme of a made-up company. The words are in the Markdown and the look (orientation, theme, header, footer) is in `py-doc.yml` |
| `release.md` | The dark theme, a chart with two series, a vertical timeline, a callout and a `{{version}}` variable |

## Settings and where they go

Every setting can be written in four places. Each one wins over the ones before it:

1. `poster:` in `py-doc.yml`: settings for every poster of the project, such as the company colours and logo.
1. The front matter of the Markdown file.
1. The poster's entry under `posters:` in `py-doc.yml`.
1. The command line: `--theme`, `--var` and `--condition`.

Mappings such as `colours` and `footer` are merged key by key, so a poster can change one colour and keep the rest. A path is relative to the file that names it. That is `py-doc.yml` for the first and third places, the Markdown file for the front matter, and the working folder for the command line.

```yaml
# py-doc.yml
poster:                                   # every poster
  theme: brand/poster-theme.yml
  logo: brand/logo.svg
  footer: {centre: Example Instruments}

posters:
  commissioning:
    source: posters/commissioning.md      # the Markdown file (required)
    output: build/posters/commissioning.html   # default: build/<name>.html
    orientation: landscape
    colours: {accent: "#d9573a"}          # over the theme
    header: {align: left, logo: left}
    footer:
      left: SN-100 commissioning
      right: Field engineering
      qr: https://example.com/commissioning
      qr-label: The full checklist
      logos: [brand/partner.png]
    variables: {version: "2.1"}
    conditions: {internal: false}
```

A mistake in `py-doc.yml`, such as an unknown key or a mapping where a value should be, is an error that names its place, such as `posters.commissioning.orientaton`. A key in the front matter that is not a setting is ignored with a warning, because front matter is shared with other tools.

| Setting | Default | What it sets |
|---|---|---|
| `title`, `subtitle`, `byline` | The first `#` heading, else the file name | The header text. `{{variables}}` are filled in |
| `orientation` | `portrait` | `portrait` or `landscape` |
| `columns` | 2 for portrait, 3 for landscape | How many columns the sections are in |
| `split` | Balanced by height | How many sections go in each column but the last, such as `3` for two columns or `2, 3` for three. Without it, the page measures each section and shares them out, in order, so the tallest column is as short as it can be |
| `paper` | `a1` | `a0` to `a4`, the page size for printing |
| `width` | 1400 for portrait, 1800 for landscape | The narrowest layout in pixels. Smaller makes everything larger on the page |
| `theme` | `default` | A built-in theme or a theme file. See [Themes](#themes) |
| `colours`, `palette`, `fonts` | The theme's | Changes over the theme, written as in a theme file |
| `logo` | The theme's | The picture in the header |
| `header` | `{align: centre, logo: left}` | `align`: `centre` or `left`. `logo`: `left`, `right` or `none` |
| `footer` | Empty | `left`, `centre` and `right` text (Markdown, with `{{variables}}`), `logos` (a list of pictures), `qr` (an address or text), `qr-label`, and `document` and `version` (shown small under the footer) |
| `document_number`, `version` | None | The document's number and version, shown small under the footer, unless `footer.document` or `footer.version` names others |
| `variables`, `conditions` | None | Values for `{{name}}` and `[[IF:]]`, as for documents |
| `pdf` | `false` | `true` prints a one-page PDF beside the page, and a path prints it there. `--pdf` and `--no-pdf` win |
| `embed_fonts` | `false` | `true` puts the theme's web fonts inside the page, so it and its PDF look the same offline. A list of subsets, such as `[latin, latin-ext]`, puts in only those. See [Fonts inside the page](#fonts-inside-the-page). `--embed-fonts` and `--no-embed-fonts` win |

`footer-left` and `footer-right` in the front matter still work, as `footer.left` and `footer.right`.

## Page structure

| Heading | Becomes |
|---|---|
| `## Stats` | A table of value, label, and optionally a change and a verdict, shown as the strip of figures. The header row is ignored |
| `## Abstract` | The introduction box |
| `## 1. Heading: accent` | A section. The text after the first colon is coloured |
| `## Summary` | The first paragraph is the banner, and each `###` is a block |
| `## References` | A list in small type above the footer, in two columns |

A section heading can end with attributes in braces:

- `{.wide}` makes the section span every column. The sections before it are balanced into the columns above it, and those after it into the columns below. `split` cannot be used with a wide section.
- `{colour=coral}` colours its heading bar, with any block colour.

```markdown
## 5. Roadmap: what comes next {.wide}
## 6. Troubleshoot: when a node will not join {.wide colour=slate}
```

### Trends

A third column in `## Stats` is a change, shown under the label with an arrow. A change that starts with `+` or `up` points up, one that starts with `-` or `down` points down, and anything else points sideways. Up and sideways are good news (`good` colour) and down is bad news (`bad` colour), unless a fourth column says `good` or `bad`:

```markdown
| Value | Label | Change | Verdict |
|---|---|---|---|
| 5.7 years | Battery life | +14 % | |
| 4 s | Typical join | -7 s | good |
```

## Writing

Section bodies are ordinary Markdown, with py-doc's own additions as in the [Writing chapter](03_writing.md):

| Markdown | On a poster |
|---|---|
| `[[INCLUDE: file.md]]`, `[[INCLUDE-CODE: file.py]]` | The file, or the file as a code block |
| `[[IF: name]]`, `[[NOT: name]]`, `[[ENDIF]]` | Kept or left out by the `conditions` |
| `{{name}}` | The value of a variable |
| `[[CAPTION:Figure]] text`, `[[CAPTION:Table]] text` | A caption. A paragraph that starts `Fig.` is one too |
| `> [!NOTE]`, `> **Warning:** text` | A callout box, in the colour of its kind: note, tip, important, warning or caution |
| `> text` | A plain callout, in the `callout` colour |
| A fenced code block | Code. A language name that is a diagram or a block below is drawn instead |
| `![alt](file.svg)` | The picture, embedded |
| `[[LANDSCAPE]]`, `[[PORTRAIT]]`, `[[PAGEBREAK]]`, `[[STYLE:Name]]` | Left out (the text after a `[[STYLE:]]` is kept). A poster is one page |

## Diagrams and charts

Every diagram fence of a document works on a poster: Mermaid, PlantUML, Graphviz, Vega-Lite and the rest. It is drawn by the tool container and embedded as an SVG picture, so it stays sharp when printed. Ditaa and the blockdiag family can only draw PNG, so theirs are PNG. Mermaid gets the colours and body font of the theme, as front matter added to the diagram, unless the diagram has its own front matter or `%%{init`. A diagram that cannot be drawn is shown as code with a warning, and the poster is still written.

> **Note:** A diagram wider than its column is scaled down and its text shrinks, so prefer compact layouts, such as Graphviz `dpi=80` or PlantUML `skinparam dpi 80`, or put it in a `{.wide}` section.

A `chart` block is drawn by py-doc itself, as SVG in the theme's colours, so it needs no container and prints sharp:

````markdown
```chart type=column title="Messages a day" unit=" msg"
series: 2.0, 2.1
Office | 1440 | 610
Warehouse | 1440 | 980
```
````

| Option | What it sets |
|---|---|
| `type` | `column` (default), `bar` (horizontal) or `line` |
| `title` | The title above the chart |
| `unit` | Text after each value label, such as `" mA"` |
| `max` | The top of the value axis (default: a round number above the largest value) |
| `height` | The height in pixels (default 300, or what the rows need for `bar`) |
| `colours` | Block colours for the series, separated by commas (default: `secondary`, `accent`, `primary`, `good`, `bad`, `muted`) |

Each line is a label and one value for each series. `series:` names the series and adds a legend.

## Poster blocks

A block colour is one of three things. It can be a name from the theme's palette: `navy`, `blue`, `amber`, `brown`, `red`, `grey` and `green` in every theme, and the theme's own. It can be a theme colour name such as `primary` or `accent`, or a colour value such as `#2a3150`.

| Fence | Lines | Options |
|---|---|---|
| `cards` | `Heading \| Text \| colour`, the colour only for the `top` style | `cols=2`, `style=` `title` (default), `label`, `top` or `plain` |
| `lcd` | Screens separated by blank lines. A line starting `--` is the caption | |
| `segments` | `weight \| label \| detail \| colour`, and an optional `title:` and `height:` | |
| `flow` | `[Filled\|colour]` or `[Outlined]` boxes, joined by `->` or `-label->` arrows | |
| `lanes` | `Label \| *filled cell \| dashed cell` | |
| `figure` | Several of `segments`, `flow` and `lanes` in one box, split by `+++` lines, each starting `@segments`, `@flow` or `@lanes` | |
| `timeline` | `date \| label \| detail \| colour`, the last two optional | `vertical` for a column instead of a row |
| `chart` | See [Diagrams and charts](#diagrams-and-charts) | |
| `qr` | The address or text to encode | `size=140` (pixels), `label="..."` |

In `segments`, `flow` and `lanes`, the lines that are not part of the diagram become notes under it, written in Markdown.

````markdown
```timeline
Jan 2026 | Pilot | 200 nodes | navy
Apr 2026 | Firmware 2.1
```

```qr size=160 label="The manual"
https://example.com/manual
```
````

A mistake in a block, such as a chart value that is not a number, stops the build with the file.

## Proportions and printing

A portrait poster has the proportions of its paper, such as 594 by 841 mm for A1. A landscape poster has those of the paper turned, so it prints on exactly one page. A script in the page finds the narrowest layout, no narrower than `width`, at which all the content fits, then scales the poster to the browser window. Adding or removing content needs no change of size. When a poster has little content there is space above the footer: lower `width` to make everything larger.

To print from a browser, use the print dialogue of Chrome with no margins and background graphics on. The page size and its orientation come from `paper` and `orientation`, and the poster fills exactly one page. Text, charts, QR codes, shapes and diagrams stay vector, apart from PNG diagrams and pictures.

## PDF

`py-doc poster --pdf`, or `pdf: true` in any of the four places, also prints each poster to a PDF with the Chromium of the tool container. It is one page of the poster's `paper`, in its `orientation`, the same as printing from Chrome. Text, charts, QR codes, shapes and diagrams stay vector, apart from PNG diagrams and pictures.

```yaml
posters:
  commissioning:
    source: poster/landscape.md
    pdf: true                          # build/commissioning.pdf, beside the page
  release:
    source: poster/release.md
    pdf: build/print/release-a3.pdf    # or a path of its own
```

> **Note:** The tool container has no network, so a theme's web fonts (`fonts.stylesheet`) are not loaded for the PDF unless they are inside the page. Set `embed_fonts: true`, or give the theme its font files, and the PDF uses the theme's own fonts. See [Fonts inside the page](#fonts-inside-the-page).

The PDF needs the tool container, like diagrams. The page alone does not.

## Themes

A theme sets the colours, the fonts, the block palette and the logo. The built-in themes are:

| Theme | What it is |
|---|---|
| `default` | A dark grey header, navy headings and blue boxes on a light page, in Source Serif 4 |
| `dark` | A dark page with amber accents, for screens |
| `print` | A white page and header with light boxes, in fonts every computer has, for printing with less ink |

`colours`, `palette`, `fonts` and `logo` beside `theme` in any of the four places change the theme, so a project can use a built-in theme with its own colours and logo without a theme file.

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

`fonts.stylesheet` is a web address the page loads the fonts from. Set it to `null` to load nothing and use the fonts installed on the computer. A font that is not installed and not loaded is replaced by its fallback. So a brand font with no web version must be installed on every computer that shows or prints the poster.

> **Important:** The page loads `fonts.stylesheet` when it opens, so the default theme needs an internet connection to show its fonts. Without one the fallback fonts are used, the layout fits itself again, and nothing else changes. The `print` theme loads no fonts, and `embed_fonts: true` puts them inside the page.

A mistake in a theme, such as an unknown colour name or a value that is not a colour, stops the build with the file and the key.

### Fonts inside the page

A poster can carry its fonts, so it looks the same on a computer without internet and in its PDF. There are two ways.

**The theme's own font files**, under `fonts.files`, are always put inside the page. Use them for a brand font that has no web version, or one you may not load from the web:

```yaml
fonts:
  heading: "'Brand Sans', Arial, sans-serif"
  files:
    - {family: Brand Sans, file: fonts/BrandSans-Bold.woff2, weight: 700}
    - {family: Brand Sans, file: fonts/BrandSans-Regular.woff2}          # weight 400, style normal
    - {family: Brand Sans, file: fonts/BrandSans-Italic.woff2, style: italic}
```

`family` is the name the font lists use. `file` is a `.woff2`, `.woff`, `.ttf` or `.otf` file, relative to the file that names it. `weight` is 100 to 900, or a range such as `100 900` for a variable font, and `style` is `normal` or `italic`.

**The web fonts of `fonts.stylesheet`** go inside the page with `embed_fonts: true`, or `--embed-fonts` on the command line. py-doc downloads the stylesheet and each font file it names once, on your computer, and keeps them in a `fonts` folder in the cache, beside the diagrams. A later build uses that copy and needs no network. When the download fails, the page links the stylesheet as before, with a warning, and the poster is still written.

```yaml
poster:
  theme: brand/company.yml
  embed_fonts: true
```

Embedded fonts make the page larger. A web font comes in subsets, one for each set of characters, and `embed_fonts` can name the ones to keep:

```yaml
embed_fonts: [latin, latin-ext]   # English and the other Western and Central European languages
```

| Theme | Every subset | `[latin, latin-ext]` | `[latin]` |
|---|---|---|---|
| `default` | 713 KB | 368 KB | 200 KB |
| The example brand | 513 KB | 315 KB | 128 KB |

The subset names are the ones Google Fonts gives, such as `latin`, `latin-ext`, `cyrillic`, `greek` and `vietnamese`. A character that no kept subset has is drawn in the fallback font. A variable font that the stylesheet lists once for each weight is put in the page once. More than 5 MB of fonts is reported with a warning, because the page is then slow to send and open.

> **Important:** A font's licence decides whether it may be put inside a file you send. The fonts of Google Fonts are under licences that allow it. Check the licence of a bought or brand font before you embed it.

### Theme colours

| Colour | What it paints |
|---|---|
| `backdrop` | Around the poster in the browser |
| `page` | The poster background |
| `surface` | Cards, figures, tables and the stats strip |
| `border` | The edges of those boxes and the footer rule |
| `text` | Body text |
| `muted` | Captions, labels, chart labels, and the centre and right footer text |
| `header` | The header background |
| `header-text` | The title |
| `subtitle` | The subtitle |
| `byline` | The byline |
| `accent` | The rule under the header, between the stats, beside the summary blocks, and timeline points |
| `accent-text` | Arrow labels and card labels |
| `primary` | Behind section headings and table headings, and the default block colour |
| `on-primary` | Text on `primary` and on block colours |
| `secondary` | The introduction box, the banner and filled lane cells |
| `on-secondary` | Text on `secondary` |
| `highlight` | The heading text after a colon |
| `strong` | Stat values, card and block headings, lane labels, timeline dates, QR codes and the left footer text |
| `code` | Behind inline code |
| `callout`, `callout-border` | A plain quote |
| `note`, `tip`, `important`, `warning`, `caution` | The callouts of each kind |
| `good`, `bad` | Trends that are good or bad news |
| `lcd`, `lcd-text`, `lcd-border` | The display screen |
| `diagram-fill` | Mermaid boxes |
