const assert = require('assert');
const MarkdownIt = require('markdown-it');
const { pyDocPlugin } = require('../extension');

const md = new MarkdownIt({ html: true });
md.use(pyDocPlugin);

console.log('Running py-doc markdown preview tests...\n');

// Test 1: Front Matter (Document Mode)
{
  const input = `---
title: My Technical Document
status: Draft
version: "1.0"
---
# Content
`;
  const html = md.render(input);
  assert(html.includes('class="pydoc-frontmatter'), 'Front matter container should be present');
  assert(html.includes('class="pydoc-doc-title">My Technical Document</h1>'), 'Title should be rendered in front matter');
  assert(html.includes('Draft'), 'Status should be rendered');
  console.log('✓ Front matter parsed and rendered successfully');
}

// Test 2: Numbered Captions
{
  const input = `
[[CAPTION:Figure]] First diagram

[[CAPTION:Figure]] Second diagram

[[CAPTION:Table]] First table
`;
  const html = md.render(input);
  assert(html.includes('Figure 1:'), 'First figure should be numbered 1');
  assert(html.includes('Figure 2:'), 'Second figure should be numbered 2');
  assert(html.includes('Table 1:'), 'First table should be numbered 1');
  console.log('✓ Numbered captions sequence independently and correctly');
}

// Test 3: Callouts / Admonitions
{
  const input = `
> [!NOTE]
> This is a github note.

> **Warning:** This is a bold warning.

> **Tip**: This is a tip with colon outside.
`;
  const html = md.render(input);
  assert(html.includes('pydoc-callout-note'), 'GitHub NOTE should have note class');
  assert(html.includes('pydoc-callout-warning'), 'Bold Warning should have warning class');
  assert(html.includes('pydoc-callout-tip'), 'Bold Tip should have tip class');
  console.log('✓ Callouts (both GitHub alerts and bold labels) rendered correctly');
}

// Test 4: Page Break and Orientation
{
  const input = `
[[PAGEBREAK]]

[[LANDSCAPE]]

[[PORTRAIT]]
`;
  const html = md.render(input);
  assert(html.includes('pydoc-pagebreak'), 'Pagebreak should be rendered');
  assert(html.includes('SECTION BREAK (LANDSCAPE)'), 'Landscape section break should be rendered');
  assert(html.includes('SECTION BREAK (PORTRAIT)'), 'Portrait section break should be rendered');
  console.log('✓ Page breaks and section breaks rendered correctly');
}

// Test 5: Word Styles and Directives
{
  const input = `
[[STYLE:Lead Paragraph]] Special text.

[[INCLUDE: docs/install.md]]
`;
  const html = md.render(input);
  assert(html.includes('data-word-style="Lead Paragraph"'), 'Word style attribute should be present');
  assert(html.includes('pydoc-directive'), 'Directive should be present');
  assert(html.includes('docs/install.md'), 'Included file path should be present');
  console.log('✓ Word styles and directives rendered correctly');
}

// Test 6: Slide Deck Features (Two Columns, Speaker Notes, Slide Cards)
{
  const input = `---
title: Sensor Node Presentation
format: pptx
---

# Introduction

Welcome to the deck.

## Architecture

:::: columns
::: column
**Left Column**
- Item 1
:::
::: column
**Right Column**
- Item 2
:::
::::

::: notes
Mention field deployment history here.
:::

<!-- notes: Also remember battery specs. -->
`;
  const html = md.render(input);
  assert(html.includes('pydoc-slide-section'), 'Level 1 heading should create a Section Slide card');
  assert(html.includes('pydoc-slide-content'), 'Level 2 heading should create a Content Slide card');
  assert(html.includes('pydoc-columns'), 'Columns block should be rendered');
  assert(html.includes('pydoc-column'), 'Individual columns should be rendered');
  assert(html.includes('pydoc-notes'), 'Speaker notes block should be rendered');
  assert(html.includes('Mention field deployment history here'), 'Speaker notes text should be present');
  assert(html.includes('Also remember battery specs'), 'HTML comment notes should be rendered');
  console.log('✓ Slide Deck features (cards, two-columns, speaker notes) rendered correctly');
}

// Test 7: Poster Features (Stats strip, Abstract, Accent Headings, Cards, Segments, Flow, Footer)
{
  const input = `---
title: SN-100 Poster
subtitle: Five years of readings
byline: Mark Bacon
paper: a1
footer:
  left: SN-100
  qr-label: Full Datasheet
---

## Key figures {.stats}

| Value | Label | Change | Verdict |
|---|---|---|---|
| 2 µA | Sleep current | -0.5 µA | good |
| 5 years | Battery life | +14 % | |

## Introduction {.abstract}

This poster summarizes the sensor node.

## 1. Hardware: what is on the board

\`\`\`cards cols=2 style=top
Sensor | Temp on I2C | blue
Radio | 868 MHz MQTT | green
\`\`\`

\`\`\`segments
title: One minute of time
6 | Asleep | 2 uA | navy
2 | Send | 12 mA | amber
\`\`\`

\`\`\`flow
[Asleep|navy] -timer-> [Measure|blue] -changed-> [Send|amber]
\`\`\`
`;
  const html = md.render(input);
  assert(html.includes('pydoc-poster-header'), 'Poster header should be rendered');
  assert(html.includes('pydoc-poster-title">SN-100 Poster</h1>'), 'Poster title should be present');
  assert(html.includes('pydoc-poster-byline">Mark Bacon</div>'), 'Poster byline should be present');
  assert(html.includes('pydoc-poster-stats'), 'Stats strip should be rendered');
  assert(html.includes('pydoc-stat-value">2 µA</div>'), 'Stat value should be rendered in card');
  assert(html.includes('pydoc-heading-abstract'), 'Abstract heading class should be preserved');
  assert(html.includes('pydoc-heading-accent"> what is on the board</span>'), 'Colon accent should be formatted');
  assert(html.includes('pydoc-cards-grid'), 'Cards grid block should be rendered');
  assert(html.includes('pydoc-card-blue'), 'Blue card should be rendered');
  assert(html.includes('pydoc-segments-box'), 'Segments block should be rendered');
  assert(html.includes('pydoc-flow-diagram'), 'Flow diagram block should be rendered');
  assert(html.includes('pydoc-poster-footer'), 'Poster footer should be rendered');
  assert(html.includes('Full Datasheet'), 'Poster QR label should be rendered');
  console.log('✓ Poster features (stats, abstract, colon accent, cards, segments, flow, footer) rendered correctly');
}

// Test 8: Image Dimensions and Diagram types
{
  const input = `
![The board](images/board.svg){width=60%}

\`\`\`plantuml title="System Architecture"
@startuml
Alice -> Bob : Authentication Request
@enduml
\`\`\`

\`\`\`dot title="Dependency Graph"
digraph G {
  main -> parse;
}
\`\`\`
`;
  const html = md.render(input);
  assert(html.includes('style="width: 60%; max-width: 100%;"'), 'Image width attribute should be converted to style');
  assert(!html.includes('{width=60%}'), 'Literal {width=...} text should be removed');
  assert(html.includes('data-diagram="plantuml"'), 'PlantUML diagram should be wrapped in diagram box');
  assert(html.includes('System Architecture'), 'PlantUML title should be displayed');
  assert(html.includes('data-diagram="dot"'), 'Graphviz dot diagram should be wrapped in diagram box');
  console.log('✓ Image width attributes and diagram fence blocks rendered correctly');
}

// Test 9: Document format detection
{
  const fs = require('fs');
  const path = require('path');
  const { detectDocumentFormat } = require('../extension');
  const doc = (text) => ({ getText: () => text, fileName: 'c:/docs/anything.md' });

  // Posters: any poster-only front matter key
  assert(detectDocumentFormat('---\ntitle: Poster\ntheme: dark\n---\n# Poster') === 'poster', 'theme in front matter means poster');
  assert(detectDocumentFormat('---\ntitle: P\norientation: landscape\npaper: a1\n---\n## A') === 'poster', 'paper/orientation mean poster');
  const landscape = path.join(__dirname, '..', '..', '..', 'examples', 'poster', 'landscape.md');
  if (fs.existsSync(landscape)) {
    assert(detectDocumentFormat(doc(fs.readFileSync(landscape, 'utf8'))) === 'poster', 'examples/poster/landscape.md is a poster');
  }

  // Slides: front matter, or blocks only a deck has
  assert(detectDocumentFormat('---\ntitle: Deck\nformat: slides\n---\n# Slide 1') === 'slides', 'format: slides means slides');
  assert(detectDocumentFormat('---\nsplit_level: 1\n---\n# S') === 'slides', 'split_level means slides');
  assert(detectDocumentFormat('# Talk\n\n## One\n\n::: notes\nSay this\n:::\n') === 'slides', 'speaker notes mean slides');
  assert(detectDocumentFormat('# Doc\n\n```markdown\n::: notes\n```\n') === 'docx', 'notes inside a code fence do not count');

  // The file name decides nothing
  assert(detectDocumentFormat({ getText: () => '# Just doc', fileName: 'c:/docs/sn100-poster.md' }) === 'docx', 'poster in a file name is not a poster');
  assert(detectDocumentFormat({ getText: () => '# Guide', fileName: 'c:/decks/talk.md' }) === 'docx', 'talk in a file name is not a deck');
  assert(detectDocumentFormat('---\ntitle: Tech Spec\nauthor: Jane\n---\n# Chapter 1') === 'docx', 'a technical doc defaults to docx');

  console.log('✓ Document format detection for live watch server (docx, slides, poster) works correctly');
}

// Test 10: Regressions: front matter mode with nested renders, list values, heading accents, split_level, escaping
{
  const fresh = () => new MarkdownIt({ html: true }).use(pyDocPlugin);
  const poster = '---\ntitle: P\nbyline: me\npaper: a1\n---\n\n## A\n\n';

  // A callout (rendered with md.renderInline) must not turn the poster header into a document header
  let html = fresh().render(poster + '> [!NOTE]\n> hi\n\n[[CAPTION:Figure]] A figure\n');
  assert(html.includes('pydoc-poster-header'), 'poster header survives callouts and captions');
  assert(!html.includes('pydoc-frontmatter'), 'no document header in a poster');

  // A list in the front matter is shown, not a crash
  html = fresh().render('---\ntitle: T\nauthor:\n  - Jane\n  - Joe\n---\n\n# x\n');
  assert(html.includes('Jane, Joe'), 'author list is joined');

  // Heading accents: posters only, formatting kept
  html = fresh().render(poster + '## Step 1: install `py-doc` with **pip**\n');
  assert(html.includes('<span class="pydoc-heading-accent">'), 'poster heading gets an accent');
  assert(html.includes('<code>py-doc</code>') && html.includes('<strong>pip</strong>'), 'accent keeps inline formatting');
  html = fresh().render('# Doc\n\n## Step 1: install `py-doc`\n');
  assert(!html.includes('pydoc-heading-accent'), 'documents get no heading accent');
  assert(html.includes('<code>py-doc</code>'), 'document heading keeps inline code');

  // split_level 1: each # heading is a content slide, ## does not split
  html = fresh().render('---\nsplit_level: 1\n---\n\n# One\n\n## Sub\n\ntext\n\n# Two\n');
  assert((html.match(/<section class="pydoc-slide /g) || []).length === 2, 'split_level 1 makes one slide per # heading');
  assert(!html.includes('pydoc-slide-section'), 'no section slides at split_level 1');

  // Colours and weights from the Markdown cannot break out of attributes
  html = fresh().render(poster + '```cards\nA | B | blue" onclick="x\n```\n\n```segments\nx" y | L | 1 | red\n```\n');
  assert(!html.includes('onclick="'), 'card colour is sanitised');
  assert(!html.includes('flex: x"'), 'segment weight is sanitised');

  console.log('✓ Regressions: nested renders, list front matter, heading accents, split_level and escaping');
}

console.log('\nAll 10 test suites passed successfully! 🎉');
