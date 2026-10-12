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

What needs Docker: Word, PowerPoint, PDF and HTML output, every diagram type, drawing the views of a model, and exporting a `.dsl` workspace. What does not: `lint` with the built-in rules, `template check|show|diff|usage`, `import`, and `c4 check` and `c4 export -f markdown` on `architecture/workspace.json`.

## What is here

| Path | What it shows |
|---|---|
| `py-doc.yml` | Four documents, output defaults, per-document variables and conditions, file naming, the build report, C4 and lint settings. Every setting has a comment |
| `docs/guide/` | The guide, in four chapters: front matter, variables, conditions, includes, both callout spellings, captions, lists, task lists, footnotes, definition lists, maths, code includes, a landscape table, page breaks, links between chapters. `DRAFT.md` is listed with `include: false` |
| `docs/datasheet.md` | One example of each diagram type that needs only the container: blockdiag, ditaa, wavedrom, packetdiag, nwdiag, seqdiag, pikchr and vega-lite |
| `docs/slides.md` | The deck: slides at second-level headings, speaker notes, a diagram, a table, a page break |
| `docs/includes/` | Files pulled in with `[[INCLUDE:]]` and `[[INCLUDE-CODE:]]` |
| `templates/sensor.docx` | The Word template: logo, title page with `Replace-with-*` placeholders, header, footer with page numbers, callout styles, a `Lead Paragraph` style, `[[INSERTCONTENT]]` where the body goes |
| `templates/sensor_Draft.docx` | The same template with a red "DRAFT" header. A document with `status: Draft` uses it without being told to |
| `templates/sensor.pptx` | The PowerPoint template: coloured titles and a `{{VERSION}}` footer shape |
| `templates/doc.css` | The stylesheet for HTML output: `py-doc`'s own plus company colours |
| `templates/make_templates.py` | Regenerates the templates, the logo and `word/design_review.docx` |
| `architecture/workspace.dsl`, `workspace.json` | The same Structurizr model twice. The JSON needs no Java or Docker |
| `structure-rules.yaml`, `vale-rules.yml`, `.markdownlint.yaml` | Rule files used by `py-doc lint` |
| `word/design_review.docx` | A Word file to try `py-doc import` on |

The diagram types that are not shown here (`bytefield-svg`, `railroad`, `wireviz`, `actdiag`) work the same way. See the Diagrams section of the main README.

## Which command makes which output

| Command | Reads | Writes |
|---|---|---|
| `py-doc build guide` | `docs/guide/*.md`, `docs/includes/`, `templates/sensor.docx` (or `sensor_Draft.docx`), `templates/doc.css` | `build/guide-v1.0.docx`, `build/guide.pdf`, `build/guide.html` |
| `py-doc build datasheet` | `docs/datasheet.md` | `build/datasheet-1_0.docx`, `build/datasheet.pdf` |
| `py-doc build deck` | `docs/slides.md`, `templates/sensor.pptx` | `build/deck.pptx` |
| `py-doc build architecture` | `architecture/workspace.json`, `docs/includes/audience.md` | `build/architecture.docx`, `build/architecture.html` (chapters generated from the model) |
| `py-doc import` | `word/design_review.docx` | Markdown and pictures in `imported/` |

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

# PowerPoint deck, one slide per second-level heading
py-doc build deck                 # build/deck.pptx

# Architecture chapters generated from the C4 model
py-doc build architecture         # build/architecture.docx

# Everything in py-doc.yml, and a list of every failure at the end instead of the first one
py-doc build --keep-going
```

To convert a single file without `py-doc.yml`:

```bash
py-doc docx docs/guide/00_overview.md -o build/overview.docx --template templates/sensor.docx
py-doc slides docs/slides.md -o build/slides.pptx --template templates/sensor.pptx
```

## Templates

The Word template is pandoc's reference document, so its styles decide how everything looks. The file is built by `templates/make_templates.py`, which is the easiest place to see what a good template contains: the callout styles (`Div.note` to `Div.caution`), `Caption`, `Source Code`, headings, a title page with placeholders, and the `[[INSERTCONTENT]]` line.

```bash
py-doc template check templates/sensor.docx --strict
py-doc template check templates/sensor.pptx --strict
py-doc template show templates/sensor.docx
py-doc template diff templates/sensor.docx templates/sensor_Draft.docx
py-doc template usage word/design_review.docx
```

The placeholders the title page can use are `Replace-with-Title`, `-Author`, `-Version`, `-Document-Number`, `-Date`, `-Description` and `-Classification`. They are filled from the front matter of the first source, in the body, tables, headers and footers.

## Lint

```bash
py-doc lint docs                    # built-in rules, structure rules and C4 model rules
py-doc lint docs --engine vale      # Vale with the bundled PyDoc style
py-doc lint docs --format csv > issues.csv   # or --format github
py-doc lint --show-vale-config
py-doc lint --check-engines
```

`lint.markdownlint` in `py-doc.yml` is commented out, because markdownlint runs in the container. Uncomment it once Docker works, and `.markdownlint.yaml` is used.

## Import a Word file

```bash
py-doc import word/design_review.docx -o imported
# writes imported/design_review.md and imported/design_review/ (pictures)
```

## Structurizr and C4

```bash
py-doc c4 check architecture/workspace.json
py-doc c4 export architecture/workspace.json -o c4-out -f markdown   # c4-out/markdown/*.md, no Docker
py-doc c4 export architecture/workspace.dsl -o c4-out -f png svg mermaid  # needs Docker
py-doc c4 lock                                  # pins the Structurizr Local image
py-doc c4 up                                    # view the model in a browser
py-doc c4 down
```

Pictures are drawn with Structurizr Local (`structurizr/structurizr local`, which replaces Structurizr Lite). The first picture pulls the image, which can take a while. `diagrams: {engine: source, format: plantuml}` in `py-doc.yml` is the other route: `structurizr-cli` writes PlantUML text from `architecture/workspace.dsl`, and it is drawn like any other diagram. Both routes need Docker. Without it, `py-doc c4 export architecture/workspace.json -f markdown` still writes the model as Markdown pages.

> **Note:** Generated pages and the export cache live in `.py-doc/` at the project root. It is ignored by Git.

## Try the features

- **Variables and conditions:** `py-doc build guide -f docx --var version=2.0 --condition internal=true`, then open the file. The `{{version}}` text, the file name and the internal-only paragraphs change.
- **Status templates:** the guide says `status: Draft`, so its Word file has a red "DRAFT" header. Change the status to `Released` in `docs/guide/00_overview.md` and the base template is used.
- **Templates:** the front matter in `docs/guide/00_overview.md` fills the `Replace-with-*` placeholders on the title page. The body goes where `[[INSERTCONTENT]]` stands.
- **Callouts, captions, page breaks, orientation, styles:** see `docs/guide/00_overview.md` and `docs/guide/02_design.md`. `[[STYLE:Lead Paragraph]]` applies a style the template defines.
- **Diagrams:** `docs/guide/02_design.md` has Graphviz, Mermaid and PlantUML blocks and a code include. `docs/datasheet.md` has the rest.
- **File names:** the guide is `guide-v1.0.docx` (`name: "{name}-v{version}"`) and the datasheet is `datasheet-1_0.docx` (`{version_safe}`). `version: git` would take the version from `git describe`.
- **Your own template:** edit `templates/make_templates.py` and run `python templates/make_templates.py`, or point `outputs.docx.template` in `py-doc.yml` at your own file and run `py-doc template check YOUR.docx --strict`.
- **Your own documents:** add Markdown files to `docs/`, list them under a new entry in `documents:` in `py-doc.yml`, and run `py-doc build NAME`.

## If something fails

- Exit status `2` means the environment: Docker is not running or the image is not built. Run `py-doc doctor`.
- Exit status `1` means a tool ran and failed. Its output is shown above the error.
- A diagram error names the file, the line and the tool's own message. `py-doc build --keep-going` lists every failing diagram together.
- If Structurizr Local does not answer, check that Docker is running and that port 8080 is free (`c4.port` in `py-doc.yml` changes it), then run `py-doc c4 down` and try again.
- `py-doc lint docs --strict` should report nothing for these files. If you change them, it names the file and line.
- Generated pages and caches live in `.py-doc/` at the project root. It is ignored by Git and safe to delete.
