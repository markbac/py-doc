# Changes

## 2.3.1

- Diagrams written in the `:::mermaid` ... `:::` form, which py-doc also draws, are highlighted in their language like a backtick fence, for every diagram language.

## 2.3.0

- Highlighting inside every diagram fence and poster block py-doc draws: Mermaid, Graphviz (and the blockdiag family) and PlantUML with grammars of the extension's own, and Vega, WaveDrom, WireViz and bytefield with VS Code's JSON, JavaScript, YAML and Clojure grammars. Poster blocks, `plot` and the written-form fences show their `key:` lines, `key=value` options, cells, icons and numbers. The attributes on a fence line are highlighted too.
- Highlighting of rich tables cell by cell (`<br>`, list items, `<` and `^` merges, `{bg=... valign=...}`, `[[BLOCK:]]`), callouts, fenced divs and pandoc attribute blocks.
- Folding of `[[IF:]]`/`[[NOT:]]` to `[[ENDIF]]`, `[[BLOCK:]]` to `[[ENDBLOCK]]`, `[[LANDSCAPE]]` to `[[PORTRAIT]]`, rich tables and fenced divs.
- Snippets for rich tables, blocks, callouts, captions, includes, conditions, page breaks, landscape sections, styles, variables, diagrams, poster blocks, speaker notes and columns.
- The README is a full guide: installing, the preview, what is highlighted, folding, snippets, settings and troubleshooting.

## 2.2.0

- Highlighting of py-doc directives in Markdown, such as `[[INCLUDE: a.md]]`, `[[LISTTABLE: header]]` and `[[BLOCK: name]]`, and of `{{variables}}`. Code is left alone.

## 2.1.0

- Highlighting of the [bpmn-text](https://github.com/markbac/bpmn-text) notation, in `.bpmnt` files and in ```` ```bpmnt ```` fences of Markdown files, with `#` comments toggled by `Ctrl+/`.

## 2.0.0

- The preview is the live preview only: py-doc's own output from `--watch`, beside the editor. The instant preview inside VS Code's Markdown preview (a markdown-it plugin and its styles) is removed, because it re-implemented py-doc's blocks in JavaScript and drifted from the build.
- The preview opens beside the editor and keeps the focus in the editor.
- A running preview follows the editor to another Markdown file (`pydoc.watch.followActiveEditor`, on by default).
- A save that does not build is shown as a warning, once until a build succeeds.
- The extension is renamed "py-doc Live Preview".

## 1.0.0

- The instant preview of documents, slide decks and posters in VS Code's Markdown preview, and the live preview through `--watch`.
