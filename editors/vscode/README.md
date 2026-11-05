# py-doc Live Preview for VS Code

Writing tools for documents, slide decks and posters written for [markbac/py-doc](https://github.com/markbac/py-doc):

- **Live preview**: py-doc's own output beside the editor, rebuilt on every save.
- **Highlighting**: py-doc's directives, rich tables, callouts, fenced divs and attributes, and the inside of every diagram fence and poster block.
- **Folding**: conditions, blocks, landscape sections, rich tables and fenced divs fold like headings.
- **Snippets**: a rich table, a callout, a condition, a diagram and the rest, a few keys away.

## Install

The extension is not on the Marketplace yet, so it is built from this repository. You need [Node.js](https://nodejs.org/) 18 or later and VS Code 1.75 or later.

On Windows, `scripts\update.ps1` at the root of the repository does it for you. When VS Code is installed, the script builds the extension and installs it, then installs it again after a pull that changed it. To do only that step:

```powershell
.\scripts\install-vscode-extension.ps1
```

By hand, on any platform, build the file and install it:

```bash
cd editors/vscode
npm ci
npx @vscode/vsce package
```

That writes `vscode-py-doc-preview-<version>.vsix`. Install it from the command line:

```bash
code --install-extension vscode-py-doc-preview-2.3.0.vsix
```

Or in VS Code: open the Extensions view (`Ctrl+Shift+X`), click **...** at its top, choose **Install from VSIX...** and pick the file. To update, build and install the new file the same way. To remove it, find **py-doc Live Preview** in the Extensions view and click **Uninstall**.

Highlighting, folding and snippets work as soon as the extension is installed. The live preview also needs:

- py-doc itself: `pip install -e .` at the root of this repository, or the `py-doc` of a virtual environment (see [Settings](#settings)).
- Docker, which draws the diagrams. `py-doc doctor` checks that everything works.

To recommend the extension to everyone who opens a project, add it to the project's `.vscode/extensions.json`:

```json
{
  "recommendations": ["py-doc.vscode-py-doc-preview"]
}
```

## Quick start

1. Open a py-doc Markdown file, such as `editors/vscode/examples/sample.md`.
1. Look at the colours: directives such as `[[PAGEBREAK]]`, callouts such as `> [!NOTE]` and the diagram fences are highlighted.
1. Type `listtable`, press `Ctrl+Space` and then `Enter`: a rich table is inserted. `Tab` moves from one field to the next.
1. Click the eye button in the editor title bar: the live preview opens beside the editor. Save, and it rebuilds.

## Live preview

Open a py-doc Markdown file and click the eye button in the editor title bar, or run **py-doc: Open Live Preview** from the Command Palette (`Ctrl+Shift+P`). The preview opens beside the editor and reloads each time you save.

- **Documents** (`py-doc docx file.md --watch`): rebuilds `file.docx` on save and shows its HTML twin, with every diagram, MathML and page breaks shown as dashed lines. A `.docx` open in Word is left as it is, with a warning, and the preview still updates.
- **Slide decks** (`py-doc slides deck.md --watch`): rebuilds `deck.pptx` and shows its HTML deck, split where PowerPoint splits it, with columns. Press `o` for every slide, and `p` for the presenter view with the speaker notes.
- **Posters** (`py-doc poster poster.md --watch`): rebuilds the self-contained poster page.

The twins are written to `.py-doc/preview/` below the file's folder, so no file of yours is overwritten. py-doc's output is in the **py-doc live preview** output channel (**View > Output**). When a save does not build, the preview keeps the last good page with the error across its top, and VS Code shows the error as a warning.

The eye button chooses the command from the file itself:

- **Poster**: the front matter has a poster setting (`paper`, `byline`, `orientation`, `theme`, `columns`, `width`, `colours`, `palette`, `logo`, `embed_fonts`).
- **Slides**: the front matter has `split_level` or a `format` of `slides`/`pptx`, or the body has `:::: columns`, `::: notes`, `::: incremental` or `<!-- notes: -->` outside code blocks.
- **Word document**: anything else.

To choose the format yourself, use **py-doc: Open Live Word Document / Presentation / Poster Preview**. One preview runs at a time: opening another stops the one already running, and **py-doc: Stop Live Preview Server** stops it. While a preview runs, switching to another Markdown file moves the preview to it (turn this off with `pydoc.watch.followActiveEditor`).

VS Code's own Markdown preview (`Ctrl+Shift+V`) still works, but shows plain Markdown: py-doc's blocks and markers need the live preview.

## Highlighting

Every Markdown file is highlighted, with no setting to turn on. The colours come from your colour theme, so they follow it in light and dark. Code blocks and inline code are left as code: a directive shown in an example is not highlighted as one.

### py-doc in Markdown

| What | Example | Shown as |
|:---|:---|:---|
| Directives, at the start of a line | `[[INCLUDE: a.md]]`, `[[IF: internal]]`, `[[CAPTION:Table]] Pins` | A keyword and its argument |
| Variables | `{{version}}` | A variable |
| Callouts | `> [!NOTE]`, `> **Warning:**` | A keyword |
| Fenced divs | `::: {.pagebreak}`, `:::: columns`, `:::` | Punctuation, classes and attributes |
| Attributes | `[text]{custom-style="Highlight Yellow"}`, `![](a.png){width=50%}`, `## Title {#id}` | Ids, classes and `key=value` pairs |

### Rich tables

A `[[LISTTABLE]]` and the rows right after it are highlighted cell by cell:

| What | Example |
|:---|:---|
| The marker and its options | `[[LISTTABLE: header, widths=8,92]]` |
| Cell separators | `\|` |
| Paragraph breaks | `<br>` |
| Bullets and numbered items | `<br>- item`, `<br>1. item` |
| Merged cells | a cell of only `<` or `^` |
| Cell colour and alignment | `{bg=E8F5E9 valign=middle}` |
| Blocks | `[[BLOCK: wiring]]` |

Bold, italic, links and the rest of Markdown inside a cell keep their usual colours. The table ends at the first line that does not start with `|`.

### Diagram fences and poster blocks

The inside of every fence py-doc draws is highlighted in the language of the fence. The attributes on the fence line, such as `width="100%"` or `cols=3`, are highlighted too. A diagram written `:::mermaid` … `:::`, the form py-doc also accepts for every diagram language, is highlighted the same way.

| Fences | Highlighted as |
|:---|:---|
| `mermaid` | Mermaid: diagram types, keywords, arrows, edge labels, colours, `%%` comments |
| `dot`, `graphviz`, `blockdiag`, `seqdiag`, `actdiag`, `nwdiag`, `packetdiag`, `rackdiag` | DOT: graph keywords, attributes, edges, strings, comments |
| `plantuml`, `puml` | PlantUML: `@startuml`, element keywords, arrows, stereotypes, colours, `'` comments |
| `bpmnt` | bpmn-text: see [BPMN files](#bpmn-files) |
| `vega`, `vega-lite` | JSON, with VS Code's own grammar |
| `wavedrom` | JavaScript, with VS Code's own grammar |
| `wireviz` | YAML, with VS Code's own grammar |
| `bytefield-svg` | Clojure, with VS Code's own grammar |
| Poster blocks (`chart`, `cards`, `steps`, `gauge` and the other blocks), `plot`, `circuit`, `chess`, `music`, `abc`, `pikchr`, `railroad` and the science fences (`molecule`, `smith` and the rest) | py-doc's written form: `key:` lines, `key=value` options, `a \| b \| c` cells, icons such as `tabler:server`, numbers with units, colours, strings, `#` comments |
| `ditaa` | Left as it is: it is a drawing |

The Mermaid, DOT and PlantUML grammars are the extension's own, so they work without other extensions. They cover what documents use most, not every corner of each language. A dedicated extension for one of these languages can be installed beside this one and highlights that language's own files. If it also highlights the fences in Markdown, VS Code uses one of the two grammars for them.

### BPMN files

`.bpmnt` files and ```` ```bpmnt ```` fences in Markdown are highlighted as the [bpmn-text](https://github.com/markbac/bpmn-text) notation: keywords, event types, flows and their labels, branch labels, `@` IDs, attributes, strings, `doc` text and comments. `Ctrl+/` toggles `#` comments in a `.bpmnt` file. py-doc draws the fences as BPMN diagrams, and `py-doc lint` reports their mistakes.

## Folding

These fold like headings, with the arrow in the gutter or `Ctrl+Shift+[` and `Ctrl+Shift+]`:

- `[[IF: key]]` or `[[NOT: key]]` to its `[[ENDIF]]`, nested ones too
- `[[BLOCK: name]]` to `[[ENDBLOCK]]`
- `[[LANDSCAPE]]` to `[[PORTRAIT]]`
- a `[[LISTTABLE]]` and its rows
- a fenced div, from `::: name` or `::: {...}` to its closing `:::`

Nothing inside a code fence folds. `Ctrl+K Ctrl+0` folds everything, headings included, and `Ctrl+K Ctrl+J` unfolds it all.

## Snippets

Type a snippet's prefix and press `Ctrl+Space`, then `Enter`. Or run **Snippets: Insert Snippet** from the Command Palette and pick from the list. After inserting, `Tab` moves to the next field to fill in, and `Shift+Tab` back.

| Prefix | Inserts |
|:---|:---|
| `listtable` | A captioned `[[LISTTABLE]]` with a header row |
| `block` | `[[BLOCK: name]]` ... `[[ENDBLOCK]]`, for a diagram or table in a cell |
| `cellstyle` | `{bg=E8F5E9 valign=middle}`, at the start of a table cell |
| `note`, `tip`, `important`, `warning`, `caution` | A callout of that kind |
| `caption-figure`, `caption-table` | A numbered caption line |
| `include`, `include-code` | `[[INCLUDE: file.md]]`, `[[INCLUDE-CODE: file.py]]` |
| `if`, `not` | A condition with its `[[ENDIF]]` |
| `pagebreak` | `[[PAGEBREAK]]` |
| `landscape` | A `[[LANDSCAPE]]` section with its `[[PORTRAIT]]` |
| `style` | `[[STYLE:Name]] text` |
| `var` | `{{name}}` |
| `mermaid`, `dot`, `plantuml` | A diagram fence with a small example |
| `chart`, `cards` | A poster block |
| `notes`, `columns` | Speaker notes, or two columns, for a slide |

VS Code does not suggest words as you type in Markdown, so snippets wait for `Ctrl+Space`. To have them offered as you type, add this to your settings (**Preferences: Open User Settings (JSON)**):

```json
{
  "[markdown]": {
    "editor.quickSuggestions": { "other": "on", "comments": "off", "strings": "off" }
  }
}
```

## Settings

| Setting | Default | What it does |
|:---|:---|:---|
| `pydoc.executable` | `py-doc` | The py-doc program the preview runs. Set it to the `py-doc` of a virtual environment (`.venv/Scripts/py-doc.exe` on Windows, `.venv/bin/py-doc` elsewhere) when it is not on the `PATH`. |
| `pydoc.watch.port` | `0` | The local port of the preview. `0` lets py-doc pick a free one, so each window can have its own preview. |
| `pydoc.watch.followActiveEditor` | `true` | Move a running preview to another Markdown file when it becomes the active editor. |

## Troubleshooting

- **The preview does not start**: open **View > Output** and choose **py-doc live preview**. "py-doc not found" means VS Code cannot find the program: set `pydoc.executable`. A diagram error means Docker is not running or the tool image is not built: run `py-doc doctor`.
- **Nothing is highlighted**: check that the file's language, shown at the right of the status bar, is **Markdown**. After installing or updating the extension, run **Developer: Reload Window**.
- **A colour is missing**: some themes give no colour to some kinds of text. Run **Developer: Inspect Editor Tokens and Scopes** with the cursor on the text: if the scope ends in `.pydoc`, the extension found it, and the theme decides its colour.
- **A fence is not highlighted inside**: check the fence name against the table under [Diagram fences and poster blocks](#diagram-fences-and-poster-blocks). A name py-doc does not draw is shown as plain code.
- **Ordinary words are coloured, such as `and`, `end` inside `pending`, or `participant`**, and code blocks below lose their colours: another extension's grammar has taken over that part of the file. A Mermaid extension that reads `:::mermaid` blocks is a likely one. Inspect a coloured word as above: when no scope ends in `.pydoc`, disable the other extension for the workspace (in the Extensions view, the gear on its card, then **Disable (Workspace)**).
- **Snippets are not offered**: press `Ctrl+Space` after the prefix, or turn on suggestions in Markdown as shown under [Snippets](#snippets).

## In the repository

```text
editors/vscode/
├── package.json
├── extension.js           # activation, commands and folding
├── src/
│   ├── detect.js          # which command a file is for
│   ├── folding.js         # what folds
│   ├── frontmatter.js     # front matter (js-yaml)
│   ├── text.js            # front matter values as text
│   └── watch.js           # the live preview process
├── syntaxes/
│   ├── pydoc.markdown.tmLanguage.json         # directives, rich tables, callouts, divs and attributes
│   ├── pydoc-fences.markdown.tmLanguage.json  # which grammar each fence takes
│   ├── mermaid, dot, plantuml, block .tmLanguage.json  # the languages of the fences
│   └── bpmnt.*                                # bpmn-text files and fences
├── snippets/pydoc.code-snippets
├── images/icon.png
├── examples/              # a document, a deck and a poster to try it on
└── test/
```

## Tests

```bash
npm ci
npm run lint   # ESLint
npm test       # node --test
```

- `test/detect.test.js`, `test/cases.test.js`: which command a file is for. The shared cases of `tests/fixtures/preview/cases.json` are also built by the Python tests (`tests/test_preview_cases.py`).
- `test/watch.test.js`: the live preview against a fake `py-doc`: the address, the port, replacing and stopping a preview, and build errors.
- `test/highlight.test.js`: py-doc Markdown tokenized by the engine VS Code uses (`vscode-textmate` with Oniguruma). VS Code's Markdown grammar is not on npm, so the tests use a stand-in. To run them against the real one, as CI does, set `PYDOC_MARKDOWN_GRAMMAR` to a copy of `extensions/markdown-basics/syntaxes/markdown.tmLanguage.json` from the VS Code repository.
- `test/grammar.test.js`, `test/folding.test.js`, `test/snippets.test.js`: the grammar files, what folds, and the snippets.
- `tests/test_editor_grammar.py` (Python): the fence grammar names every fence and poster block py-doc draws, and no other.

## Changes

See [CHANGELOG.md](CHANGELOG.md).
