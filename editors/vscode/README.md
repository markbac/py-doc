# py-doc Live Preview for VS Code

Previews documents, slide decks and posters written for [markbac/py-doc](https://github.com/markbac/py-doc) beside the editor, as py-doc builds them.

The preview runs `py-doc docx`, `py-doc slides` or `py-doc poster` with `--watch` on the open file and shows the page py-doc serves. It is py-doc's own output, so every block, diagram, theme and caption looks as it will in the build. A new py-doc feature is in the preview as soon as py-doc has it.

---

## Using it

Open a py-doc Markdown file and click the eye button in the editor title bar, or run **py-doc: Open Live Preview** from the Command Palette. The preview opens beside the editor and reloads each time you save.

- **Documents** (`py-doc docx file.md --watch`): rebuilds `file.docx` on save and shows its HTML twin, with every diagram, MathML and page breaks shown as dashed lines. A `.docx` open in Word is left as it is, with a warning, and the preview still updates.
- **Slide decks** (`py-doc slides deck.md --watch`): rebuilds `deck.pptx` and shows each slide as a numbered 16:9 box, split where PowerPoint splits it, with columns and speaker notes.
- **Posters** (`py-doc poster poster.md --watch`): rebuilds the self-contained poster page.

The twins are written to `.py-doc/preview/` below the file's folder, so no file of yours is overwritten. py-doc's output is in the **py-doc live preview** output channel. When a save does not build, the preview keeps the last good page with the error across its top, and VS Code shows the error as a warning.

The eye button chooses the command from the file itself:

- **Poster**: the front matter has a poster setting (`paper`, `byline`, `orientation`, `theme`, `columns`, `width`, `colours`, `palette`, `logo`, `embed_fonts`).
- **Slides**: the front matter has `split_level` or a `format` of `slides`/`pptx`, or the body has `:::: columns`, `::: notes`, `::: incremental` or `<!-- notes: -->` outside code blocks.
- **Word document**: anything else.

To choose the format yourself, use **py-doc: Open Live Word Document / Presentation / Poster Preview**. One preview runs at a time: opening another stops the one already running, and **py-doc: Stop Live Preview Server** stops it. While a preview runs, switching to another Markdown file moves the preview to it (turn this off with `pydoc.watch.followActiveEditor`).

VS Code's own Markdown preview (`Ctrl+Shift+V`) still works, but shows plain Markdown: py-doc's blocks and markers need the live preview.

---

## Install

The extension is not on the Marketplace yet. Build it and install the file:

```bash
cd editors/vscode
npm ci
npx @vscode/vsce package          # writes vscode-py-doc-preview-<version>.vsix
code --install-extension vscode-py-doc-preview-*.vsix
```

The preview needs py-doc itself (`pip install -e .` at the root of this repository) and Docker, for the diagrams.

---

## Settings

| Setting | Default | What it does |
|:---|:---|:---|
| `pydoc.executable` | `py-doc` | The py-doc program the preview runs. Set it to the `py-doc` of a virtual environment (`.venv/Scripts/py-doc.exe` on Windows, `.venv/bin/py-doc` elsewhere) when it is not on the `PATH`. |
| `pydoc.watch.port` | `0` | The local port of the preview. `0` lets py-doc pick a free one, so each window can have its own preview. |
| `pydoc.watch.followActiveEditor` | `true` | Move a running preview to another Markdown file when it becomes the active editor. |

---

## In the repository

```text
editors/vscode/
├── package.json
├── extension.js       # activation and commands
├── src/
│   ├── detect.js      # which command a file is for
│   ├── frontmatter.js # front matter (js-yaml)
│   ├── text.js        # front matter values as text
│   └── watch.js       # the live preview process
├── images/icon.png
├── examples/          # a document, a deck and a poster to try it on
└── test/
```

To recommend it in a project, add it to `.vscode/extensions.json`:

```json
{
  "recommendations": ["py-doc.vscode-py-doc-preview"]
}
```

---

## Tests

```bash
npm ci
npm run lint   # ESLint
npm test       # node --test
```

- `test/detect.test.js`: which command a file is for.
- `test/cases.test.js`: the shared cases of `tests/fixtures/preview/cases.json` pick the command they are built with. The Python tests (`tests/test_preview_cases.py`) build the same cases into the HTML twin.
- `test/watch.test.js`: the live preview against a fake `py-doc`: the address, the port, replacing and stopping a preview, and build errors.

## Changes

See [CHANGELOG.md](CHANGELOG.md).
