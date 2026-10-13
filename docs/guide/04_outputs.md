---
title: Outputs
---

# Outputs

Every output is made by pandoc, which runs in the tool container.

```yaml
outputs:
  docx: {template: templates/Template.docx}
  pdf: {toc: true}                  # XeLaTeX, with the built-in template unless `template` names a .tex file
  html: {template: styles/doc.css}  # one self-contained file; `template` is the stylesheet
  pptx: {split_level: 2, template: templates/Slides.pptx}
```

## Word

Pandoc writes the document with the template as its reference document, so the template's styles decide how everything looks (`Heading 1`, `Body Text`, `First Paragraph`, `Compact`, `Block Text`, `Source Code`, `Table`, `Image Caption` and so on). A template can be `.docx` or `.dotx`. Without one, a built-in reference document is used, which defines the callout box styles.

- **Merging**: when a template is set, the result is merged into it. The body goes where `[[INSERTCONTENT]]` stands, or at the end if there is no marker. `[[LANDSCAPE]]`, `[[PORTRAIT]]`, `[[STYLE:Name]]` and `[[CAPTION:Figure]]` lines are applied afterwards.
- **Placeholders**: `Replace-with-Title`, `-Author`, `-Version`, `-Document-Number`, `-Date`, `-Description` and `-Classification` are filled in the template body, tables, headers and footers. `placeholder_prefix` (default `Replace-with-`) and `marker` (default `[[INSERTCONTENT]]`) can be changed. A placeholder the document has no value for is emptied with a warning, and one that no property can fill (`Replace-with-Mystery`) is left and named in a warning.
- **Contents list**: `docx: {toc: true}` adds a table of contents to the depth of `toc_depth` (front matter). Word fills in the page numbers when the file is opened and asks to update fields.
- **Document properties** (title, author, subject, keywords, category, comments) are capped at Word's 255 characters, with a warning when a value is cut.
- **Code** is highlighted with the built-in theme.
- **A missing template is an error**, unless `allow_missing_template: true`. Pandoc's own warnings are shown as warnings.

## PowerPoint

Slides start at headings up to `split_level` (`--split-level`, default 2) and at `::: {.pagebreak}` lines. The title and author in the front matter make the title slide. Pandoc chooses layouts by their standard names (`Title Slide`, `Title and Content`, `Section Header`, `Two Content`, `Comparison`), so a template must start from `pandoc --print-default-data-file reference.pptx` and be edited in PowerPoint. A template that gives an empty deck is reported with that hint.

- **Speaker notes**: `<!-- notes: text -->`, or a `::: notes` block for more than one paragraph.
- **Columns**: a `:::: columns` block with two `::: column` blocks uses the Two Content layout.
- **Diagrams and pictures** sit on the slide on their own, with the `[[CAPTION:Figure]]` text under them.
- **Footer**: `footer: "{title} v{version}"` fills the footer placeholder of every slide (a layout without one is reported), and `{{VERSION}}` in a template shape is replaced by the version.
- **Long slides**: a slide with more than 16 lines gets a warning, because nothing is shrunk silently.
- **Fonts** embedded in a template are kept.

## PDF and HTML

- **PDF** is written by XeLaTeX with a built-in template that has a title page, or the `.tex` file named by `template`. `toc` is on by default. Callouts are coloured boxes, maths is typeset, and task lists keep their boxes.
- **HTML** is one self-contained file with pictures embedded. `template` is the stylesheet (py-doc's own by default), `toc: true` adds a contents list, and maths is MathML.

## Templates

`py-doc template check Template.docx` reports what the template lacks for the pandoc pipeline. `.docx`, `.dotx`, `.pptx` and `.potx` are accepted.

```bash
py-doc template check templates/sensor.docx --strict
py-doc template check templates/datasheet.docx --strict --prefix "@@" --marker "<<BODY>>"
py-doc template show templates/sensor.docx         # the styles, or the layouts of a deck
py-doc template diff A.docx B.docx                 # styles or layouts missing from one, or defined differently
py-doc template usage File.docx                    # how often a Word file uses each style
```

A FAIL exits with status 1: a style of the wrong type, bold body text, or a deck without the `Title Slide` or `Title and Content` layout. A WARN, such as a style pandoc will take from its own defaults, exits with 1 only with `--strict`. `-v` adds INFO. `diff` exits with 1 when the templates differ. A build runs the check, logs the failures and carries on. `py-doc init --templates` writes pandoc's own reference documents to start from.
