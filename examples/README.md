# py-doc examples

A small project to try every part of `py-doc` on: Markdown sources, a `py-doc.yml`, Word and PowerPoint templates, lint rules and a Structurizr model. Copy the folder and change it into your own project.

## Before you start

1. Install `py-doc` (Python 3.10 or later) from the repository root:

    ```bash
    pip install -e .
    ```

1. Build the tool image once. It holds pandoc, Mermaid, PlantUML, Graphviz, xelatex, Inkscape and Structurizr, so nothing else needs installing. Docker must be running (on Windows, Docker in WSL).

    ```bash
    py-doc tools build        # slow the first time
    py-doc doctor             # checks that the image works
    ```

1. Work from this folder. `py-doc` finds `py-doc.yml` here and writes to `build/`:

    ```bash
    cd examples
    ```

What needs Docker: Word, PowerPoint, PDF and HTML output, Mermaid, PlantUML and Graphviz diagrams, and exporting a `.dsl` workspace. What does not: `lint` (built-in rules), `template check|show|diff|usage`, `import`, and `c4 check|export -f markdown` on `architecture/workspace.json`.

## What is here

- `py-doc.yml` -- three documents (`guide`, `deck`, `architecture`), output defaults, C4 and lint settings.
- `docs/` -- Markdown sources: front matter, variables, conditions, includes, callouts, diagrams, code includes, page breaks and orientation.
- `templates/company.docx` and `templates/company.pptx` -- templates with `Replace-with-*` placeholders, `[[INSERTCONTENT]]`, callout styles and slide layouts.
- `templates/make_templates.py` -- regenerates the templates and `word/design_meeting.docx`.
- `architecture/workspace.dsl` and `workspace.json` -- the same small Structurizr model. The JSON needs no Java or Docker.
- `vale-rules.yml` and `structure-rules.yaml` -- rule files used by `py-doc lint`.
- `word/design_meeting.docx` -- a Word file to try `py-doc import` on.

## Which file makes which output

| Command | Reads | Writes |
|---|---|---|
| `py-doc build guide` | `docs/00_overview.md` to `03_operations.md`, `docs/includes/`, `templates/company.docx` | `build/guide-v1.0.docx`, `build/guide.pdf`, `build/guide.html` |
| `py-doc build deck` | `docs/slides.md`, `templates/company.pptx` | `build/deck.pptx` |
| `py-doc build architecture` | `architecture/workspace.json`, `docs/includes/audience.md` | `build/architecture.docx` (chapters generated from the model) |
| `py-doc import` | `word/design_meeting.docx` | Markdown and pictures in `imported/` |

Output names, templates, variables and conditions are set in `py-doc.yml`. The comments in that file explain each setting.

## Build the outputs

Each command writes into `build/`. Run them in this order the first time.

```bash
# Word, PDF and HTML of the guide (the formats in py-doc.yml)
py-doc build guide

# One format at a time
py-doc build guide -f docx        # build/guide-v1.0.docx
py-doc build guide -f pdf         # build/guide.pdf
py-doc build guide -f html        # build/guide.html

# The internal version of the guide, with another version number
py-doc build guide -f docx --condition internal=true --var version=1.1

# PowerPoint deck, one slide per second-level heading
py-doc build deck                 # build/deck.pptx

# Architecture chapters generated from the C4 model
py-doc build architecture         # build/architecture.docx

# Everything in py-doc.yml
py-doc build
```

The Mermaid and PlantUML blocks in `docs/02_design.md` need the Docker image: run `py-doc tools build` once.

To convert a single file without `py-doc.yml`:

```bash
py-doc docx docs/00_overview.md -o build/overview.docx --template templates/company.docx
py-doc slides docs/slides.md -o build/slides.pptx --template templates/company.pptx
```

## Templates

```bash
py-doc template check templates/company.docx --strict
py-doc template check templates/company.pptx --strict
py-doc template show templates/company.docx
py-doc template diff templates/company.docx word/design_meeting.docx
py-doc template usage word/design_meeting.docx
```

## Lint

```bash
py-doc lint docs                    # built-in rules, structure rules and C4 model rules
py-doc lint docs --engine vale      # Vale with the bundled PyDoc style
py-doc lint docs --format csv > issues.csv   # or --format github
py-doc lint --show-vale-config
py-doc lint --check-engines
```

## Import a Word file

```bash
py-doc import word/design_meeting.docx -o imported
# writes imported/design_meeting.md and imported/design_meeting/ (pictures)
```

## Structurizr and C4

```bash
py-doc c4 check architecture/workspace.json
py-doc c4 export architecture/workspace.json -o c4-out -f markdown   # c4-out/markdown/*.md, no Docker
py-doc c4 export architecture/workspace.dsl -o c4-out -f png svg mermaid  # needs Docker
py-doc c4 lock                                  # pins the Structurizr Lite image
py-doc c4 up                                    # view the model in a browser
py-doc c4 down
```

> **Note:** Generated pages and the export cache live in `.py-doc/` at the project root. It is ignored by Git.

## Try the features

- **Variables and conditions:** `py-doc build guide -f docx --var version=2.0 --condition internal=true`, then open the file. The `{{version}}` text, the file name and the internal-only paragraphs change.
- **Templates:** the front matter in `docs/00_overview.md` fills the `Replace-with-*` placeholders on the title page of `templates/company.docx`. The body goes where `[[INSERTCONTENT]]` stands.
- **Callouts, captions, page breaks, orientation:** see `docs/00_overview.md` and `docs/02_design.md`.
- **Diagrams:** `docs/02_design.md` has Graphviz, Mermaid and PlantUML blocks and a code include.
- **Your own template:** edit `templates/make_templates.py` and run `python templates/make_templates.py`, or point `outputs.docx.template` in `py-doc.yml` at your own file and run `py-doc template check YOUR.docx --strict`.
- **Your own documents:** add Markdown files to `docs/`, list them under a new entry in `documents:` in `py-doc.yml`, and run `py-doc build NAME`.

## If something fails

- Exit status `2` means the environment: Docker is not running or the image is not built. Run `py-doc doctor`.
- Exit status `1` means a tool ran and failed. Its output is shown above the error.
- `py-doc lint docs --strict` should report nothing for these files. If you change them, it names the file and line.
- Generated pages and caches live in `.py-doc/` at the project root. It is ignored by Git and safe to delete.
