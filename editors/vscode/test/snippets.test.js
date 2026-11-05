'use strict';

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const manifest = require('../package.json');

const file = path.join(__dirname, '..', manifest.contributes.snippets[0].path);
const snippets = JSON.parse(fs.readFileSync(file, 'utf8'));

test('every snippet has a prefix, a body and a description, and no two share a prefix', () => {
  const prefixes = Object.values(snippets).map((s) => s.prefix);
  assert.strictEqual(new Set(prefixes).size, prefixes.length);
  for (const [name, s] of Object.entries(snippets)) {
    assert.ok(s.prefix && Array.isArray(s.body) && s.body.length && s.description, name);
  }
});

test('the snippets write what py-doc reads', () => {
  assert.match(snippets['Rich table'].body.join('\n'), /^\[\[LISTTABLE: header, widths=\$\{2:30,70\}\]\]$/m);
  assert.deepStrictEqual(snippets['Condition'].body, ['[[IF: ${1:key}]]', '$0', '[[ENDIF]]']);
  assert.strictEqual(snippets['Callout: warning'].body[0], '> [!WARNING]');
});
