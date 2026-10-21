'use strict';

// The shared preview cases of tests/fixtures/preview/cases.json, through the instant preview.
// tests/test_preview_cases.py runs the same cases through the HTML twin that --watch builds, so the
// instant preview cannot drift from the build without one of the two failing.

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const MarkdownIt = require('markdown-it');
const { pyDocPlugin, detectDocumentFormat } = require('../extension');

const CASES = path.join(__dirname, '..', '..', '..', 'tests', 'fixtures', 'preview', 'cases.json');
const { cases } = JSON.parse(fs.readFileSync(CASES, 'utf8'));

const count = (html, needle) => html.split(needle).length - 1;

for (const c of cases) {
  test(c.name, () => {
    // The build takes the split level from the command line; the instant preview from the front matter
    const markdown = c.split_level ? `---\nsplit_level: ${c.split_level}\n---\n\n${c.markdown}` : c.markdown;
    assert.strictEqual(detectDocumentFormat(markdown), c.command, 'detected command');

    const html = new MarkdownIt({ html: true }).use(pyDocPlugin).render(markdown);
    const expect = c.expect;
    for (const kind of expect.callouts || []) {
      assert.ok(html.includes(`pydoc-callout-${kind}`), `callout ${kind}`);
    }
    assert.strictEqual(count(html, 'class="pydoc-pagebreak"'), expect.pagebreaks || 0, 'page breaks');
    assert.strictEqual(count(html, '<section class="pydoc-slide '), expect.slides || 0, 'slides');
    assert.strictEqual(count(html, 'pydoc-slide-section'), expect.parts || 0, 'part slides');
    assert.strictEqual(count(html, 'pydoc-notes"'), expect.notes || 0, 'speaker notes');
    assert.strictEqual(count(html, 'pydoc-columns"'), expect.columns || 0, 'columns');
    for (const text of expect.text || []) {
      assert.ok(html.includes(text), text);
    }
  });
}
