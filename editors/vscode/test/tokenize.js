'use strict';

// Tokenizes Markdown with the extension's grammars, through vscode-textmate and Oniguruma, the engine VS Code uses.
// VS Code's own Markdown grammar and the JSON, JavaScript, YAML and Clojure grammars are built into VS Code, not
// published on npm, so they are stand-ins here: a host that does nothing, so the injections run everywhere.
// To test against VS Code's real Markdown grammar, set PYDOC_MARKDOWN_GRAMMAR to a copy of
// extensions/markdown-basics/syntaxes/markdown.tmLanguage.json from the VS Code repository.

const fs = require('fs');
const path = require('path');
const vsctm = require('vscode-textmate');
const oniguruma = require('vscode-oniguruma');

const root = path.join(__dirname, '..');
const manifest = require('../package.json');
const stub = (scopeName) => ({ scopeName, patterns: [], repository: { inline: { patterns: [] } } });
const BUILT_IN = ['text.html.markdown', 'source.json', 'source.js', 'source.yaml', 'source.clojure', 'text.xml'];

let registry;

async function load() {
  if (registry) return registry;
  const wasm = fs.readFileSync(require.resolve('vscode-oniguruma/release/onig.wasm'));
  await oniguruma.loadWASM(wasm.buffer.slice(wasm.byteOffset, wasm.byteOffset + wasm.byteLength));
  const paths = Object.fromEntries(manifest.contributes.grammars.map((g) => [g.scopeName, path.join(root, g.path)]));
  registry = new vsctm.Registry({
    onigLib: Promise.resolve({
      createOnigScanner: (sources) => new oniguruma.OnigScanner(sources),
      createOnigString: (text) => new oniguruma.OnigString(text)
    }),
    loadGrammar: async (scopeName) => {
      const real = process.env.PYDOC_MARKDOWN_GRAMMAR;
      if (scopeName === 'text.html.markdown' && real) return vsctm.parseRawGrammar(fs.readFileSync(real, 'utf8'), real);
      if (BUILT_IN.includes(scopeName)) return vsctm.parseRawGrammar(JSON.stringify(stub(scopeName)), 'stub.json');
      if (!paths[scopeName]) return null;
      return vsctm.parseRawGrammar(fs.readFileSync(paths[scopeName], 'utf8'), paths[scopeName]);
    },
    getInjections: (scopeName) =>
      scopeName === 'text.html.markdown'
        ? manifest.contributes.grammars.filter((g) => (g.injectTo || []).includes(scopeName)).map((g) => g.scopeName)
        : []
  });
  return registry;
}

// The tokens of `text` (Markdown, or the language of `scopeName`), as [text, scopes] pairs, line by line
async function tokenize(text, scopeName = 'text.html.markdown') {
  const grammar = await (await load()).loadGrammar(scopeName);
  let stack = vsctm.INITIAL;
  return text.split('\n').map((line) => {
    const result = grammar.tokenizeLine(line, stack);
    stack = result.ruleStack;
    return result.tokens.map((t) => [line.slice(t.startIndex, t.endIndex), t.scopes]);
  });
}

// The scopes of the first token whose text is `piece`, on the line `line` (0-based) of `tokens`
function scopesOf(tokens, line, piece) {
  const found = tokens[line].find(([text]) => text === piece || text.trim() === piece);
  if (!found) throw new Error(`no token '${piece}' on line ${line}: ${JSON.stringify(tokens[line].map(([t]) => t))}`);
  return found[1].join(' ');
}

module.exports = { tokenize, scopesOf };
