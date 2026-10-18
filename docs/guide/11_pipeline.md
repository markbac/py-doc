---
title: Generators, the build pipeline and analysis
---

# Generators, the build pipeline and analysis

## Content generators

A generator writes a Markdown file from another source before anything reads the sources. Examples are a glossary from a list of terms, an index of the documents, or a table of an API's operations. A document lists the file it writes like any other source. `py-doc build` and `py-doc site` run the generators first, and `py-doc generate` runs them on their own.

```yaml
content:
  generators:
    - {type: glossary, source: glossary.yml, output: gen/glossary.md}
    - {type: documents, output: gen/documents.md}
    - {type: requirements, sources: ["docs/requirements/*.md"], output: gen/trace.md}
    - {type: openapi, source: api/openapi.yaml, output: gen/api.md}
    - {type: command, run: [python, tools/release_table.py], output: gen/releases.md}

documents:
  reference:
    sources: [gen/glossary.md, gen/trace.md, gen/api.md]
```

```bash
py-doc generate             # every generator
py-doc generate glossary    # one, by name (default: the output's file name without .md)
py-doc generate --list      # the generators of py-doc.yml and the types there are
```

Each generator has a `type`, an `output` and the options of its type. Paths are relative to `py-doc.yml`. A file is written only when its text changes, so a site or a build tool that watches files is not woken for nothing.

| Type | Options | What it writes |
|---|---|---|
| `glossary` | `source` (a YAML or JSON file of term and definition), `title` | A table of the terms, sorted. Without a source: the `lint.glossary` terms and the spellings to avoid |
| `documents` | `documents` (default: all), `link` (`source`, or a format such as `pdf`), `title` | A table of the documents with their number, version and status, each linked |
| `toc` | `document`, `depth` (default 3), `title` | The headings of a document as a nested list of links |
| `adr-index` | `source` (a folder), `title` | Number, title, status and date of each architecture decision record. The status comes from the front matter, a `Status:` line or the paragraph under a Status heading |
| `requirements` | `sources` (files and patterns), `pattern` (default: letters, a hyphen and two or more digits, such as `FR-001`), `title` | A traceability table: where each identifier is defined (the first cell of a table row, or a heading) and every other place that names it |
| `openapi` | `source`, `engine`, `html`, `validate`, `ruleset`, `samples`, `heading_offset`, `title` | The reference documentation of an OpenAPI or Swagger description, made by Redocly and Widdershins. See [API reference documentation](#api-reference-documentation) |
| `asyncapi` | `source`, `engine`, `html`, `heading_offset`, `title` | The reference documentation of an AsyncAPI description, made by the AsyncAPI generator. See [API reference documentation](#api-reference-documentation) |
| `python-api` | `source` (a package folder or a module), `private`, `title` | Each module, class, function and method with its signature and the first paragraph of its docstring. The code is read, never imported |
| `diagram` | `source`, `language` (default: from the file's extension), `caption`, `title` | A Mermaid, PlantUML, Graphviz or D2 file as a fenced block, which the build draws like any diagram |
| `command` | `run` (the program and its arguments, as a list), `timeout` (seconds, default 300) | What the program writes to standard output. It runs in the project folder, with no shell |
| `python` | `callable` (`module:function`) | What your function returns. It is called with the generator's settings and the project |

## API reference documentation

The `openapi` and `asyncapi` generators make the reference documentation of an API from its YAML or JSON description, with the standard tools of each, in the tool container:

| Generator | Checked by | Markdown by | HTML page by |
|---|---|---|---|
| `openapi` | `redocly lint` | `redocly bundle`, then Widdershins | Redoc (`redocly build-docs`) |
| `asyncapi` | The AsyncAPI parser | The AsyncAPI generator with `@asyncapi/markdown-template` | `@asyncapi/html-template` |

```yaml
content:
  generators:
    - type: openapi
      source: api/openapi.yaml       # may $ref other files: Redocly bundles them into one first
      output: gen/rest-api.md
      heading_offset: 1              # a chapter of a larger document
      html: site/docs/api/rest.html  # also a Redoc page, here in the MkDocs content folder
    - type: asyncapi
      source: api/asyncapi.yaml      # AsyncAPI 2 or 3
      output: gen/events.md
      html: site/docs/api/events.html
```

- **What the Markdown holds**: for OpenAPI, the servers, authentication, and each operation by tag with its parameters, request body, example responses and response codes, then every schema with its properties. For AsyncAPI, the servers, each channel and operation, and each message with its headers, payload and examples.
- **Checking**: an OpenAPI description is linted with Redocly's `minimal` rules first, and an error stops the build. `ruleset` picks `recommended`, `recommended-strict` or `spec` instead, and `validate: false` skips it. An AsyncAPI description that the parser rejects always stops the build.
- **Code samples**: Widdershins writes none by default, because a document is read rather than run. `samples: [shell, python, javascript]` adds them.
- **For Word and PDF**: the tools write for web pages, so py-doc turns their HTML headings into Markdown headings and their asides into callouts. `heading_offset` moves every heading down, and `title` replaces the top one.
- **HTML pages**: `html` writes the standalone Redoc or AsyncAPI page too. In the content folder of a site it is published as it is, and `site.pages` can add it to the navigation.
- **Without the container**: `engine: summary` writes only an overview (the operations or channels in a table) with no tool.

The [examples](../../examples/README.md) build both from the sample descriptions in `examples/docs/includes/apis`.

Mermaid and PlantUML written in a fenced block need no generator: the build draws them. A package can add generator types through the `py_doc.generators` entry point group, so py-doc does not depend on its tools. Each is a function that takes the generator's settings and the project and returns Markdown.

## The build pipeline

`py-doc build` runs these steps in order. A failed step stops the ones after it, except that every document is tried:

1. **Configuration**: `py-doc.yml` is read and checked.
2. **Generators**: `content.generators` write their files. A build of named documents runs only the generators whose output is one of their sources. `--no-generate` or `build.generate: false` skips them.
3. **Lint**: with `build.lint: on`, `--lint`, `build.lint: strict` or `--strict`, the sources of the documents being built are linted first. Files that generators write are left out, because the project's writing rules are for the files people write. An error (or, when strict, a warning) stops the build before anything is written. `--no-lint` skips it.
4. **Documents and bundles**: every document named, or all, in every format asked for.
5. **Site**: with `build.site: true` or `--site`, the pages are written and the site is built, every target of `site.targets`.
6. **Outputs**: every file the build wrote is there and is not empty.

```yaml
build:
  lint: on                         # off (the default), on, or strict
  lint_report: build/lint.sarif    # also write the lint issues here: .sarif, .json or .csv
  site: true                       # build the site after the documents
```

```bash
py-doc build --strict --lint-report build/lint.sarif --report build/report.json
```

The JSON build report lists the steps that ran, with `ok`, `failed` or `skipped`, beside the documents, diagrams and tools. In CI, upload the SARIF file to code scanning, or lint with `--format github` for annotations on the changed lines. The exit status is not zero when any step fails.

## Checking a project

`py-doc check` finds what would stop a build without building: a source or template that is not there, a site section without its site project, and every lint error. It needs no container unless markdownlint is set.

```bash
py-doc check                  # the project and the writing
py-doc check --strict         # fail on lint warnings too
py-doc check --no-lint        # the project only
py-doc check --format sarif --output build/check.sarif
```

## Statistics

`py-doc stats` counts the words of prose, the headings, code blocks, tables, pictures and links of each document, or of the files and folders named. Code, link targets and front matter are not words. `--lint` adds the lint issues of each.

```bash
py-doc stats
py-doc stats docs/guide README.md --lint
py-doc stats --format json
```

## Comparing versions

`py-doc diff` compares two versions of a document section by section, not line by line. A section is a heading and the text up to the next heading, named by the headings above it, such as `Install > Windows`. Rewrapping a paragraph is not a change.

```bash
py-doc diff old/guide.md docs/guide.md    # two files
py-doc diff --rev main                    # every source of py-doc.yml against a Git revision
py-doc diff --rev v1.0 docs/guide         # the Markdown below a folder
py-doc diff --rev HEAD~1 --format json --exit-code
```

Each change is one of:

| Change | Meaning |
|---|---|
| `added` | A section that was not there, with its number of words |
| `removed` | A section that is gone |
| `renamed` | The same text under a new heading |
| `moved` | A section now in another place among the others, or under another parent |
| `changed` | The same heading with other text, with the words added and removed |

`--exit-code` exits with status `1` when anything changed, for a check that a release changed no documents.
