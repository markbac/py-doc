---
title: Linting
---

# Linting

`py-doc lint` (also `py-doclint`) checks Markdown for writing quality. It runs on its own document tree, so code blocks, inline code, HTML, link destinations and front matter are never treated as prose. URLs and file names written as plain text are skipped.

```bash
py-doc lint docs/             # lint a folder (default: the current one)
py-doc lint docs/Guide.md     # lint one file
py-doc lint docs/ README.md   # several files and folders, as one report
py-doc lint docs/ --strict    # exit 1 if any warning or error is reported
py-doc lint . --exclude drafts
py-doc lint docs/ --format csv > issues.csv      # a spreadsheet (the summary goes to standard error)
py-doc lint docs/ --format github                # ::warning file=...,line=... annotations for GitHub Actions
py-doc lint docs/ --format json                  # every issue with rule, severity, file, line, column, message and suggestion
py-doc lint docs/ --format sarif --output build/lint.sarif   # SARIF 2.1.0 for code scanning
```

With `--format csv`, `json` or `sarif` the summary goes to standard error, so standard output can be read by a program. `--output` writes the issues to a file instead. A file that cannot be linted is in the JSON `errors` list and in the SARIF run as a failed notification, never left out.

With several targets, each Markdown file is checked once and the settings come from the `py-doc.yml` nearest the first one, unless `--config` names another.

A `[[CAPTION:Figure]]` or `[[CAPTION:Table]]` marker counts when it is on the line before or after the picture, table or diagram.

A poster's Markdown, named under `posters:` in `py-doc.yml`, is linted with every rule except the structure rules. Those are document conventions, such as a caption for every picture, that a poster does not follow. `py-doc build --lint` lints the posters it builds as well as the documents.

## Built-in rules

| Rule | Category | Default severity | What it reports |
|---|---|---|---|
| `DOC001` | Glossary | warning | A glossary term written differently from its canonical form, in any capitalisation (`mQTT`), plus listed misspellings (`Lw2m`) |
| `DOC002` | Style | warning | Wordy phrases such as `in order to`, also when wrapped over two lines, with a shorter wording suggested |
| `DOC003` | Acronym | info | The first use of an all-capitals acronym that is never defined, or is defined only later |
| `DOC004` | Directive | error | An `[[ENDIF]]` with nothing open, an `[[IF:]]` never closed, or an include whose file does not exist |
| `DOC005` | Structure | warning | A heading more than one level below the heading before it, such as a level 4 after a level 2 |
| `DOC006` | Link | warning | A link or picture whose file, relative to the Markdown file, is not there. Web addresses, `#anchors`, paths from the root and `{{variables}}` are not checked |
| `DOC007` | Accessibility | warning | A picture without alt text |
| `DOC008` | Style | info | A sentence longer than `lint.limits.sentence_words` words (default 40) |
| `DOC009` | Style | info | A heading longer than `lint.limits.heading_length` characters (default 80) |
| `DOC010` | Structure | info | A heading with the same text as an earlier one in the same section |
| `DOC011` | Structure | error | A code fence that is never closed, so the rest of the file is code |
| `DOC012` | Structure | warning | A document of `py-doc.yml` without a heading `lint.required_sections` asks for, in any of its files |
| `DOC013` | Terminology | info | A word written both hyphenated and closed up across the files linted together (`e-mail` and `email`). The rarer spelling is reported |

- **Required sections**: `lint.required_sections` maps a document to the headings it must have, or `*` to every document: `{'*': [Introduction, Scope], spec: [Requirements]}`. A document's own list replaces the `*` one. Case and a leading number such as `2.1` are ignored.
- **Glossary**: a wrong spelling listed under two terms, or a term listed as a wrong spelling of another, is a configuration error.
- **Acronym options** under `lint.acronyms`:
    - `min_length`: the shortest acronym checked (default 3).
    - `allowed`: acronyms added to the built-in list.
    - `require_definition`: default true. False reports only an acronym used before a later definition.
    - `scope`: `file` (the default) or `document`. With `document`, a definition in an earlier file of the same document in `py-doc.yml` counts, and each acronym is reported once per document.
    - `suggestion`: the advice shown, with `{acronym}` replaced; empty for none.

    The severity is `lint.rules.DOC003`.
- **Acronym definitions** are recognised in both orders, `Pre-Shared Key (PSK)` and `PSK (Pre-Shared Key)`, including mixed-case forms such as `LwM2M` and `IoT`. The words must spell out the acronym. Words in the built-in allow-list and glossary terms need no definition.
- **Folders**: hidden folders and `node_modules`, `venv`, `env`, `site-packages`, `__pycache__`, `dist`, `build` and `vendor` are skipped. `.md` and `.markdown` files are found in any capitalisation. Paths are printed relative to the working folder.
- **Exit status**: `0` when clean, or when only info is reported, or when warnings are reported without `--strict`. `1` for any issue the configuration calls an error, or with `--strict` and at least one warning. `2` when the target is missing or not Markdown, or when any file cannot be read, so an error is never mistaken for a clean result.
- **Limits**: issues from the built-in rules carry a line number but no column, because the document tree records lines only. Terms inside a URL, a dotted or slashed name such as `lwm2m/dtls`, or code are not checked.

## Structure rules and markdownlint

Two more checks join the style rules in one list, one summary line and one exit status. Errors fail the command and `--strict` fails on warnings, for every engine.

```yaml
lint:
  structure: structure-rules.yaml     # a file, or the list of rules written here
  markdownlint:
    config: .markdownlint.yaml        # a file, or the settings written here as a mapping
    severity: warning
```

- **Structure rules** are project conventions as data. The rule types are `manifest-file-exists`, `regex-line`, `blank-line-between`, `path-exists`, `balanced-markers`, `requires-caption` and `cross-file-anchors`. Code blocks and inline code are never searched. Each rule has an `id`, a `severity` and a `message`, and `enabled: false` switches it off. A mistake in a rule is a configuration error that names the rule. `py-doc lint --print-example-rules` prints an example set.
- **Cross-file anchors** work on the documents of `py-doc.yml`. All the files of a document share one set of heading anchors, as they do in pandoc. A repeated heading gets `-1`, `-2` and so on, and a `[x](#anchor)` link is checked against that set. Files pulled in with `[[INCLUDE:]]` count. A broken link and a repeated heading are reported with file and line.
- **markdownlint** runs in the tool container (`markdownlint-cli2`), only when `lint.markdownlint` is set, and its findings appear with rules `MD001` and so on. Without it, lint needs no container.

## Vale

`py-doc lint` can run [Vale](https://vale.sh) beside the built-in rules, and shows one list sorted by file and line. Vale is found on the `PATH` (or at `lint.vale.binary`). With `--engine vale` and no Vale on the host, the tool container's copy is used. If Vale is installed and `lint.vale.enabled` is `auto` (the default), both engines run. If it is not installed, one warning says so and the built-in rules run alone.

| Option | Effect |
| --- | --- |
| `--engine auto` | Built-in rules and Vale, when Vale is installed (default) |
| `--engine builtin` | No Vale |
| `--engine vale` | Vale replaces the text rules `DOC001` to `DOC003`. Structure rules and markdownlint still run. Missing Vale exits with status 2 |
| `--show-vale-config` | Print the `.vale.ini` py-doc generates, and the rules it wrote |
| `--check-engines` | Say whether Vale is found, its version (3.0 or newer is needed) and its folder |
| `--sync` | Run `vale sync` for `lint.vale.packages`. This is the only step that uses the network |

A Vale alert that is an `error` fails the command, and `--strict` fails on warnings, as for the built-in rules. `suggestion` becomes `info`. A Vale crash, bad output or a missing package is an error on every file (exit status 2), never a clean result. Vale's `PyDoc.Terms` and `PyDoc.Wordy` rules repeat `DOC001` and `DOC002`, so the Vale copy is dropped when the built-in rule reports the same line.

```yaml
lint:
  vale:
    enabled: auto             # auto, true or false
    binary: vale              # if not on the PATH
    min_alert_level: suggestion
    packages: [write-good]    # downloaded by `py-doc lint --sync`
    spelling: en-GB           # en-GB, en-US or off
    rules:
      PyDoc.SentenceLength: {level: warning, max: 30}
      PyDoc.PassiveVoice: off
      write-good.Weasel: error
    terms:                    # added to lint.glossary
      Kubernetes: [k8s, kube]
    avoid:
      - {pattern: "\\bsimply\\b", message: "Do not say 'simply'.", level: warning}
    ignore: ["CHANGELOG.md", "docs/generated/**"]
    rules_file: [vale-rules.yml]  # shared rules; later files override earlier ones, inline keys override all
    config: .vale.ini         # use your own file instead: the keys above are then ignored
```

py-doc writes the configuration, the `PyDoc` style and a vocabulary of your glossary terms into `.py-doc/vale` (it ignores itself in Git). `lint.glossary` and `lint.phrases` feed both engines. Every key is checked when `py-doc.yml` loads, and a bad rule id, level or pattern is named by its place (`lint.vale.rules.PyDoc.Typo`). `src/py_doc/lint/vale.schema.json` is a JSON schema for the section.

| Rule in the `PyDoc` style | Default | Why |
| --- | --- | --- |
| `SentenceLength` (`max` 30) | warning | Long sentences are hard to follow |
| `ParagraphLength` (`max` 150) | info | Long paragraphs hide the point |
| `PassiveVoice` | info | Say who does the action |
| `WeaselWords` | info | Vague words weaken a statement |
| `Repeated` | error | "the the" is always a typing slip |
| `DoubleSpace` | warning | One space between words |
| `HeadingPunctuation` | warning | No full stop at the end of a heading |
| `HeadingCase` | info | Sentence case in headings |
| `Placeholders` | warning | Unfinished-work markers and dummy Latin text must not reach a release |
| `Spelling` | warning | British spelling by default, American with `en-US` |
| `Terms`, `Wordy`, `Redundant` | warning | Generated from `lint.glossary` and `lint.phrases` |
| `Acronyms` | info | Spell out an acronym at first use |
| `Avoid1`, `Avoid2`, ... | as set | Generated from `lint.vale.avoid` |

Skipped heading levels and duplicate headings are not Vale's job: use the structure rules and markdownlint (`MD001`, `MD024`). Vale's Markdown handling skips code, front matter and link destinations, and py-doc tells it to ignore `[[directives]]` and `{{variables}}`. Other well-known styles (`Microsoft`, `Google`, `write-good`, `proselint`) can be added by name under `packages`.

Installing Vale: `brew install vale`, `winget install errata-ai.Vale` or `scoop install vale` on Windows, or a release from the Vale site. To move an existing `.vale.ini`, put its `MinAlertLevel`, `Packages` and per-rule levels under `lint.vale` as shown, or keep the file and point `config:` at it.

## From Python

```python
from py_doc.lint import DocLinter

report = DocLinter().lint_path("docs")
for issue in report.issues:
    print(issue)  # docs/Guide.md:12: warning DOC001 [Glossary] ...
print(report.files_scanned, "files scanned,", len(report.errors), "could not be read")
```
