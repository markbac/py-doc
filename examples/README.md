# py-doc examples

A small project to try every part of `py-doc` on. It documents a generic IoT product, the SN-100 sensor node, which measures temperature and humidity and publishes the readings over MQTT. It has Markdown sources, a `py-doc.yml`, Word, PowerPoint and HTML templates, lint rules and a Structurizr model. Copy the folder and change it into your own project.

## Before you start

1. Install `py-doc` (Python 3.10 or later) from the repository root:

    ```bash
    pip install -e .
    ```

1. Install Docker Engine if you have not (on Windows this needs WSL 2 with Ubuntu or Debian already installed):

    ```bash
    py-doc setup
    ```

1. Build the tool image once. It holds pandoc, Mermaid, PlantUML, Graphviz, xelatex, Inkscape and Structurizr, so nothing else needs installing. Docker must be running. On Windows that means Docker Engine inside a WSL 2 distribution, not Docker Desktop. `py-doc doctor` tells you what is missing.

    ```bash
    py-doc tools build        # slow the first time, with progress shown
    py-doc doctor             # checks that the image works
    ```

1. Work from this folder. `py-doc` finds `py-doc.yml` here and writes to `build/`:

    ```bash
    cd examples
    ```

What needs Docker: Word, PowerPoint, PDF and HTML output, every diagram type, drawing the views of a model, exporting a `.dsl` workspace, `c4 up` and the web site. What does not: `lint` with the built-in rules, `template check|show|diff|usage`, `import`, and `c4 check` and `c4 export -f markdown` on `architecture/workspace.json`.

## What is here

| Path | What it shows |
|---|---|
| `py-doc.yml` | Five documents, output defaults, per-document variables and conditions, file naming, the build report, C4, lint and site settings. Every setting has a comment |
| `site/` | The MkDocs site project: `mkdocs.yml` (yours to change) and `py-doc-nav.yml` (written by `py-doc site`) |
| `docs/guide/` | The guide, in five files: front matter and document properties, variables, conditions, nested includes, every callout style, all heading levels, block quotes, captions, lists, task lists, footnotes, definition lists, maths, code includes, a landscape section, page breaks, an appendix with a shifted heading level, links between chapters. `DRAFT.md` is listed with `include: false` |
| `docs/guide/05_diagram_types.md` | One example of every other diagram type: blockdiag, actdiag, seqdiag, nwdiag, packetdiag, ditaa, wavedrom, bytefield-svg, wireviz, railroad, pikchr, vega and vega-lite. Graphviz, Mermaid and PlantUML are in `docs/guide/02_design.md` |
| `docs/datasheet.md` | A short datasheet that includes the diagram chapter, to try the datasheet template (`@@` placeholders) and the LaTeX template |
| `docs/release-notes.md` | A short document whose version comes from Git (`version: git`) |
| `docs/deck/slides.md` | The deck: section slides, bullets, columns, incremental lists, both kinds of speaker notes, diagrams, a picture, a table, maths, callouts, code, an include, a condition, a page break |
| `docs/includes/` | Files pulled in with `[[INCLUDE:]]` and `[[INCLUDE-CODE:]]` |
| `templates/sensor.docx` | The Word template: logo, title page with `Replace-with-*` placeholders, header, footer with page numbers, callout styles, a `Lead Paragraph` style, `[[INSERTCONTENT]]` where the body goes |
| `templates/sensor_Draft.docx` | The same template with a red "DRAFT" header. A document with `status: Draft` uses it without being told to |
| `templates/sensor.pptx`, `sensor_Draft.pptx` | The PowerPoint template, and the one a `status: Draft` deck uses. Coloured titles and a `{{VERSION}}` shape on the master, filled in when the deck is built |
| `templates/datasheet.docx` | A Word template with its own placeholder prefix (`@@Title`) and body marker (`<<BODY>>`) |
| `templates/report.tex`, `report_Draft.tex` | A LaTeX template for PDF output with its own colours, and a twin with a DRAFT watermark for `status: Draft` |
| `templates/doc.css`, `doc_Draft.css` | The stylesheet for HTML output (`py-doc`'s own plus company colours), and the red-banner one a `status: Draft` document uses |
| `templates/make_templates.py` | Regenerates the templates, the logo and `word/design_review.docx` |
| `architecture/workspace.dsl`, `workspace.json` | The same Structurizr model twice. The JSON needs no Java or Docker |
| `structure-rules.yaml`, `vale-rules.yml`, `.markdownlint.yaml` | Rule files used by `py-doc lint` |
| `word/design_review.docx` | A Word file to try `py-doc import` on |

The diagram chapter is part of the guide (`docs/guide/05_diagram_types.md`) and of the datasheet, so `py-doc build guide` draws every diagram type: blockdiag, actdiag, seqdiag, nwdiag, packetdiag, ditaa, wavedrom, bytefield-svg, wireviz, railroad, pikchr, vega, vega-lite, Graphviz, Mermaid and PlantUML. All of them are installed in the tool image. `graphviz` and `puml` are accepted as other names for `dot` and `plantuml`. See the Writing chapter of the user guide (`docs/guide/03_writing.md`).

## Quick start

Run these in order from this folder. Each line says what it makes.

```bash
py-doc build guide                                   # build/guide-v1.0.docx, guide.pdf, guide.html
py-doc build datasheet                               # build/datasheet-1_0.docx and datasheet.pdf
py-doc build deck                                    # build/deck.pptx
py-doc build release-notes                           # build/release-notes-<git version>.docx, needs a Git commit
py-doc build architecture                            # build/architecture.docx and architecture.html
py-doc import word/design_review.docx -o imported    # imported/design_review.md and imported/design_review/
py-doc docx imported/design_review.md                # imported/design_review.docx: the round trip
py-doc import build/deck.pptx -o imported            # imported/deck.md: the deck back as Markdown
py-doc site init                                     # site/mkdocs.yml, once
py-doc site build                                    # site/build/index.html: the guide, datasheet and architecture as a site
```

`py-doc import` needs the Word or PowerPoint file as its argument, so a bare `py-doc import` prints a usage error. The sample files are `word/design_review.docx` and the deck you built.

## Which command makes which output

| Command | Reads | Writes |
|---|---|---|
| `py-doc build guide` | `docs/guide/*.md`, `docs/includes/`, `templates/sensor.docx` (or `sensor_Draft.docx`), `templates/doc.css` | `build/guide-v1.0.docx`, `build/guide.pdf`, `build/guide.html` |
| `py-doc build datasheet` | `docs/datasheet.md`, `templates/datasheet.docx`, `templates/report.tex` | `build/datasheet-1_0.docx`, `build/datasheet.pdf` |
| `py-doc build deck` | `docs/deck/slides.md`, `templates/sensor.pptx` (or `sensor_Draft.pptx`) | `build/deck.pptx` |
| `py-doc build architecture` | `architecture/workspace.json`, `docs/includes/audience.md` | `build/architecture.docx`, `build/architecture.html` (chapters generated from the model) |
| `py-doc import` | `word/design_review.docx`, `build/deck.pptx` | Markdown and pictures in `imported/` |
| `py-doc site build` | The sources of the guide, datasheet and architecture, `site/mkdocs.yml` | Pages in `site/docs/<document>/`, navigation in `site/py-doc-nav.yml`, the site in `site/build` |

Every build also writes `build/report.json`, with the tools and versions used, each source, each output with its SHA-256, and each diagram.

## Build the outputs

Run these from this folder, in this order the first time.

```bash
# Word, PDF and HTML of the guide (the formats in py-doc.yml)
py-doc build guide

# One format at a time
py-doc build guide -f docx        # build/guide-v1.0.docx
py-doc build guide -f pdf         # build/guide.pdf
py-doc build guide -f html        # build/guide.html

# The internal version of the guide, with another version number
py-doc build guide -f docx --condition internal=true --var version=1.1

# The staff version: the [[IF: audience == staff]] text appears
py-doc build guide -f html --condition audience=staff

# The datasheet, with all its diagram types
py-doc build datasheet

# PowerPoint deck: a section slide per first-level heading, a slide per second-level heading
py-doc build deck                 # build/deck.pptx

# Architecture chapters generated from the C4 model
py-doc build architecture         # build/architecture.docx

# Everything in py-doc.yml, and a list of every failure at the end instead of the first one
py-doc build --keep-going
```

To convert a single file without `py-doc.yml`:

```bash
py-doc docx docs/guide/02_design.md -o build/design.docx --template templates/sensor.docx
py-doc slides docs/guide/02_design.md -o build/design.pptx --template templates/sensor.pptx --split-level 2
```

A file with `[[IF:]]` lines (`00_overview.md`, `03_operations.md`, the deck) needs its conditions, which only `py-doc build` sets, so build those as documents.

## Templates

The Word template is pandoc's reference document, so its styles decide how everything looks. The file is built by `templates/make_templates.py`, which is the easiest place to see what a good template contains: the callout styles (`Div.note` to `Div.caution`), `Caption`, `Source Code`, headings, a title page with placeholders, and the `[[INSERTCONTENT]]` line.

```bash
py-doc template check templates/sensor.docx --strict
py-doc template check templates/sensor.pptx --strict
py-doc template check templates/datasheet.docx --strict --prefix "@@" --marker "<<BODY>>"
py-doc template show templates/sensor.docx
py-doc template diff templates/sensor.docx templates/sensor_Draft.docx
py-doc template usage word/design_review.docx
```

The placeholders the title page can use are `Replace-with-Title`, `-Author`, `-Version`, `-Document-Number`, `-Date`, `-Description` and `-Classification`. They are filled from the front matter of the first source, in the body, tables, headers and footers.

## Features by format

Every feature each format supports appears at least once in these files.

| Format | Features and where to see them |
|---|---|
| Word | Title page placeholders, status template, header and footer fields, contents list (`toc`, `toc_depth`), numbered captions, every callout style, heading levels 1 to 4, block quotes, footnotes, maths as Word equations, landscape and portrait sections, page breaks, `[[STYLE:]]`, document properties (subject, category, keywords), own placeholder prefix and body marker (`datasheet.docx`), file name patterns. See `docs/guide/` and `docs/datasheet.md` |
| PowerPoint | Title, section, one-column and two-column layouts (text and text, text and picture), nested bullets, incremental lists, speaker notes in both spellings, footer pattern, version shape, Draft template, diagrams with captions, picture, table, maths, callouts, code, include, condition, empty-title slide from a page break. See `docs/deck/slides.md` |
| PDF | Contents list on or off, the built-in LaTeX template with title page fields, a custom `.tex` template (`report.tex`), captions, task lists, callouts, maths, footnotes, every diagram type. See `docs/guide/` and `docs/datasheet.md` |
| HTML | Stylesheet template, embedded pictures, captions, contents list, callouts |

## Lint

```bash
py-doc lint docs                    # built-in rules, structure rules and C4 model rules
py-doc lint docs --engine vale      # Vale with the bundled PyDoc style
py-doc lint docs --format csv > issues.csv   # or --format github
py-doc lint --show-vale-config
py-doc lint --check-engines
```

`lint.markdownlint` in `py-doc.yml` is commented out, because markdownlint runs in the container. Uncomment it once Docker works, and `.markdownlint.yaml` is used.

## Import a Word file or a deck

`py-doc import` turns a Word file or a PowerPoint deck into Markdown. Headings, lists, tables, bold and italic text, pictures and captions are kept, and a caption becomes a `[[CAPTION:Figure]]` or `[[CAPTION:Table]]` line. A deck also keeps its sections, columns, code, callouts and speaker notes.

```bash
py-doc import word/design_review.docx -o imported
# writes imported/design_review.md and imported/design_review/ (pictures)
py-doc docx imported/design_review.md        # builds it again: imported/design_review.docx

py-doc build deck
py-doc import build/deck.pptx -o imported    # imported/deck.md
py-doc slides imported/deck.md -t templates/sensor.pptx   # the same slides again
```

Without `-o`, the Markdown is written next to the input. `--force` replaces an existing `.md` file, and `--no-defloat-images` leaves floating Word pictures out instead of placing them inline. The deck's one equation is not imported, and a warning says so.

## Web site

`site:` in `py-doc.yml` publishes the guide, the datasheet and the architecture as a MkDocs site, from the same sources.

```bash
py-doc site init        # site/mkdocs.yml and site/docs/index.md, once
py-doc site build       # pages in site/docs/<document>/, the site in site/build
```

Each source file is a page, with its diagrams, callouts and captions. `site/mkdocs.yml` is yours to change: py-doc writes only the pages and `site/py-doc-nav.yml`, which `mkdocs.yml` takes in with `INHERIT`. Change `engine: mkdocs` to `engine: starlight` and use another `dir` for an Astro + Starlight site.

## Structurizr and C4

```bash
py-doc c4 check architecture/workspace.json
py-doc c4 export architecture/workspace.json -o c4-out -f markdown   # c4-out/markdown/*.md, no Docker
py-doc c4 export architecture/workspace.dsl -o c4-out -f png svg mermaid  # needs Docker
py-doc c4 lock                                  # pins the Structurizr Local image
py-doc c4 up architecture/workspace.dsl         # view and arrange the views in your browser; Ctrl+C stops it
py-doc c4 up architecture/workspace.dsl --detach   # or leave it running ...
py-doc c4 down                                  # ... and stop it later
```

`c4 up` opens `http://localhost:8080/workspace/1/diagrams`. Changes to `workspace.dsl` show when the page is reloaded. Layouts arranged in the diagram editor are saved to `workspace.json` beside it, and builds use them. The views here use `autoLayout`, so remove it from a view to arrange that view by hand.

Structurizr Local only answers requests for `localhost`, so the browser that draws the pictures shares Local's network. Pictures are drawn with Structurizr Local (`structurizr/structurizr local`, which replaces Structurizr Lite). The first picture pulls the image, which can take a while. `diagrams: {engine: source, format: plantuml}` in `py-doc.yml` is the other route: `structurizr-cli` writes PlantUML text from `architecture/workspace.dsl`, and it is drawn like any other diagram. Both routes need Docker. Without it, `py-doc c4 export architecture/workspace.json -f markdown` still writes the model as Markdown pages.

> **Note:** Generated pages and the export cache live in `.py-doc/` at the project root. It is ignored by Git.

## Try the features

- **Variables and conditions:** `py-doc build guide -f docx --var version=2.0 --condition internal=true`, then open the file. The `{{version}}` text, the file name and the internal-only paragraphs change.
- **Status templates:** the guide says `status: Draft`, so its Word file has a red "DRAFT" header. Change the status to `Released` in `docs/guide/00_overview.md` and the base template is used.
- **Templates:** the front matter in `docs/guide/00_overview.md` fills the `Replace-with-*` placeholders on the title page. The body goes where `[[INSERTCONTENT]]` stands.
- **Callouts, captions, page breaks, orientation, styles:** see `docs/guide/00_overview.md` and `docs/guide/02_design.md`. `[[STYLE:Lead Paragraph]]` applies a style the template defines.
- **Diagrams:** `docs/guide/02_design.md` has Graphviz, Mermaid and PlantUML blocks and a code include. `docs/guide/05_diagram_types.md` has the rest.
- **File names:** the guide is `guide-v1.0.docx` (`name: "{name}-v{version}"`) and the datasheet is `datasheet-1_0.docx` (`{version_safe}`). `py-doc build release-notes` takes its version from `git describe --tags --always` (`version: git`), so it needs a commit in this folder's repository.
- **Your own template:** edit `templates/make_templates.py` and run `python templates/make_templates.py`, or point `outputs.docx.template` in `py-doc.yml` at your own file and run `py-doc template check YOUR.docx --strict`.
- **Your own documents:** add Markdown files to `docs/`, list them under a new entry in `documents:` in `py-doc.yml`, and run `py-doc build NAME`.

## If something fails

- Exit status `2` means the environment: Docker is not running or the image is not built. Run `py-doc doctor`.
- Exit status `1` means a tool ran and failed. Its output is shown above the error.
- A diagram error names the file, the line and the tool's own message. `py-doc build --keep-going` lists every failing diagram together.
- If Structurizr Local does not answer, check that Docker is running and that port 8080 is free (`c4.port` in `py-doc.yml` changes it), then run `py-doc c4 down` and try again.
- `py-doc lint docs --strict` should report nothing for these files. If you change them, it names the file and line.
- Generated pages and caches live in `.py-doc/` at the project root. It is ignored by Git and safe to delete.
