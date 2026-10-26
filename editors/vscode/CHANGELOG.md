# Changes

## 2.0.0

- The preview is the live preview only: py-doc's own output from `--watch`, beside the editor. The instant preview inside VS Code's Markdown preview (a markdown-it plugin and its styles) is removed, because it re-implemented py-doc's blocks in JavaScript and drifted from the build.
- The preview opens beside the editor and keeps the focus in the editor.
- A running preview follows the editor to another Markdown file (`pydoc.watch.followActiveEditor`, on by default).
- A save that does not build is shown as a warning, once until a build succeeds.
- The extension is renamed "py-doc Live Preview".

## 1.0.0

- The instant preview of documents, slide decks and posters in VS Code's Markdown preview, and the live preview through `--watch`.
