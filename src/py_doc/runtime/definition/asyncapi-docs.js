#!/usr/bin/env node
/*
 * AsyncAPI documentation with the AsyncAPI generator and its official templates, installed in the image.
 *
 * usage: node asyncapi-docs.js SPEC OUTDIR (markdown|html) [NAME=VALUE ...]
 *
 * markdown  @asyncapi/markdown-template: OUTDIR/asyncapi.md
 * html      @asyncapi/html-template, one self-contained page: OUTDIR/index.html
 *
 * NAME=VALUE pairs are template parameters. The templates are used where they are installed, so nothing is
 * downloaded and the run needs no network. An invalid document stops the run with the parser's messages.
 *
 * The generator compiles a template into its own folder (__transpiled) the first time. The image build runs
 * `asyncapi-docs.js --compile` as root, so later runs, as an ordinary user, use the compiled copy.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const SAMPLE = 'asyncapi: 2.6.0\ninfo: {title: Sample, version: 1.0.0}\nchannels:\n  sample:\n    subscribe:\n      message: {payload: {type: string}}\n';

const TEMPLATES = {
  markdown: { name: '@asyncapi/markdown-template', params: { toc: 'true' } },
  html: { name: '@asyncapi/html-template', params: { singleFile: 'true' } },
};

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

async function compileAll() {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'asyncapi-'));
  const spec = path.join(folder, 'sample.yaml');
  fs.writeFileSync(spec, SAMPLE);
  for (const format of Object.keys(TEMPLATES)) {
    await main([spec, path.join(folder, format), format], true);
  }
  fs.rmSync(folder, { recursive: true, force: true });
}

async function main(argv, compile = false) {
  const [spec, outDir, format, ...pairs] = argv;
  if (!spec || !outDir || !TEMPLATES[format]) {
    fail('usage: asyncapi-docs.js SPEC OUTDIR (markdown|html) [NAME=VALUE ...]');
  }
  const template = TEMPLATES[format];
  const params = { ...template.params };
  for (const pair of pairs) {
    const at = pair.indexOf('=');
    if (at < 1) fail(`'${pair}' is not NAME=VALUE`);
    params[pair.slice(0, at)] = pair.slice(at + 1);
  }
  const loaded = require('@asyncapi/generator');
  const Generator = loaded.default || loaded;
  const templateDir = path.dirname(require.resolve(`${template.name}/package.json`));
  const compiled = fs.existsSync(path.join(templateDir, '__transpiled'));
  const generator = new Generator(templateDir, path.resolve(outDir), {
    forceWrite: true,
    install: false,
    compile: compile || !compiled,
    templateParams: params,
  });
  try {
    await generator.generateFromFile(path.resolve(spec));
  } catch (error) {
    const problems = error.validationErrors || error.diagnostics;
    if (!problems && !/parse|valid/i.test(error.title || '')) {
      fail(`The AsyncAPI generator failed on ${spec}: ${error.stack || error.message}`);
    }
    const details = (problems || [])
      .map((d) => `  ${d.title || d.message}${d.location ? ` (${JSON.stringify(d.location.jsonPointer || d.location)})` : ''}`)
      .join('\n');
    fail(`${spec} is not a valid AsyncAPI document: ${error.title || error.message}${details ? `\n${details}` : ''}`);
  }
}

const args = process.argv.slice(2);
(args[0] === '--compile' ? compileAll() : main(args)).catch((error) => fail(error && error.stack ? error.stack : String(error)));
