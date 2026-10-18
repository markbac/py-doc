---
title: Projects
---

# Projects

A py-doc project is a folder with a `py-doc.yml` that lists its documents. `py-doc build`, `py-doc lint`, `py-doc c4` and `py-doc site` find the nearest `py-doc.yml` above the current folder, or take `--config`.

## Starting a project

`py-doc init` makes a project in the current folder, or in the folder it is given:

```bash
py-doc init                                   # asks for the name and the options, in a terminal
py-doc init docs-project --name "Pump Controller" --c4 --site mkdocs -y
```

| Option | What it adds |
|---|---|
| `--name NAME` | The project name (default: the folder name) |
| `--c4` | `architecture/workspace.dsl`, a C4 model, and a document generated from it |
| `--templates` | `templates/reference.docx` and `reference.pptx`: pandoc's own, with py-doc's callout styles in the Word one. They need the tool container |
| `--site mkdocs` or `--site starlight` | A site section in `py-doc.yml` and the site project in `site/` |
| `-y`, `--yes` | Ask nothing: what is not given is left out |

It always writes `py-doc.yml`, with a comment on every setting, and `docs/overview.md`, a first document with YAML front matter, and adds `build/`, `.py-doc/` and `.structurizr/` to `.gitignore`. In a terminal, `init` asks for what the options do not say, and with `--yes` or in a script it asks nothing. A folder that already has a `py-doc.yml` is refused and left as it is. A file that is already there is kept and named, never replaced. The new project lints clean and builds at once, and `init` ends with the commands to run next.

## The configuration file

One file describes documents, outputs, lint policy, C4 settings and the site. Paths are relative to the file. Every key is checked when the file loads, so a typo is an error that names its place, such as `documents.guide.sources[1].page_brek`.

```yaml
project:
  name: Technical documentation

outputs:                       # defaults for every document
  docx:
    template: templates/Template.docx
    dir: build                 # where documents go unless they set a path
  pptx:
    split_level: 2

documents:
  c4-guide:
    title: C4 Architecture Modelling
    author: Mark Bacon
    version: "1.0.4"
    document_number: GD-001
    status: Proposed
    keywords: [architecture, C4]
    sources:
      - index.md
      - file: 01-foundations.md
        heading_offset: 0      # shift every heading level (kept within 1 to 6)
        page_break: true       # start on a new page, or a new slide
        title: Foundations     # replaces the first heading, or adds one
        site_path: basics/foundations  # its page on a site (default: its place below the sources' folder)
      - {file: draft.md, include: false}
    variables: {version: "1.0"}
    conditions: {internal: false}
    outputs:
      docx: {path: build/guides/c4-guide.docx}
      pptx: {}                 # also build a deck
  api:
    sources:
      - api/index.md
      - {collection: endpoints, page_break: true}   # every file of a collection, in order

collections:                   # named sets of source files, for any document to take in
  endpoints: [api/endpoints/*.md]   # a pattern adds its files sorted by path

bundles:                       # several documents in one output, each starting on a new page
  handbook:
    title: Sensor handbook
    documents: [c4-guide, api]
    outputs: {pdf: {}}

site:                          # a web site of the documents: see the web sites chapter
  engine: mkdocs
  dir: site

lint:
  exclude: [drafts]
  rules:
    DOC001: error              # error, warning, info or off
    DOC002: off
  glossary:
    Kubernetes: [k8s]
  phrases:
    utilise: use
  acronyms:
    min_length: 3
    allowed: [SBOM]
    scope: document            # a definition in an earlier file of the same document counts
  limits:
    sentence_words: 40
```

- **Documents** join their sources in order. Properties come from the configuration, then from the first source's front matter, then from its first heading. A document builds the formats listed under `outputs`, or Word if none is listed.
- **Output options** per format: `template`, `allow_missing_template`, `name`, `placeholder_prefix`, `marker` and `toc` for Word, `split_level` and `footer` for PowerPoint, `template`, `toc`, `name` and `number_sections` for PDF and HTML, and `heading_numbers` for every format. A document's value overrides the default. The [outputs chapter](04_outputs.md) has the details.
- **Lint** settings extend the built-in glossary, phrases and allowed acronyms. The [linting chapter](07_lint.md) has every setting.
- **C4**: `c4.cli`, `c4.image` and `c4.port` say how Structurizr runs. See the [C4 chapter](06_c4.md).
- **Reports**: `reports.path` writes the JSON build report of every build.
- **Collections** name sets of source files: a list of files and patterns such as `docs/guide/*.md` or `docs/**/*.md`. A document takes one in with `{collection: name}`, which can carry `heading_offset` and `page_break`. The same file can be in several collections and documents.
- **Bundles** build several documents as one output, beside their own outputs. A bundle lists its `documents` and can set the same properties, `outputs`, `variables` and `conditions` as a document. Its own properties come first, then the first document's front matter. Each document after the first starts on a new page. `py-doc build handbook` builds one bundle. A bundle is not on the site unless `site.documents` names it.
- **Content generators** (`content.generators`) write Markdown files from other sources before the build, and **build** settings (`build.lint`, `build.lint_report`, `build.site`, `build.generate`) say what `py-doc build` does around the documents. Both are in [Generators, the build pipeline and analysis](11_pipeline.md).

## Building

```bash
py-doc build                      # every document
py-doc build c4-guide -f pptx     # one document, one format
py-doc build --var version=2.1 --condition internal=true
py-doc build --keep-going         # list every broken diagram, not just the first
py-doc build --lint --site        # generate, lint, build the documents, then the site
```

`--var` and `--condition` win over the values in the file. A document that fails does not stop the others: each failure is named, a summary follows, and the exit status is `1`. The generators, lint and site steps around the documents are described in [the build pipeline](11_pipeline.md#the-build-pipeline).

## Converting single files

`py-doc docx` and `py-doc slides` convert files without a `py-doc.yml`:

```bash
py-doc docx Technical_Specification.md -o Technical_Specification.docx
py-doc docx Technical_Specification.md -t Template.docx
py-doc docx docs/ -o dist/docx/              # a whole folder, structure kept
py-doc slides talk.md -o talk.pptx
py-doc slides talk.md -t Corporate.pptx --split-level 1
```

| Option | Commands | Description |
|---|---|---|
| `input` | both | A Markdown file, or a folder searched for `.md` and `.markdown` files in any capitalisation |
| `-o`, `--output` | both | The output file, or a folder. A folder (an existing one, or a path ending in `/`) gets `<name>.docx` or `<name>.pptx` inside it |
| `-t`, `--template` | both | A reference `.docx` or `.dotx` (Word), or `.pptx` or `.potx` (PowerPoint). `-r`, `--reference` is the old slides name |
| `--allow-missing-template` | both | Warn and use a blank document if the template file is missing (default: fail) |
| `--split-level N` | slides | Start a new slide at each heading up to level N (default 2) |
| `-q`, `-v` | both | Only warnings and errors, or debug detail |
| `--version` | both | Print the version |

A file that uses `[[IF:]]` needs its conditions defined, and only `py-doc build` can set them, so build such a file as a document of a `py-doc.yml`. For a folder of files:

- Hidden folders and `node_modules`, `venv`, `env`, `site-packages`, `__pycache__`, `dist`, `build` and `vendor` are skipped, and so is an output folder inside the input.
- One bad file does not stop the rest. Each failure is printed on stderr, a summary follows, and the exit status is `1` if anything failed.
- Two sources that would write the same output (`a.md` and `a.markdown`) are refused before anything is converted.
- The input is checked before any folder is created, so a typo leaves nothing behind.

The old commands `py-doc2docx`, `py-doc2slides` and `py-doclint` still work and print a one-line note naming their replacement. `-q` hides the note.

## File names and versions

- **File names**: the default is exactly the path given. `name: "{name}-{version_safe}"` on any output makes `guide-1_2_3.docx`. The fields are `{name}` (the file name it would have had), `{version}` (an error when there is no version) and `{version_safe}` (dots become underscores, no version gives `x_x_x`).
- **Version from Git**: `version: git`, in the configuration or the front matter, is `git describe --tags --always` of the project folder. Outside a repository, or without a commit, the build fails instead of inventing a version.
- **Status templates**: with `status: Draft` and `template: Template.docx`, `Template_Draft.docx` (then `Template_draft.docx`) is used when it exists, else the base template, and the log says which. The same rule applies to PowerPoint, LaTeX and HTML templates.

## Build report

`py-doc build --report build.json`, or `reports: {path: build.json}` in `py-doc.yml`, writes a JSON report of the build:

- the py-doc version, the image tag and id, and the version of each tool used;
- each document with its sources (words, sentences, paragraphs) and its outputs (size and SHA-256);
- every diagram: type, file, line, and whether the cache served it;
- template problems, and every warning with file and line.
 Keys are in a fixed order and there are no times unless you pass `--timestamps`, which also adds the render time of each diagram. The report is written when the build fails too, with `status: failed` and the error. Word and PowerPoint files contain the time they were written, so their checksums differ between builds. The schema is `py_doc/report.schema.json`.
