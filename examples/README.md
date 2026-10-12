# py-doc examples

A small project to run every part of `py-doc` against. Work from this folder:

```bash
cd examples
```

## What is here

- `py-doc.yml` -- three documents (`guide`, `deck`, `architecture`), output defaults, C4 and lint settings.
- `docs/` -- Markdown sources: front matter, variables, conditions, includes, callouts, diagrams, code includes, page breaks and orientation.
- `templates/company.docx` and `templates/company.pptx` -- templates with `Replace-with-*` placeholders, `[[INSERTCONTENT]]`, callout styles and slide layouts.
- `templates/make_templates.py` -- regenerates the templates and `word/design_meeting.docx`.
- `architecture/workspace.dsl` and `workspace.json` -- the same small Structurizr model. The JSON needs no Java or Docker.
- `vale-rules.yml` and `structure-rules.yaml` -- rule files used by `py-doc lint`.
- `word/design_meeting.docx` -- a Word file to try `py-doc import` on.

## Build the outputs

Each command writes into `build/`.

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
```

## Lint

```bash
py-doc lint docs                    # built-in rules, structure rules and C4 model rules
py-doc lint docs --engine vale      # Vale with the bundled PyDoc style
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
