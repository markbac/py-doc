---
title: Writing
---

# Writing

This chapter is the reference for the Markdown py-doc reads. For a walk through writing one from a blank file, read [Writing a document](14_writing_documents.md), [Writing a slide deck](15_writing_slides.md) or [Writing a poster](13_writing_posters.md).

Pandoc reads the Markdown: its own flavour, with fenced divs, raw HTML, table captions, strikethrough and task lists. Footnotes, definition lists, maths and the rest of pandoc Markdown work too. py-doc adds front matter, callouts, markers, includes, conditions, variables and diagrams.

## Supported Markdown

| Markdown | Output |
|---|---|
| Front matter | Title, author, date, version, status and the like become the document properties and the title block. A first heading equal to the title is not shown twice |
| Callouts, `> [!NOTE]` and `> **Note:**` | A box in the `Div.note` to `Div.caution` styles (Word), a coloured block (HTML, PDF), an admonition or aside (sites) |
| `[[CAPTION:Figure]] text` | A numbered caption for the picture, diagram or table that follows |
| `[[LANDSCAPE]]`, `[[PORTRAIT]]` | A section of that orientation (Word), and picture widths in the other formats |
| `[[STYLE:Name]] text` | The paragraph in that Word style |
| `[[PAGEBREAK]]`, or `::: {.pagebreak}` and `:::` | A page break, or a new slide |
| Fenced diagram blocks | A picture: see [Diagrams](#diagrams) |
| Raw HTML | Kept in HTML and sites, dropped elsewhere by pandoc |

py-doc itself never drops a word or a sentence. Anything pandoc cannot represent in a format (raw HTML in Word, for example) is dropped by pandoc, which says so in a warning.

## VS Code preview

A companion VS Code extension in [`editors/vscode/`](../../editors/vscode) previews py-doc Markdown as you write. Click the eye button in the editor title bar. It runs `py-doc docx`, `py-doc slides` or `py-doc poster` with `--watch` on the open file, and shows the page it serves beside the editor. It rebuilds on every save, with every diagram drawn, so the preview is py-doc's own output. A save that does not build shows the error as a warning, and the preview moves to another Markdown file when you switch to it. VS Code's built-in Markdown preview shows plain Markdown only. The extension chooses the command from the file. A poster setting such as `paper` or `byline` in the front matter means a poster. `split_level` or speaker notes mean a deck, and anything else is a Word document. See [live preview](02_projects.md#live-preview) and the extension's [README](../../editors/vscode/README.md).

## Poster blocks in documents

The blocks of a poster work in a Word document, a PDF, a deck and a site page, written the same way:

````markdown
[[CAPTION:Figure]] Messages a day
```chart type=column unit=" msg"
series: 2.0, 2.1
Office | 1440 | 610
Warehouse | 1440 | 980
```

```cards cols=3 style=top
Sensor | Temperature and humidity on I2C | blue
Controller | Sleeps at 2 µA | navy
Radio | Sends one message, then sleeps | green
```
````

A [`plot`](12_posters.md#plots) works the same way. Each block becomes a picture, as a diagram does, with its caption, `width=` and alt text. A block that is all SVG, such as a `chart`, a `qr` or a `barcode`, stays SVG in HTML and a site, and is PNG in Word, PowerPoint and PDF. A block made of boxes and text, such as `cards`, `steps` or `equation`, is laid out at the width of the page's text and becomes a PNG. Pictures are cached as diagrams are, and drawing them needs the tool container.

The blocks are drawn in the `print` theme, so they suit a white page. `diagrams.theme` in `py-doc.yml` chooses another, a built-in name or a theme file:

```yaml
diagrams:
  theme: brand/poster-theme.yml   # the colours and fonts of the company's posters
```

## Front matter

The YAML between `---` lines at the top of the first source of a document gives its properties: `title`, `subtitle`, `author`, `date`, `version`, `status`, `document_number`, `description`, `classification`, `subject`, `keywords`, `category`, `company` and `toc_depth`. A value in `py-doc.yml` wins over the front matter. Every document of py-doc's own repository has front matter, so its properties travel with the file.

## Callouts

Callouts are drawn as boxes in every format, in both spellings:

```markdown
> [!WARNING]
> Disconnect the battery first.

> **Tip:** the kinds are note, tip, important, warning and caution.
```

Word uses the `Div.note` to `Div.caution` paragraph styles. The built-in reference document defines them, and a template that lacks one that the document uses gets a warning naming it. Sites get MkDocs admonitions or Starlight asides.

## Captions, orientation and styles

- **Captions**: `[[CAPTION:Figure]] Text` (or `Table`) on the line before a picture, diagram, code block or table becomes its caption. A diagram also takes one from the line after it. In Word the number is a `SEQ` field, shared with the captions pandoc makes itself, so captions renumber when Word updates fields. Cross-references to captions are not supported. On a slide the caption is the text under the picture.
- **Orientation**: `[[LANDSCAPE]]` and `[[PORTRAIT]]` start a Word section of that orientation, and widen or narrow pictures in the other formats.
- **Styles**: `[[STYLE:Name]] text` applies a named Word paragraph style, and warns once if the template has none of that name. Other formats keep the text.
- **Page breaks**: `[[PAGEBREAK]]` on its own line, `::: {.pagebreak}` followed by `:::`, or `page_break: true` on a source. In a deck it starts a new slide, and on a site it is left out.

## Includes, conditions and variables

These lines are applied to each source before it is parsed. They are only recognised outside code, so a document can show the syntax in a fenced block or in backticks.

```markdown
[[INCLUDE: shared/legal.md]]        <!-- another Markdown file, expanded in turn -->
[[INCLUDE-CODE: src/server.py]]     <!-- a file as a fenced code block; the language comes from the extension -->

[[IF: internal]]                    <!-- also [[IF: audience == staff]] and [[NOT: internal]] -->
Internal notes.
[[ENDIF]]

This is version {{version}}.
```

Set values under a document in `py-doc.yml`, or for one build with `--var` and `--condition`, which win over the file:

```yaml
documents:
  guide:
    sources: [guide.md]
    variables: {version: "2.1"}
    conditions: {internal: false}
```

- **Paths** start at the file that holds the directive. Image paths in an included file are relative to the file that includes it, not to the included file.
- **Mistakes are errors** that name the file and line: a missing or circular include, an `[[IF:]]` that is never closed, an `[[ENDIF]]` with nothing open, or a condition that is not defined. An undefined `{{variable}}` is left as written and reported as a warning, because the braces are ordinary text in many documents.
- **Truth**: `false`, `no`, `off`, `0` and an empty value are false; anything else is true. `==` and `!=` compare as text.

## Diagrams

A fenced block whose language is a diagram type becomes a picture in every output:

````markdown
```plantuml title="System context" width="80%"
@startuml
Alice -> Bob : hello
@enduml
```
````

| Fences | Tool |
|---|---|
| `mermaid` (also `:::mermaid`), `plantuml` or `puml`, `dot` or `graphviz`, `ditaa` | Mermaid, PlantUML, Graphviz, ditaa |
| `blockdiag`, `seqdiag`, `actdiag`, `nwdiag`, `packetdiag`, `rackdiag` | The blockdiag family |
| `wavedrom`, `bytefield-svg`, `pikchr`, `railroad`, `wireviz` | Drawn as SVG |
| `vega`, `vega-lite` | Vega, drawn as SVG |

- **Format**: HTML and sites keep SVG where the tool can write it. Word, PowerPoint and PDF get PNG at 192 dpi, shrunk to the page width (wider after a `[[LANDSCAPE]]` line, until `[[PORTRAIT]]`).
- **Alt text** comes from `caption="..."` or `title="..."` after the language, else from a `title` line in the diagram, else the diagram type.
- **Captions**: a `[[CAPTION:Figure]] text` line directly above or below the diagram is its caption. Without one, the alt text is the caption.
- **Size**: `width="100%"` after the language makes the diagram that share of the text width (the page less its margins). A length such as `12cm`, `30mm`, `4in` or `600px` is also allowed. Without it, a diagram keeps its drawn size, shrunk to fit the page.
- **A broken diagram stops the build** with the file, the line and the tool's own message, and no output file is written. `py-doc build --keep-going` draws every diagram first and lists all the failures together.
- **Pictures are cached** in your user cache folder (`PY_DOC_CACHE` overrides it), keyed by the diagram text, the format and the tool image, so an unchanged diagram is not drawn again. A PlantUML diagram with `!include` is always drawn, because the included file can change on its own.
- **PlantUML includes** are looked up in the folder of the Markdown file, which is the only source folder the tool can read.
- **Mermaid** is version 12, drawn by mermaid-cli 12. A diagram is drawn at its natural size, and only one wider or taller than the page (1200 pixels, or 1800 after `[[LANDSCAPE]]`) is shrunk to fit.
- **Mermaid 12 looks different** from Mermaid 11: flowcharts, class, state and ER diagrams are laid out with ELK and drawn in the `neo` look. To keep the Mermaid 11 layout and look for one diagram, start it with front matter:

    ```markdown
    ---
    config:
      layout: dagre
      look: classic
    ---
    flowchart LR
      A --> B
    ```

    To give every Mermaid diagram of a project the same settings, put them under `diagrams.mermaid` in `py-doc.yml`. A diagram's own front matter wins, key by key:

    ```yaml
    diagrams:
      mermaid:
        layout: dagre
        look: classic
        theme: neutral
    ```

    Give settings in front matter, not in a `%%{init: ...}%%` line. Mermaid ignores the whole init line when a value in it has a single quote, such as a font list.
- **Poster blocks** (`cards`, `chart`, `steps`, `equation`, `terminal` and the rest of [the posters chapter](12_posters.md#poster-blocks)) work in documents, decks and sites too. See [Poster blocks in documents](#poster-blocks-in-documents).
- **Pictures** in Markdown are looked up in the folders of the source files, so `![](images/a.png)` works as it does next to the Markdown. `![](images/a.png){width=50%}` makes a picture that share of the text width, in Word too, where py-doc works it out from the template's page and margins.
