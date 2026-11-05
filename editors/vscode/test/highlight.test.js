'use strict';

// What VS Code shows: py-doc Markdown tokenized with the extension's grammars by VS Code's own engine.

const { test } = require('node:test');
const assert = require('node:assert');
const { tokenize, scopesOf } = require('./tokenize');

const has = (scopes, name) => assert.ok(scopes.includes(name), `${name} not in ${scopes}`);

test('a mermaid fence is highlighted as Mermaid', async () => {
  const t = await tokenize('```mermaid\nflowchart LR\n  A[Power on] -->|joins| B\n%% a comment\n```');
  has(scopesOf(t, 1, 'flowchart'), 'storage.type.diagram.mermaid');
  has(scopesOf(t, 1, 'flowchart'), 'meta.embedded.block.pydoc-mermaid');
  has(scopesOf(t, 2, '-->'), 'keyword.operator.arrow.mermaid');
  has(scopesOf(t, 2, 'joins'), 'string.unquoted.label.mermaid');
  has(scopesOf(t, 3, '%% a comment'), 'comment.line.percentage.mermaid');
});

test('dot, graphviz and the blockdiag family are highlighted as DOT, with the fence attributes', async () => {
  const t = await tokenize('```dot width="100%"\ndigraph g { rankdir=LR; a -> b [label="x"]; }\n```');
  has(scopesOf(t, 0, 'width'), 'entity.other.attribute-name.pydoc');
  has(scopesOf(t, 1, 'digraph'), 'storage.type.graph.dot');
  has(scopesOf(t, 1, 'rankdir'), 'entity.other.attribute-name.dot');
  has(scopesOf(t, 1, '->'), 'keyword.operator.edge.dot');
  const b = await tokenize('```seqdiag\nseqdiag { browser -> server; }\n```');
  has(scopesOf(b, 1, 'seqdiag'), 'storage.type.graph.dot');
  has(scopesOf(await tokenize('```graphviz\ngraph { a -- b }\n```'), 1, '--'), 'keyword.operator.edge.dot');
});

test('a plantuml or puml fence is highlighted as PlantUML', async () => {
  const t = await tokenize("```puml\n@startuml\nactor User\nUser -> System : asks\n' a comment\n@enduml\n```");
  has(scopesOf(t, 1, '@startuml'), 'keyword.control.startend.plantuml');
  has(scopesOf(t, 2, 'actor'), 'storage.type.element.plantuml');
  has(scopesOf(t, 3, '->'), 'keyword.operator.arrow.plantuml');
  has(scopesOf(t, 4, "' a comment"), 'comment.line.apostrophe.plantuml');
});

test('vega, wavedrom, wireviz and bytefield fences take the JSON, JavaScript, YAML and Clojure grammars', async () => {
  for (const [fence, key] of [['vega-lite', 'json'], ['wavedrom', 'javascript'], ['wireviz', 'yaml'], ['bytefield-svg', 'clojure']]) {
    const t = await tokenize('```' + fence + '\nx\n```');
    has(scopesOf(t, 1, 'x'), `meta.embedded.block.pydoc-${key}`);
  }
});

test('a poster block shows its rows, options, keys, icons and numbers', async () => {
  const t = await tokenize('```chart type=column title="A day"\nseries: 2.0, 2.1\nOffice | 1440 | 610\n```');
  has(scopesOf(t, 0, 'type'), 'entity.other.attribute-name.pydoc');
  has(scopesOf(t, 1, 'series'), 'entity.name.tag.key.pydoc');
  has(scopesOf(t, 2, '|'), 'punctuation.separator.cell.pydoc');
  has(scopesOf(t, 2, '1440'), 'constant.numeric.pydoc');
  const c = await tokenize('```cards cols=3\nSensor | Temperature | icon=tabler:temperature\n```');
  has(scopesOf(c, 1, 'icon'), 'entity.other.attribute-name.pydoc');
  has(scopesOf(c, 1, 'tabler:temperature'), 'string.unquoted.value.pydoc');
  const v = await tokenize('```circuit\nR1: resistor 10 kΩ | right\n```');
  has(scopesOf(v, 1, 'R1'), 'entity.name.tag.key.pydoc');
});

test('a rich table shows its marker, breaks, merges, cell styles, lists and blocks', async () => {
  const t = await tokenize(
    '[[LISTTABLE: header, widths=8,92]]\n| Step | What |\n| 1 | Do:<br>- a<br>1. b<br>[[BLOCK: wiring]] |\n| ^ | {bg=E8F5E9 valign=middle} c |\n| x | < |\n\nAfter | not a row'
  );
  has(scopesOf(t, 0, 'LISTTABLE'), 'keyword.control.directive.pydoc');
  has(scopesOf(t, 0, 'header, widths=8,92'), 'string.unquoted.argument.pydoc');
  has(scopesOf(t, 2, '<br>'), 'entity.name.tag.break.pydoc');
  has(scopesOf(t, 2, '-'), 'punctuation.definition.list.begin.markdown');
  has(scopesOf(t, 2, '1.'), 'punctuation.definition.list.begin.markdown');
  has(scopesOf(t, 2, 'wiring'), 'string.unquoted.argument.pydoc');
  has(scopesOf(t, 3, '^'), 'keyword.operator.merge.pydoc');
  has(scopesOf(t, 3, 'bg'), 'entity.other.attribute-name.pydoc');
  has(scopesOf(t, 3, 'E8F5E9'), 'constant.other.color.pydoc');
  has(scopesOf(t, 4, '<'), 'keyword.operator.merge.pydoc');
  assert.ok(!t[6].some(([, scopes]) => scopes.includes('meta.table.listtable.pydoc')), 'the table ends at a line without |');
});

test('callouts, fenced divs, attributes, directives and variables are highlighted', async () => {
  const t = await tokenize(
    '> [!WARNING]\n> **Note:** text\n::: {.pagebreak}\n[x]{custom-style="Highlight Yellow"}\n## Title {#top}\n[[INCLUDE: a.md]]\nVersion {{version}}.'
  );
  has(scopesOf(t, 0, 'WARNING'), 'keyword.other.callout.pydoc');
  has(scopesOf(t, 1, '**Note:**'), 'keyword.other.callout.pydoc');
  has(scopesOf(t, 2, ':::'), 'punctuation.definition.div.pydoc');
  has(scopesOf(t, 2, '.pagebreak'), 'entity.other.attribute-name.class.pydoc');
  has(scopesOf(t, 3, 'custom-style'), 'entity.other.attribute-name.pydoc');
  has(scopesOf(t, 4, '#top'), 'entity.other.attribute-name.id.pydoc');
  has(scopesOf(t, 5, 'INCLUDE'), 'keyword.control.directive.pydoc');
  has(scopesOf(t, 6, '{{version}}'), 'variable.other.pydoc');
});

test('braces in prose are not attributes', async () => {
  const t = await tokenize('Use {x} in a sentence, not as attributes.');
  assert.ok(!t[0].some(([, scopes]) => scopes.some((s) => s.startsWith('entity.other.attribute-name'))));
});

test(
  'py-doc syntax shown in a code block is left as code (needs PYDOC_MARKDOWN_GRAMMAR, see tokenize.js)',
  { skip: !process.env.PYDOC_MARKDOWN_GRAMMAR && 'the stand-in Markdown grammar has no code blocks' },
  async () => {
    const t = await tokenize('```markdown\n[[INCLUDE: a.md]]\n> [!NOTE]\n```\n\nSee `{{version}}` and `[[PAGEBREAK]]`.');
    for (const line of [t[1], t[2], t[5]]) {
      assert.ok(!line.some(([, scopes]) => scopes.some((s) => s.endsWith('.pydoc'))), JSON.stringify(line));
    }
  }
);
