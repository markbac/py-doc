'use strict';

const { test } = require('node:test');
const assert = require('node:assert');
const { foldingRanges } = require('../src/folding');

const fold = (text) => foldingRanges(text.split('\n')).map(({ start, end }) => [start, end]);

test('conditions, blocks, landscape sections, rich tables and fenced divs fold', () => {
  const text = [
    '[[IF: internal]]', //  0
    'Staff only.', //       1
    '[[NOT: draft]]', //    2
    'Released.', //         3
    '[[ENDIF]]', //         4
    '[[ENDIF]]', //         5
    '[[LISTTABLE]]', //     6
    '| a | b |', //         7
    '| c | d |', //         8
    'After.', //            9
    '[[BLOCK: wiring]]', // 10
    'x', //                 11
    '[[ENDBLOCK]]', //      12
    '[[LANDSCAPE]]', //     13
    'Wide.', //             14
    '[[PORTRAIT]]', //      15
    '::: {.notes}', //      16
    'Said aloud.', //       17
    ':::' //                18
  ].join('\n');
  assert.deepStrictEqual(fold(text), [[0, 5], [2, 4], [6, 8], [10, 12], [13, 15], [16, 18]]);
});

test('nothing in a code fence folds, and an unclosed block does not either', () => {
  assert.deepStrictEqual(fold('```markdown\n[[IF: a]]\nx\n[[ENDIF]]\n```\n[[BLOCK: b]]\ny'), []);
  assert.deepStrictEqual(fold('[[LISTTABLE]]\nno rows'), []);
});

test('a fenced div inside another folds on its own', () => {
  assert.deepStrictEqual(fold(':::: columns\n::: column\na\n:::\n::::'), [[0, 4], [1, 3]]);
});
