'use strict';

// Highlighting: .bpmnt files, ```bpmnt fences in Markdown, and py-doc's directives and variables in Markdown.

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

test('py-doc directives and variables are highlighted in Markdown', () => {
  const grammar = read('syntaxes/pydoc.markdown.tmLanguage.json');
  const directive = new RegExp(grammar.repository.directive.match);
  for (const line of ['[[LISTTABLE: header, widths=5,95]]', '[[BLOCK: wiring]]', '[[ENDBLOCK]]', '[[INCLUDE: a.md]]', '[[CAPTION:Table]] Sizes']) {
    assert.match(line, directive, line);
  }
  assert.strictEqual('[[LISTTABLE: header]]'.match(directive)[2], 'LISTTABLE');
  assert.doesNotMatch('[[not a directive]]', directive);
  assert.doesNotMatch('text [[INCLUDE: a.md]]', directive);
  assert.match('Version {{ version }}', new RegExp(grammar.repository.variable.match));
  assert.match(grammar.injectionSelector, /-markup\.fenced_code/);
});
