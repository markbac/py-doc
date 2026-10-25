'use strict';

// Which py-doc command the live preview runs for a file: docx, slides or poster.

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { detectDocumentFormat } = require('../extension');

const doc = (text, fileName = 'c:/docs/anything.md') => ({ getText: () => text, fileName });

test('a poster-only front matter key means a poster', () => {
  assert.strictEqual(detectDocumentFormat('---\ntitle: Poster\ntheme: dark\n---\n# Poster'), 'poster');
  assert.strictEqual(detectDocumentFormat('---\ntitle: P\norientation: landscape\npaper: a1\n---\n## A'), 'poster');
  const landscape = path.join(__dirname, '..', '..', '..', 'examples', 'poster', 'landscape.md');
  assert.strictEqual(detectDocumentFormat(doc(fs.readFileSync(landscape, 'utf8'))), 'poster');
});

test('slides come from the front matter, or from blocks only a deck has', () => {
  assert.strictEqual(detectDocumentFormat('---\ntitle: Deck\nformat: slides\n---\n# Slide 1'), 'slides');
  assert.strictEqual(detectDocumentFormat('---\nsplit_level: 1\n---\n# S'), 'slides');
  assert.strictEqual(detectDocumentFormat('# Talk\n\n## One\n\n::: notes\nSay this\n:::\n'), 'slides');
  assert.strictEqual(detectDocumentFormat('# Doc\n\n```markdown\n::: notes\n```\n'), 'docx', 'notes inside a code fence do not count');
});

test('the file name decides nothing, and a document is the default', () => {
  assert.strictEqual(detectDocumentFormat(doc('# Just doc', 'c:/docs/sn100-poster.md')), 'docx');
  assert.strictEqual(detectDocumentFormat(doc('# Guide', 'c:/decks/talk.md')), 'docx');
  assert.strictEqual(detectDocumentFormat('---\ntitle: Tech Spec\nauthor: Jane\n---\n# Chapter 1'), 'docx');
});
