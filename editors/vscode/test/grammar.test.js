'use strict';

// bpmn-text highlighting: .bpmnt files, and ```bpmnt fences in Markdown.

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const manifest = require('../package.json');
const read = (file) => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));

test('every grammar and language file the manifest names exists, under the scope it is registered as', () => {
  for (const grammar of manifest.contributes.grammars) {
    assert.strictEqual(read(grammar.path).scopeName, grammar.scopeName, grammar.path);
  }
  for (const language of manifest.contributes.languages) {
    assert.ok(read(language.configuration).comments.lineComment, language.configuration);
  }
});

test('a bpmnt fence in Markdown is highlighted with the bpmn-text grammar', () => {
  const fence = manifest.contributes.grammars.find((g) => g.injectTo);
  const block = read(fence.path).repository['bpmnt-code-block'];
  assert.match('```bpmnt', new RegExp(block.begin.replace('(?i:', '(?:')));
  assert.match('~~~~ bpmnt title="Order"', new RegExp(block.begin.replace('(?i:', '(?:')));
  assert.doesNotMatch('```bpmnt2', new RegExp(block.begin.replace('(?i:', '(?:')));
  assert.deepStrictEqual(block.patterns[0].patterns, [{ include: 'source.bpmnt' }]);
  assert.strictEqual(fence.embeddedLanguages[block.patterns[0].contentName], 'bpmnt');
});

test('the keywords are the statement keywords of the bpmn-text notation', () => {
  const statement = read('syntaxes/bpmnt.tmLanguage.json').repository.statement.match;
  for (const word of ['pool', 'lane', 'start', 'task', 'send', 'receive', 'xor', 'and', 'sub', 'doc', 'else']) {
    assert.match(`  ${word} Something`, new RegExp(statement), word);
  }
  assert.doesNotMatch('  Ship parcel', new RegExp(statement));
});
