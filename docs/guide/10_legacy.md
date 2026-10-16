---
title: Legacy build files
---

# Legacy build files

Before `py-doc.yml`, each document had its own YAML build file for the `createdocs` scripts: a `meta` block, a `cli` block and a list of `entries`. py-doc reads these files as they are, so old documents keep building while you move over. It also starts new documents in the same format and gives each one a unique number.

| Task | Command |
|---|---|
| Build one legacy file | `py-doc build --legacy FILE.yaml` |
| Start a new legacy document | `py-doc new` |
| Number an existing Markdown file | `py-doc new FILE.md` |
| Add existing documents to the number register | `py-doc new --scan` |
| Set where new numbers begin | `py-doc new --start N` |
| Turn legacy files into one `py-doc.yml` | `py-doc migrate PATH` |

## The legacy build file

```yaml
meta:
  title: "Build and Release Pipelines"
  author: "Mark Bacon"
  version: "1.0.0"
  date: "29 September 2026"
  description: "How the firmware is built, signed and released."
  document_number: "G460-TN-012"
  classification: "Confidential"

cli:
  emit-docx: true
  output: G460-TN-012-Build-and-Release-Pipelines.docx
  template: ../../DocScripts/Template.docx

entries:
  - file: G460-TN-012-build-and-release-pipelines.md
    heading_offset: 0
  - file: appendix.md
    section: Appendix
    heading_offset: 1
    page_break: true
```

Paths are relative to the build file. Every key py-doc reads:

| Key | What py-doc does with it |
|---|---|
| `meta.title`, `subtitle`, `author`, `date`, `version`, `status`, `description`, `classification`, `subject`, `keywords`, `category`, `company`, `toc_depth` | Document properties. They fill the template's `Replace-with-*` placeholders and the file properties |
| `meta.document_number` (or `doc_number`) | The document number: a property like the others, and the key the number register reads |
| `cli.output` | The output file. Its extension chooses the format when no `emit-*` switch is set: `.docx`, `.pptx`, `.pdf` or `.html` |
| `cli.emit-docx`, `emit-pptx`, `emit-pdf`, `emit-html` | Build that format. Several may be set |
| `cli.template` | A `.pptx` template goes to the PowerPoint output, any other to the Word output |
| `cli.no-template` | Ignore `cli.template` |
| `cli.css` | The stylesheet of the HTML output |
| `cli.toc-depth` | The depth of the contents list, when `meta.toc_depth` is not set |
| `entries[].file` | A Markdown source, in order |
| `entries[].heading_offset` | Push that file's headings down this many levels |
| `entries[].title`, or `section` | Replace the file's first heading with this text |
| `entries[].page_break` | Start that file on a new page |
| `entries[].include: false` | Leave the file out |
| `variables`, `conditions` | Values for `{{name}}` and `[[IF:]]` in the Markdown |

Some keys are accepted and ignored, each with one warning. The tool container supplies PlantUML and ditaa, so `plantuml-jar-path` and `ditaa-jar-path` are not needed. Nor are `keep-tmp`, `keep-temps` and `no-svg-to-png`. PDF is always built with XeLaTeX, so `pdf-from-docx` is ignored, and `-v` replaces `verbose`. `emit-md`, processed Markdown, is not supported, and an unknown key is reported, never dropped quietly.

The version is added to the output file name, as `createdocs` did: `G460-TN-012-Build-and-Release-Pipelines-1_0_0.docx`. With `status: Draft`, a template named `Template_Draft.docx` beside `Template.docx` is used when it exists.

## Building a legacy file

```bash
py-doc build --legacy G460-TN-012-build-and-release-pipelines.yaml
py-doc build --legacy G460-OV-001.yaml -f pptx     # only the PowerPoint output
```

`--legacy` reads the file the way `py-doc migrate` would, and builds it straight away. Nothing is written but the outputs. The keys it ignores are shown as warnings first. The other `py-doc build` options work too, such as `--var`, `--condition`, `--keep-going` and `--report`.

## Starting a new document

```bash
py-doc new                                                  # asks for everything
py-doc new -y --title "Meter Wakeup Behaviour" --type TN --classification Confidential
```

`py-doc new` writes a build file and its Markdown in the current folder, named after the number and the title: `G460-TN-013-Meter-Wakeup-Behaviour.yaml` and `.md`. The Markdown starts with the title as its heading. The date is today and the version is `0.1.0`. It asks, in this order:

| Question | Option | Default |
|---|---|---|
| Number prefix (only when the register is made, or when it lists `prefixes`) | `--prefix` | the register's `prefix` |
| Title | `--title` | none: it is needed |
| Type code | `--type` | empty |
| Word or PowerPoint | `--format` | `docx` |
| Author | `--author` | `git config user.name` |
| Classification | `--classification` | empty |
| Description | `--description` | empty |

A question is skipped when its option is given. `-y` asks nothing, and nothing is asked when there is no terminal, so a script must give `--title`. A file that is already there is never replaced. The build file has `cli.template` as a comment: set it to your template.

## Numbering an existing Markdown file

```bash
py-doc new notes/pump-control.md --type TN
```

Given a Markdown file, `py-doc new` writes only the build file, beside it, and gives the document the next number. The Markdown file is not renamed or changed, and the build file names it in `entries`. The answers start from what the file says about itself. The title comes from its front matter, else its first heading. The author, version, classification and description come from its front matter. An option still wins.

A file whose front matter already has a `document_number` is refused, and so is a file that a build file in the register already uses. Either way it has a number already.

## The number register

The numbers live in `doc-numbers.yml` at the repository root. `py-doc new` finds it from any folder below the root.

```yaml
prefix: G460                                      # the default prefix
prefixes: [G460, G470]                            # optional: the only prefixes allowed
types: [TN, OV, SP]                               # optional: the only type codes allowed
classifications: [Confidential, Internal, Public] # optional: the only classifications allowed
start: 100                                        # optional: where new numbers begin
documents:
  - number: G460-TN-012
    title: Build and Release Pipelines
    file: docs/notes/G460-TN-012-build-and-release-pipelines.yaml
```

Each document has three fields: its number, its title and its build file.

### How a number is made

A number is `[prefix-][type-]NNN`, such as `G460-TN-013`. Either the prefix or the type may be left out, giving `G460-013`, `TN-013` or `013`.

- **The prefix** defaults to the register's `prefix`, and `--prefix` changes it for one document.
- **The type** is asked for each document.
- **`NNN`** is one counter for every prefix and type. It is one more than the highest number in the register, so `G460-TN-013` and `G460-OV-013` cannot both be given out. It has at least three digits, more when an existing number has more.

### Allowed values

When the register has a `prefixes`, `types` or `classifications` list, the value must be one of it. Case does not matter, and the spelling in the list is used, so `tn` becomes `TN`. The wizard shows the list and asks again after a wrong or empty answer. A wrong option is an error that names the list. Without a list, anything goes.

### The first register

The first `py-doc new` in a repository makes the register. It adds the `document_number` of every legacy build file already below the root, so a new number cannot repeat an old one. Then it asks for the prefix.

### Adding existing documents and choosing where numbers begin

```bash
py-doc new --scan               # add the legacy build files that are not in the register yet
py-doc new --scan --start 100   # and begin new numbers at 100
```

Neither makes a document. `--scan` adds every legacy build file below the root that is not in the register yet, even when its number is taken. It lists each number used by more than one file as a clash. Fix clashes by hand: py-doc never renumbers a document. A second scan adds nothing new.

`--start N` is kept in the register as `start: N`. New numbers then begin at `N` and step over any number a document already has. They stay unique however the old numbers were given out. Without it, the next number is one more than the highest.

### Working with others

Commit `doc-numbers.yml` with each new document. If two people take a number on separate branches, Git then reports a conflict in the register when the second branch merges. Keep both entries and give one document the next free number.

## Writing legacy documents

Legacy documents use the same Markdown as the rest of py-doc: see [Writing](03_writing.md). The directives older documents rely on all work:

- `[[PAGEBREAK]]` on its own line starts a new page, or a new slide in a deck.
- `[[CAPTION:Figure]] text` or `[[CAPTION:Table]] text` on the line before or after a picture, diagram or table is its caption. A table caption stays on the page of its table in Word.
- `[[INCLUDE: file.md]]`, `[[IF: key]]`, `[[ENDIF]]`, `[[LANDSCAPE]]`, `[[PORTRAIT]]` and `[[STYLE:Name]]` work as described there.

## Moving to py-doc.yml

```bash
py-doc migrate docs/ --check      # report what would be migrated, write nothing
py-doc migrate docs/              # write py-doc.yml
py-doc migrate docs/ --backup     # also keep .bak copies of the originals and any old py-doc.yml
```

Each legacy file becomes one document in `py-doc.yml`, so folders, sources, templates and shared chapters keep their relations. A template used by every Word document is set once under `outputs`. YAML files that are not build files, such as `mkdocs.yml`, are listed as skipped. The originals are never changed or deleted. An existing `py-doc.yml` is not replaced unless you pass `--backup` or `--force`. `--from createdocs` names the legacy format: it is the default and, for now, the only one.

The report lists the keys that are ignored or have no equivalent, as above, so nothing is lost quietly.

The `Setup-DocTools.ps1` script that installed pandoc, TeX and the diagram tools on Windows is no longer needed: the tools run in the tool container. Use `py-doc setup` (Docker Engine in WSL), then `py-doc tools build` and `py-doc doctor`.

## A typical session

1. `py-doc new --scan` once in the repository, to make the register from the documents already there.
1. `py-doc new` in the folder for a new document, or `py-doc new FILE.md` for one already written.
1. Set `cli.template` in the new build file.
1. `py-doc build --legacy FILE.yaml` to build it.
1. Commit the Markdown, the build file and `doc-numbers.yml` together.
