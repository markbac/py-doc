'use strict';

// The shared preview cases of tests/fixtures/preview/cases.json: the live preview must pick the py-doc command
// each case is built with. tests/test_preview_cases.py builds the same cases into the HTML twin that --watch
// serves and checks what it shows.

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { detectDocumentFormat } = require('../extension');

const CASES = path.join(__dirname, '..', '..', '..', 'tests', 'fixtures', 'preview', 'cases.json');
const { cases } = JSON.parse(fs.readFileSync(CASES, 'utf8'));

for (const c of cases) {
  test(c.name, () => {
    // The build takes the split level from the command line; the preview finds it in the front matter
    const markdown = c.split_level ? `---\nsplit_level: ${c.split_level}\n---\n\n${c.markdown}` : c.markdown;
    assert.strictEqual(detectDocumentFormat(markdown), c.command, 'detected command');
  });
}
