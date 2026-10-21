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
py-doc poster commissioning --watch       # build again on every save, and reload it in the browser
```

`--watch` builds the posters, serves them on this computer only and opens the first in the browser. It builds them again whenever a source file below a poster's folder changes, or a file its settings name, such as the theme, a logo or `py-doc.yml`. Each open page then reloads itself. A source file is Markdown, YAML, JSON, CSV, text, a picture, a diagram source or a font. A build that fails keeps the last good page, with the error shown across its top. `--port` chooses the port (default: a free one), and `--no-open` leaves the browser closed. It builds the pages only, so it does not take `--pdf`.

`py-doc build` builds the posters of `py-doc.yml` too, after the documents, with their PDFs when they have `pdf: true`. `py-doc build NAME` builds one poster or document, and `py-doc build -f poster` builds only the posters. `--var` and `--condition` reach the posters as they reach the documents.

`site.posters` puts posters on the web site. The [web sites chapter](08_sites.md#posters) has the details.

For a step-by-step introduction, read [Writing a poster](13_writing_posters.md) first. This chapter is the reference.

The examples in `examples/poster/` show four kinds, and `examples/py-doc.yml` lists them under `posters:`. Between them they use every setting and block in this chapter:

| Example | What it shows |
|---|---|
| `poster.md` | Portrait A1 in the default theme: a picture, a Mermaid diagram, bar and line charts, segments, flow, lanes and `lcd` screens. Also a timeline, a JSON code block, a full-width section, and a band of three columns (`{cols=3}`) under a band of two. A QR code is in the footer. Every setting is in its front matter |
| `landscape.md` | Landscape A1 in three columns, in the theme of a made-up company, with its web fonts inside the page (`embed_fonts: [latin]`) and a partner logo in the footer. A numbered Mermaid sequence from `diagrams.mermaid`, a gallery of mounting drawings, an acceptance checklist, handover steps, a QR block and an included table. The words and the layout (orientation, paper) are in the front matter, and the company's look (theme, header, footer) is in `py-doc.yml` |
| `release.md` | Portrait A3 in the dark theme: a column chart with two series, a before and after `compare` and a Mermaid sequence with notes. Also title cards, a vertical timeline, callouts, `people`, references and a `{{version}}` variable |
| `reliability.md` | Portrait A0 in the print theme, in three columns set by `columns` and `split`, with the logo on the right and `version: git`. PlantUML, Graphviz, Vega-Lite and ditaa (PNG) diagrams, a `figure` block, a line chart with `max`, `height` and `colours`, `highlight` figures, `progress` bars, `[[INCLUDE:]]`, `[[INCLUDE-CODE:]]`, `[[IF:]]` and `[[NOT:]]` with `conditions` from `py-doc.yml`, and table and figure captions |

## Settings and where they go

Every setting can be written in four places. Each one wins over the ones before it:

1. `poster:` in `py-doc.yml`: settings for every poster of the project, such as the company colours and logo.
1. The front matter of the Markdown file.
1. The poster's entry under `posters:` in `py-doc.yml`.
1. The command line: `--theme`, `--var` and `--condition`.

Put a setting with what it belongs to. The layout goes with the words, so `orientation`, `columns`, `split`, `paper` and `width` belong in the front matter: the file then builds the same poster on its own, with `py-doc poster file.md`. The company's look is shared, so its `theme`, `colours`, `logo`, `header` and `footer` belong under `poster:` in `py-doc.yml`. The poster's entry is for what one poster does differently, and the command line is for one build.

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
      logos: [brand/partner.svg]
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
| `document_number`, `version` | None | The document's number and version, shown small under the footer, unless `footer.document` or `footer.version` names others. `version: git` is the output of `git describe --tags --always`, as for a document |
| `variables`, `conditions` | None | Values for `{{name}}` and `[[IF:]]`, as for documents |
| `pdf` | `false` | `true` prints a one-page PDF beside the page, and a path prints it there. `--pdf` and `--no-pdf` win |
| `embed_fonts` | `false` | `true` puts the theme's web fonts inside the page, so it looks the same offline (a PDF gets the fonts inside either way). A list of subsets, such as `[latin, latin-ext]`, puts in only those. See [Fonts inside the page](#fonts-inside-the-page). `--embed-fonts` and `--no-embed-fonts` win |

`footer-left` and `footer-right` in the front matter still work, as `footer.left` and `footer.right`.

## Page structure

A poster is its header, then its sections in the order of the file, then its footer. What each section is, and how wide, is said in braces at the end of its heading. No heading name has a meaning of its own, so the headings are yours to choose.

| Braces | The section is |
|---|---|
| None | A section in a band of columns |
| `{.wide}` | A section that spans every column, a band of its own |
| `{.stats}` | The strip of figures: a table of value, label, and optionally a change and a verdict. The header row is ignored |
| `{.abstract}` | The introduction box |
| `{.summary}` | The banner, from its first paragraph, then a block for each `###` |
| `{.references}` | A list in small type, in two columns, under its own heading |

A stats strip, abstract, summary or references list is full width and has no heading bar: the heading names it in the file, and only a references list shows it. Each goes where it is in the file, so a second stats strip can sit halfway down.

The other braces change one section:

- `{cols=3}` gives its band of columns three columns. Give it on any one section of the band. Without it, the band has `columns:` columns.
- `{.flow}` lets the section go on in the next column, between two of its blocks, under its heading again with "(continued)". Use it for a section much taller than the rest. A caption stays with its picture or table.
- `{colour=coral}` colours its heading bar, or the box of an abstract or the banner of a summary, with any block colour.

The sections between two full-width parts are a band of columns, balanced by height. Of every way to share them out, in order, the page takes those whose tallest column is shortest, and of those the one whose columns are most even. `split` chooses the columns by hand instead, on a poster with one band of columns.

So a poster that goes full width, two columns, full width, three columns, then a summary is written as:

```markdown
## Key figures {.stats}
## Why this matters {.abstract}
## 1. Overview {.wide}
## 2. Left of the first band {cols=2}
## 3. Right of the first band
## 4. Results {.wide colour=slate}
## 5. First of three {cols=3}
## 6. Second of three
## 7. Third of three
## In short {.summary}
## Sources {.references}
```

The header comes from the `title`, `subtitle`, `byline`, `logo` and `header` settings, and the footer from the `footer` setting. They have no section, because they are the same on every page of a project. Without a `title`, the first `#` heading is the title. In a section heading, the text after the first colon is coloured.

### Trends

A third column in a `{.stats}` table is a change, shown under the label with an arrow. A change that starts with `+` or `up` points up, one that starts with `-` or `down` points down, and anything else points sideways. Up and sideways are good news (`good` colour) and down is bad news (`bad` colour), unless a fourth column says `good` or `bad`:

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
| `[[CAPTION:Figure]] text`, `[[CAPTION:Table]] text` | A numbered caption, "Figure 1:" or "Table 1:" as in Word, counted down the poster and through its includes. A paragraph that starts `Fig.` is a caption as written, with no number |
| `> [!NOTE]`, `> **Warning:** text` | A callout box, in the colour of its kind: note, tip, important, warning or caution |
| `> text` | A plain callout, in the `callout` colour |
| A fenced code block | Code. A language name that is a diagram or a block below is drawn instead |
| `![alt](file.svg)` | The picture, embedded |
| `[[LANDSCAPE]]`, `[[PORTRAIT]]`, `[[PAGEBREAK]]`, `[[STYLE:Name]]` | Left out (the text after a `[[STYLE:]]` is kept). A poster is one page |

## Diagrams and charts

Every diagram fence of a document works on a poster: Mermaid, PlantUML, Graphviz, Vega-Lite and the rest. It is drawn by the tool container and embedded as an SVG picture, so it stays sharp when printed. Ditaa and the blockdiag family can only draw PNG, so theirs are PNG. Mermaid gets the colours and body font of the theme, as front matter added to the diagram, unless the diagram has its own front matter or `%%{init`. The `diagrams.mermaid` settings of py-doc.yml apply too, under the theme's colours. A diagram that cannot be drawn is shown as code with a warning, and the poster is still written.

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
| `min` | The bottom of the value axis, for a `line` chart only (default: zero, or a round number below a negative value). A column or bar that does not start at zero misleads |
| `max` | The top of the value axis (default: a round number above the largest value) |
| `step` | The distance between gridlines, for `line` and `column` (default: a quarter of the axis). At most 20 steps |
| `values` | Which values are written by their point, bar or column: `all`, `last` or `none` (default: `none` for `line`, else `all`) |
| `axis` | The title of the value axis |
| `markers` | `yes` (default) or `no`: a dot on each point of a `line` chart |
| `area` | `yes` or `no` (default): shade under each line of a `line` chart |
| `dashed` | The series of a `line` chart drawn dashed, by name or number, separated by commas, such as `dashed=Target` |
| `height` | The height in pixels (default 300, or what the rows need for `bar`) |
| `colours` | Block colours for the series, separated by commas (default: `secondary`, `accent`, `primary`, `good`, `bad`, `muted`) |

Each line is a label and one value for each series. `series:` names the series and adds a legend.

## Poster blocks

A block colour is one of three things. It can be a name from the theme's palette: `navy`, `blue`, `amber`, `brown`, `red`, `grey` and `green` in every theme, and the theme's own. It can be a theme colour name such as `primary` or `accent`, or a colour value such as `#2a3150`.

| Fence | Lines | Options |
|---|---|---|
| `cards` | `Heading \| Text \| colour`, the colour only for the `top` style | `cols=2`, `style=` `title` (default), `label`, `top` or `plain` |
| `lcd` | Screens separated by blank lines. A line starting `--` is the caption | `cols=` (default: up to 3). Six screens with `cols=2` are 2 columns and 3 rows |
| `segments` | `weight \| label \| detail \| colour`, and an optional `title:` and `height:` | |
| `flow` | `[Filled\|colour]` or `[Outlined]` boxes, joined by `->` or `-label->` arrows | |
| `lanes` | `Label \| *filled cell \| dashed cell` | |
| `figure` | Several of `segments`, `flow` and `lanes` in one box, split by `+++` lines, each starting `@segments`, `@flow` or `@lanes` | |
| `timeline` | `date \| label \| detail \| colour`, the last two optional | `vertical` for a column instead of a row |
| `chart` | See [Diagrams and charts](#diagrams-and-charts) | |
| `qr` | The address or text to encode, or with `type=` the `key: value` lines of a contact, event or other kind. See [QR codes](#qr-codes) | `type=` (default `url`), `file=`, `size=140` (pixels), `label="..."`, `ecc=` `L`, `M` (default), `Q` or `H` |
| `barcode` | The data to encode, on one line | `type=` `code128` (default), `code39`, `ean13`, `ean8`, `upca` or `itf14`, `width=240` and `height=70` (pixels), `text=no`, `check=yes` (Code 39), `label="..."`. See [Barcodes](#barcodes) |
| `steps` | `Heading \| text \| colour`, the text and colour optional | `cols=1`, `start=1`: the number of the first step |
| `gallery` | `picture \| caption`, the picture relative to the Markdown and the caption optional | `cols=3` (or fewer pictures), `height=` in pixels: crop every picture to one height |
| `progress` | `label \| value \| target \| colour`, the colour optional (default: `good` when met, else `accent`, or `bad` over a ceiling) | `unit=" nodes"`, `show=` `values` (default) or `percent`, `better=` `higher` (default) or `lower`, for a ceiling such as a return rate |
| `checklist` | `[x] done`, `[ ] open` or `[!] failed`, then the text | `cols=1` |
| `compare` | A header such as `\| Before \| After`, then `label \| before \| after`. Any number of columns; the last is stressed | |
| `people` | `name \| role \| contact \| photo`, all but the name optional. Without a photo the initials are shown | `cols=2` (or fewer people) |
| `highlight` | `value \| label \| detail \| colour`, the last two optional (default colour: `accent`) | `cols=` (default: one for each line) |

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

### QR codes

A `qr` block encodes its text as written: an address, or any text. With `type=`, its lines are the parts of something a phone knows how to use, written as `key: value`. py-doc writes the standard form that phones read, with its escaping, so a poster never needs the vCard or iCalendar syntax.

| `type=` | A phone offers to | Lines (repeat `tel`, `mobile`, `email` and `url` for more than one) |
|---|---|---|
| `url` (default), `text` | Open the address, or show the text | The address or text |
| `vcard` (or `contact`) | Save the contact (vCard 3.0) | `name` (or `first` and `last`), `org`, `title`, `tel`, `mobile`, `email`, `url`, `address` (street, town, postcode, country), `note` |
| `event` (or `calendar`) | Add the event to a calendar (iCalendar) | `title`, `start` and `end` (`YYYY-MM-DD` for a whole day, `YYYY-MM-DD HH:MM` local time, or with `Z` for UTC; default end: an hour or a day later), `location`, `description`, `url` |
| `wifi` | Join the network | `ssid`, `password`, `security` (`WPA`, the default with a password, `WEP` or `none`), `hidden` |
| `email` | Write an e-mail | `to`, `subject`, `body` |
| `phone` | Call the number | `number` |
| `sms` | Send a text | `number`, `body` |
| `geo` | Show the place on a map | `lat`, `lon` |

````markdown
```qr type=vcard label="Commissioning support"
name: Jane Smith
org: Example Instruments
tel: +44 1234 567890
email: support@example.com
```

```qr type=event label="Add the training day"
title: SN-100 commissioning training
start: 2026-11-03 09:00
end: 2026-11-03 16:30
location: Leeds test lab
```

```qr file=contacts/jane.vcf label="Jane's card"
```
````

- `file=` encodes a file, relative to the Markdown: a `.vcf` or `.ics` file is a contact or an event, anything else is text. Text already in a standard form, such as the lines of a vCard starting `BEGIN:VCARD`, is also encoded as it is.
- The more a code holds, the denser it is. A contact or an event needs a larger `size=` than an address to stay easy to scan from a distance. `ecc=` trades size for robustness: `L` makes the smallest code, `H` survives the most damage.
- A mistake, such as a key the type does not have or a date that is not a date, stops the build with the file and what is wrong.
- The footer's `qr` encodes an address or text only.

### Barcodes

A `barcode` block draws a linear barcode of its line, in the theme's colour on white, with the digits or text under the bars.

| `type=` | For | Data |
|---|---|---|
| `code128` (default) | Serial numbers, part numbers, any short text | Printable ASCII |
| `code39` | Older equipment and labels | `A` to `Z`, `0` to `9`, space and `- . $ / + %`, letters made capital. `check=yes` adds the check character |
| `ean13` | Retail products | 12 digits, or 13 with the check digit |
| `ean8` | Small retail products | 7 digits, or 8 with the check digit |
| `upca` | Retail products in North America | 11 digits, or 12 with the check digit |
| `itf14` | Cartons and outer cases (GTIN-14), drawn with its bearer bars | 13 digits, or 14 with the check digit |

````markdown
```barcode type=ean13 label="SN-100 retail box"
501234567890
```

```barcode width=320 label="Serial"
SN-100-0042
```
````

- The check digit of an EAN, UPC or ITF-14 code is worked out when it is left out, and checked when it is given. So a mistyped digit stops the build instead of printing a barcode of another product. Spaces and hyphens in the digits are ignored.
- EAN and UPC are drawn as on products: longer guard bars, and the digits in their groups between them. The space the scanner needs on each side (the quiet zone) is part of the drawing, so nothing should be put closer than its white box.
- `width=` is the whole drawing, quiet zones included. Print a retail code no smaller than its standard size: about 140 pixels wide for EAN-13 and UPC-A, 100 for EAN-8 and 400 for ITF-14.

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

The tool container has no network. So py-doc downloads a theme's web fonts (`fonts.stylesheet`) on this computer, and prints the PDF from a copy of the page with them inside. The page itself still links them, unless `embed_fonts` is set. The fonts are kept in the cache folder, so later builds need no network. Offline with an empty cache, py-doc warns and the PDF has the fallback fonts.

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

A poster can carry its fonts, so it looks the same on a computer without internet. There are two ways. A PDF that py-doc prints gets the web fonts inside whether or not the page has them: see [PDF](#pdf).

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
