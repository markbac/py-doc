'use strict';

// The live preview against a fake py-doc (a Node script) and a fake vscode module.

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { LiveWatch, SERVING, FAILED } = require('../src/watch');

function fakeVscode(settings = {}) {
  const calls = { browser: [], errors: [], warnings: [], output: [] };
  const vscode = {
    calls,
    window: {
      createOutputChannel: () => ({
        append: (t) => calls.output.push(t),
        appendLine: (t) => calls.output.push(t + '\n'),
        clear: () => {},
        show: () => {},
        dispose: () => {},
      }),
      withProgress: (options, task) => task(),
      showErrorMessage: (m) => calls.errors.push(m),
      showWarningMessage: (m) => calls.warnings.push(m),
    },
    workspace: { getConfiguration: () => ({ get: (key, fallback) => (key in settings ? settings[key] : fallback) }) },
    commands: {
      executeCommand: async (id, uri, options) => {
        if (id === 'simpleBrowser.api.open') calls.browser.push({ address: uri.value, ...options });
      },
    },
    Uri: { parse: (value) => ({ value }) },
    ViewColumn: { Beside: -2 },
    ProgressLocation: { Window: 10 },
  };
  return vscode;
}

// A fake py-doc: prints what --watch prints, then keeps running (or fails, with FAIL set)
const script = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'pydoc-watch-')), 'fake-py-doc.js');
fs.writeFileSync(script, `
const args = process.argv.slice(2);
if (process.env.FAKE_FAIL) { console.error('Error: pandoc failed'); process.exit(1); }
const port = args.includes('--port') ? args[args.indexOf('--port') + 1] : '54321';
console.log('ARGS ' + JSON.stringify(args));
console.log('wrote ' + args[1]);
console.log('serving http://127.0.0.1:' + port + '/');
if (process.env.FAKE_REBUILD_FAIL) {  // a save that does not build, twice, then one that does
  setTimeout(() => console.log('Error: no sections found'), 50);
  setTimeout(() => console.log('Error: no sections found'), 100);
  setTimeout(() => console.log('built in 0.4 s, watching for changes (Ctrl+C stops)'), 150);
  setTimeout(() => console.log('Error: no sections found'), 200);
}
setInterval(() => {}, 1000);
`);

test('the serving line gives the address', () => {
  assert.strictEqual('built in 1.2 s\nserving http://127.0.0.1:61234/\n'.match(SERVING)[1], 'http://127.0.0.1:61234/');
});

test('a preview opens the address py-doc serves, and stops', async (t) => {
  const vscode = fakeVscode();
  const live = new LiveWatch(vscode, { command: [process.execPath, script] });
  t.after(() => live.stop());
  const address = await live.start('docx', path.join(os.tmpdir(), 'guide.md'));
  assert.strictEqual(address, 'http://127.0.0.1:54321/');
  assert.deepStrictEqual(vscode.calls.browser, [{ address: 'http://127.0.0.1:54321/', viewColumn: -2, preserveFocus: true }]);
  assert.ok(live.running);
  assert.strictEqual(live.filePath, path.join(os.tmpdir(), 'guide.md'));
  assert.strictEqual(await live.stop(), true);
  assert.ok(!live.running);
  assert.strictEqual(live.filePath, null);
  assert.strictEqual(await live.stop(), false);
});

test('the port setting is passed on, and a new preview replaces the running one', async (t) => {
  const vscode = fakeVscode({ 'watch.port': 8899 });
  const live = new LiveWatch(vscode, { command: [process.execPath, script] });
  t.after(() => live.stop());
  await live.start('docx', path.join(os.tmpdir(), 'a.md'));
  const first = live.child;
  await live.start('poster', path.join(os.tmpdir(), 'b.md'));
  assert.ok(first.exitCode !== null || first.signalCode !== null, 'the first preview was stopped');
  assert.deepStrictEqual(vscode.calls.browser.map((b) => b.address), ['http://127.0.0.1:8899/', 'http://127.0.0.1:8899/']);
  const argsLine = vscode.calls.output.join('').split('\n').filter((l) => l.startsWith('ARGS ')).pop();
  assert.deepStrictEqual(JSON.parse(argsLine.slice(5)), ['poster', path.join(os.tmpdir(), 'b.md'), '--watch', '--no-open', '--port', '8899']);
  await live.stop();
});

test('a preview that fails says so, and opens nothing', async () => {
  process.env.FAKE_FAIL = '1';
  try {
    const vscode = fakeVscode();
    const live = new LiveWatch(vscode, { command: [process.execPath, script] });
    assert.strictEqual(await live.start('slides', path.join(os.tmpdir(), 'deck.md')), null);
    assert.deepStrictEqual(vscode.calls.browser, []);
    assert.strictEqual(vscode.calls.errors.length, 1);
    assert.ok(vscode.calls.output.join('').includes('pandoc failed'));
    assert.ok(!live.running);
  } finally {
    delete process.env.FAKE_FAIL;
  }
});

test('a program that cannot be started says so', async () => {
  const vscode = fakeVscode({ executable: path.join(os.tmpdir(), 'no-such-py-doc') });
  const live = new LiveWatch(vscode);
  assert.strictEqual(await live.start('docx', path.join(os.tmpdir(), 'guide.md')), null);
  assert.ok(vscode.calls.output.join('').includes('Cannot start'));
  assert.strictEqual(vscode.calls.errors.length, 1);
});

test('the error line of a failed build is matched without its line ending', () => {
  assert.strictEqual('Error: no sections found\r\n'.match(FAILED)[1], 'no sections found');
});

test('a build that fails after the preview opened is shown once, and again after a good build', async (t) => {
  process.env.FAKE_REBUILD_FAIL = '1';
  const vscode = fakeVscode();
  const live = new LiveWatch(vscode, { command: [process.execPath, script] });
  t.after(() => {
    delete process.env.FAKE_REBUILD_FAIL;
    return live.stop();
  });
  await live.start('poster', path.join(os.tmpdir(), 'poster.md'));
  await new Promise((resolve) => setTimeout(resolve, 600));
  assert.deepStrictEqual(vscode.calls.warnings, ['py-doc preview: no sections found', 'py-doc preview: no sections found']);
});
