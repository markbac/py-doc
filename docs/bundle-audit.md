# Bundle audit

Findings from reading the remaining tools in `structurizr.zip`. Nothing was copied. Each tool is marked as covered, partly covered or not covered by `py-doc`, with the defects found in the original.

## Covered

### check_docx_styles.py

Covered by `py-doc template check` (Div.* callout styles, bold leaks, keep-with-next, Caption, InlineCode, code spell-check, language).

Defects in the original:

- The table style is hard-coded as `Table Grid,Eykon`, a company alias that python-docx cannot resolve, so the check always warns elsewhere. `py-doc` checks the plain name `Table Grid`.
- It exits 0 whatever it finds, so it cannot gate a build. `py-doc template check --strict` exits 1.

### check_pptx.py

Covered by `py-doc template check` for decks (fonts, empty placeholders, slide number placeholder).

Defects in the original:

- The slide number check has dead code (`"pptx.oxml.text.fld" in str(type(...))` followed by `pass`).
- The code-font spell-check heuristic warns on every run once, so it is noise. Not ported.
- Exit status is always 0.

### create_pptx.py, Convert_to_pptx.ps1, create_pptx.ps1

Covered by `py-doc build` with the `pptx` output: status templates (`naming.status_template`), version footer (`{{VERSION}}`), the `.fntdata` content type fix and Mermaid rendering.

Defects in the original:

- `_run` uses `shell=True` with a list, which breaks on paths with spaces or quotes on Linux and is a command injection risk on any platform.
- `Convert_to_pptx.ps1` looks for `Template.pptx` beside the script, and the `.ps1` wrappers source `..\scripts\_run.ps1`, which is not in the bundle.
- `Convert_to_pptx.ps1` passes the file as a positional argument, but `create_pptx.py` requires `--input`, so the batch script fails every file.
- Versioned file names replace dots by underscores (`1_0`), which differs from `createdocs`. `py-doc` uses one `name` pattern for all outputs.

### check_docs.py (docs-check)

Covered by `py-doc lint`: structure rules, caption rules, cross-file anchors, markdownlint (`lint/mdlint.py`), Vale with a derived config.

Defects in the original:

- Checking a single `.md` file skips the manifest, so cross-file anchor checks see only that file and report links to other files as broken. `py-doc lint` resolves anchors across the whole target.
- Vale is found on `PATH` or in the WinGet folder only, so a Linux host without it on `PATH` needs `--vale-bin`. `py-doc` also has a container copy.

### docx_style_inspector.py

`py-doc template show` lists styles and layouts, `template diff` compares two templates and `template usage` counts styles in a document. Not ported:

- Style definitions flattened through the `basedOn` chain.

Defects in the original: `STYLE_REFERENCES` names `Light List Accent 3`, which the code does not use, and the references name `createdocs` modules that no longer exist.

### check_docs.py output formats

The CSV report (`write_csv`) and the editor line format (`write_editor_format`) are covered by `py-doc lint --format csv|github`. The plain text output already has the `file:line:` form editors read.

## Structurizr scripts

Covered by `py-doc c4` (export through the container, Structurizr Local on a named network, headless diagram export, caching, model rules, image lock):

- `structurizr-container.py`, `structurizr-export.py`, `structurizr-local.py`, `structurizr-playground.py`, `export-diagrams.js`, `pylogkit.py`.

Not ported by design:

- `structurizr-local.py` builds a Maven plugin JAR from source. It is outside the Markdown pipeline and needs Java and Maven on the host.
- `structurizr-playground.py` runs `structurizr/playground`. It is a viewer only, and `py-doc c4 up` covers the Local viewer.
- `export-structurizr-diagrams.js` is an older copy of `export-diagrams.js` with `--no-sandbox` fixed on and no login support. `py-doc` uses the newer one.

Defects in the original:

- `structurizr-export.py` accepts `--js-password` on the command line, which exposes it in the process list. An environment variable would be safer.
- `export-diagrams.js` asks for `headless: 'new'`, which Puppeteer 24 no longer accepts. `py-doc` patches it to `headless: true`.
- `Readme.md.bak` is shipped in the bundle.

## Setup scripts

### setup-DocTools.ps1

Not needed: tools come from the Docker image (`py-doc tools build`). Defects in the original:

- It re-launches itself elevated for Graphviz, Inkscape and MiKTeX, and `exit $LASTEXITCODE` after `Start-Process` does not carry the elevated child's exit status, so a failed or cancelled install can look like success.
- It installs the global `@mermaid-js/mermaid-cli` without a version, so builds differ between machines.
- The minimum Pandoc version is `3.8.2.1`, which is not enforced anywhere else in the toolchain. `py-doc` pins the version in `tools.lock`.

### createdocs.ps1

A wrapper that sources `..\scripts\_run.ps1`, which is not in the bundle. Replaced by the `py-doc` command.

## Structurizr Lite and the new tooling

Structurizr Lite gets no more updates. `py-doc c4` now draws views with `structurizr/structurizr local`, the
tool the Structurizr documentation names as its replacement (the bundle's `structurizr-local.py` uses the same
image and command). Local reads only `workspace.dsl` or `workspace.json`, so a workspace with another name is
copied to a temporary folder first, and auto-save is off so drawing never changes the project.

Not changed yet: DSL export (`py-doc c4 export`, DSL as a source) still runs `structurizr-cli`, pinned in
`tools.lock`. The new consolidated tool (`structurizr.war`, Java 21, from `download.structurizr.com`) is its
successor. Moving to it needs its checksum recorded with `py-doc tools lock` and a Java 21 image.

## Follow-ups done

- `py-doc lint --format csv|github` covers the report formats of check_docs.py.
- `py-doc template diff A B` and `py-doc template usage FILE` cover the comparison and usage counts of docx_style_inspector.py. Style definitions flattened through the `basedOn` chain are not ported.
