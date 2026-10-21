# py-doc Markdown Preview for VS Code

A lightweight, zero-runtime-dependency Visual Studio Code extension that extends the built-in Markdown preview to render technical documentation, slide decks, and posters authored for [markbac/py-doc](https://github.com/markbac/py-doc).

It formats custom `py-doc` Word (`.docx`) markers, callouts, numbered captions, PowerPoint (`.pptx`) slide layouts, and HTML/PDF poster structures so that your live editor preview matches the structure of the generated documents.

---

## Features

### 1. Technical Documents (Word `.docx`)

| Feature | `py-doc` Syntax | Preview Rendering |
|:---|:---|:---|
| **Numbered Captions** | `[[CAPTION:Figure]] Description`<br>`[[CAPTION:Table]] Description` | Automatically counted and formatted as **Figure 1: Description**, **Table 1: Description**, etc. (independent sequences). |
| **Word Callouts & Admonitions** | `> [!NOTE]` / `> **Note:**`<br>`> [!TIP]` / `> **Tip:**`<br>`> [!IMPORTANT]` / `> **Important:**`<br>`> [!WARNING]` / `> **Warning:**`<br>`> [!CAUTION]` / `> **Caution:**` | Formatted into color-coded callout boxes matching Word's `Div.note` through `Div.caution` styles with icons and colored borders. |
| **Document Cover Header** | YAML block between `---` at the top | Formatted as a document cover header showing title, subtitle, document number, version, status pill, author, and date. |
| **Page Breaks** | `[[PAGEBREAK]]` or `::: {.pagebreak}` | Rendered as a visual `─── PAGE BREAK ───` divider. |
| **Orientation Breaks** | `[[LANDSCAPE]]` or `[[PORTRAIT]]` | Rendered as a `─── SECTION BREAK (LANDSCAPE) ───` divider. |
| **Word Paragraph Styles** | `[[STYLE:StyleName]] Text` | Strips the marker and adds a subtle `[Style: StyleName]` tag to preview styled Word paragraphs. |
| **Directives** | `[[INCLUDE: file.md]]`<br>`[[IF: condition]]` | Rendered as clean visual badges so directives are clearly identifiable. |

---

### 2. Slide Decks (PowerPoint `.pptx`)

When authoring a slide deck (e.g. `slides.md`, `format: pptx`, or using slide directives), the preview switches to **Slide Deck Mode**:

| Slide Feature | `py-doc` Syntax | Preview Rendering |
|:---|:---|:---|
| **Section Header Slide** | `# Section Title` | Formatted as a full-bleed PowerPoint Section Header slide card. |
| **Content Slide** | `## Slide Title` | Formatted as a 16:9 presentation slide card with slide header and footer (`Slide 1`, `Slide 2`, etc.). |
| **Two Columns** | `:::: columns`<br>`::: column`<br>Left<br>`:::`<br>`::: column`<br>Right<br>`:::`<br>`::::` | Formatted as a responsive, side-by-side flexbox layout matching PowerPoint's **Two Content** layout. |
| **Speaker Notes** | `::: notes`<br>Note text<br>`:::`<br>or `<!-- notes: Text -->` | Formatted as a dedicated 📝 **Speaker Notes** card (kept distinct from audience-facing slide content). |
| **Incremental Reveals** | `::: incremental`<br>1. Point 1<br>2. Point 2<br>`:::` | Tagged with a click-by-click indicator so the author knows the list builds incrementally. |
| **Slide Breaks** | `[[PAGEBREAK]]` | Splits onto a new untitled slide card (e.g. for full-slide diagrams or quotes). |

---

### 3. Posters (HTML & PDF Posters)

When authoring a poster (e.g. `paper: a1`, `byline: ...`, or headings with `{.stats}`), the preview switches to **Poster Mode**:

| Poster Feature | `py-doc` Syntax | Preview Rendering |
|:---|:---|:---|
| **Poster Header** | Front matter `title`, `subtitle`, `byline`, `paper` | Large centered poster header banner with title, subtitle, byline, and paper badge. |
| **Stat Strip** | `## Key figures {.stats}` + Table | Formatted into a responsive KPI strip with large numbers, labels, and green/red trend badges. |
| **Abstract Box** | `## Introduction {.abstract}` | Formatted as a prominent introduction box. |
| **Section Headings with Accent** | `## 1. Topic: details` | Topic followed by highlighted accent text after the colon. |
| **Cards Grid** | ```` ```cards ```` with `Title \| Desc \| color` | Responsive multi-column card grid with colored top accents. |
| **Segments Bar** | ```` ```segments ```` with `weight \| label \| value \| color` | Proportional horizontal timeline or resource bar. |
| **Flow Diagram** | ```` ```flow ```` with `[Node\|color] -label-> [Node]` | Step-by-step pipeline sequence with badges and arrows. |
| **Summary Banner** | `## In short {.summary}` | Prominent takeaway banner. |
| **Poster Footer** | Front matter `footer.left`, `footer.right`, `footer.qr` | Formatted footer with left/right text and QR code label. |

---

## Adding to the `py-doc` Repository

To include this extension as a standard writing tool in the [`markbac/py-doc`](https://github.com/markbac/py-doc) repository:

### 1. Place in the Repo Structure
Located in `editors/vscode`:
```text
py-doc/
├── src/py_doc/
├── docs/
├── examples/
└── editors/
    └── vscode/             <-- VS Code extension
        ├── package.json
        ├── extension.js
        ├── styles/
        │   └── py-doc-preview.css
        ├── test/
        │   └── test.js
        └── README.md
```

### 2. Recommend in Projects (`.vscode/extensions.json`)
In projects initialized with `py-doc init`, or at the root of `py-doc`:
```json
{
  "recommendations": [
    "py-doc.vscode-py-doc-preview"
  ]
}
```

---

## Running Automated Tests

```bash
npm test
```

Runs all 7 test suites validating documents, slides, and poster features.
