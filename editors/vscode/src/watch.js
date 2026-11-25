'use strict';

// The live preview: runs `py-doc preview FILE --kind KIND --stdin --no-open` as a child process, shows what it
// prints in an output channel, reads the address it serves from its "serving http://..." line, and opens that
// in VS Code's Simple Browser beside the editor.
//
// `py-doc preview` writes only the preview page, to a temporary folder it removes when it stops, so nothing is
// left beside the Markdown. It keeps running when the preview moves to another file: the extension writes the
// file on its standard input, and the page in the Simple Browser reloads with it, so following the editor is
// one build and no new tab. Closing standard input stops it.
//
// A py-doc older than `py-doc preview` is run as before, with `py-doc docx|slides|poster FILE --watch`, which
// also writes the document beside the Markdown and starts again for each file.
//
// py-doc picks a free port unless the pydoc.watch.port setting names one, so two windows never fight over a
// port. One preview runs at a time. A build that fails after the preview opened ("Error: ..." on a line) is
// also shown as a warning.

const path = require('path');
const { spawn, execFile } = require('child_process');

const START_TIMEOUT = 180000;  // ms: a first build may have to start the tool container
const STOP_TIMEOUT = 5000;
const SERVING = /^serving (http:\/\/127\.0\.0\.1:\d+\/)/m;
const FAILED = /^Error: (.+?)\r?$/m;  // what py-doc prints when a build on save fails
const BUILT = /^built /m;
const NO_PREVIEW_COMMAND = /invalid choice: 'preview'|unknown command.*preview|No such command/i;

class LiveWatch {
  /**
   * @param vscode the vscode module
   * @param options.command the program and its first arguments, in place of the pydoc.executable setting (tests)
   */
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.command = options.command || null;
    this.child = null;
    this.legacy = false;  // whether the running preview is `--watch`, which cannot move to another file
    this.address = null;
    this.filePath = null;  // the file being previewed
    this.format = null;  // docx, slides or poster
    this.lastError = null;  // the build error last shown, so a repeated one is not shown again
    this.noPreviewCommand = false;  // this py-doc has no `preview`: use --watch until the window reloads
    this.output = vscode.window.createOutputChannel('py-doc live preview');
  }

  get running() {
    return this.child !== null;
  }

  /**
   * Preview filePath as `format` (docx, slides or poster). A running `py-doc preview` moves to it, in the same
   * tab; otherwise py-doc is started and the Simple Browser opened. Resolves to the address, or null.
   */
  async start(format, filePath, cwd) {
    if (this.running && !this.legacy && this.child.stdin && this.child.stdin.writable) {
      if (filePath === this.filePath && format === this.format) return this.address;
      this.filePath = filePath;
      this.format = format;
      this.lastError = null;
      this.child.stdin.write(JSON.stringify({ file: filePath, kind: format }) + '\n');
      return this.address;
    }
    await this.stop();
    let address = this.noPreviewCommand ? undefined : await this.launch(format, filePath, cwd, false);
    if (address === undefined) {
      this.noPreviewCommand = true;
      this.output.appendLine('This py-doc has no `py-doc preview`, so the preview uses --watch, which also writes '
        + 'the document beside the Markdown. Update py-doc for faster previews that write nothing.');
      address = await this.launch(format, filePath, cwd, true);
    }
    return address || null;
  }

  /** Start py-doc. Resolves to its address, to null if it failed, or to undefined if it has no `preview`. */
  async launch(format, filePath, cwd, legacy) {
    const config = this.vscode.workspace.getConfiguration('pydoc');
    const [program, ...first] = this.command || [config.get('executable', 'py-doc')];
    const port = config.get('watch.port', 0);
    const ports = port ? ['--port', String(port)] : [];
    const args = legacy
      ? [...first, format, filePath, '--watch', '--no-open', ...ports]
      : [...first, 'preview', filePath, '--kind', format, '--stdin', '--no-open', ...ports];

    this.filePath = filePath;
    this.format = format;
    this.legacy = legacy;
    this.lastError = null;
    if (!legacy) this.output.clear();
    this.output.appendLine(`> ${program} ${args.join(' ')}`);
    const child = spawn(program, args, {
      cwd: cwd || path.dirname(filePath),
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' },
      stdio: [legacy ? 'ignore' : 'pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    this.child = child;
    if (child.stdin) child.stdin.on('error', () => {});  // py-doc gone: its exit says why

    let printed = '';
    const started = new Promise((resolve) => {
      let seen = '';
      const timer = setTimeout(() => resolve(null), START_TIMEOUT);
      const done = (address) => {
        clearTimeout(timer);
        resolve(address);
      };
      const read = (chunk) => {
        const text = chunk.toString();
        printed += text.length < 4000 ? text : '';
        this.output.append(text);
        if (seen === null) this.report(text);
        if (seen !== null) {
          seen += text;
          const m = seen.match(SERVING);
          if (m) {
            const rest = seen.slice(m.index + m[0].length);
            seen = null;  // found: the rest of the output is only shown
            if (rest) this.report(rest);
            done(m[1]);
          }
        }
      };
      child.stdout.on('data', read);
      child.stderr.on('data', (chunk) => this.output.append(chunk.toString()));
      child.stderr.on('data', (chunk) => { printed += chunk.toString(); });
      child.on('error', (err) => {
        this.output.appendLine(`Cannot start ${program}: ${err.message}. Set pydoc.executable to the py-doc program.`);
        done(null);
      });
      child.on('exit', (code, signal) => {
        this.output.appendLine(`py-doc stopped (${signal || `exit status ${code}`})`);
        if (this.child === child) {
          this.child = null;
          this.filePath = null;
          this.address = null;
        }
        done(null);
      });
    });

    const address = await this.vscode.window.withProgress(
      { location: this.vscode.ProgressLocation.Window, title: `py-doc: starting the ${format} preview` },
      () => started
    );
    if (child.stoppedByUs) return null;  // stopped, or replaced by another preview, while it started
    if (address) {
      this.address = address;
      const { Uri, ViewColumn } = this.vscode;
      await this.vscode.commands.executeCommand('simpleBrowser.api.open', Uri.parse(address), {
        viewColumn: ViewColumn.Beside,
        preserveFocus: true,
      });
      return address;
    }
    await this.stop();
    if (!legacy && NO_PREVIEW_COMMAND.test(printed)) return undefined;
    this.output.show(true);
    this.vscode.window.showErrorMessage(`The py-doc ${format} preview did not start. See the "py-doc live preview" output.`);
    return null;
  }

  /** Show a build failure from what py-doc printed after the preview opened, once until a build succeeds. */
  report(text) {
    const failed = text.match(FAILED);
    if (failed && failed[1] !== this.lastError) {
      this.lastError = failed[1];
      this.vscode.window.showWarningMessage(`py-doc preview: ${failed[1]}`);
    } else if (BUILT.test(text)) {
      this.lastError = null;
    }
  }

  /** Stop the running preview, and its whole process tree. Resolves to whether one was running. */
  stop() {
    const child = this.child;
    this.child = null;
    this.filePath = null;
    this.address = null;
    if (child) child.stoppedByUs = true;
    if (!child || child.exitCode !== null || child.signalCode !== null) return Promise.resolve(false);
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        kill(child);
        resolve(true);
      }, STOP_TIMEOUT);
      child.once('exit', () => {
        clearTimeout(timer);
        resolve(true);
      });
      if (child.stdin && child.stdin.writable) {
        child.stdin.end();  // `py-doc preview` stops by itself, and removes its temporary folder
        setTimeout(() => { if (child.exitCode === null && child.signalCode === null) kill(child); }, 1500);
      } else {
        kill(child);
      }
    });
  }

  dispose() {
    this.stop();
    this.output.dispose();
  }
}

// End the process tree: py-doc.exe is a launcher that starts Python, so /T ends the tree, not only the launcher
function kill(child) {
  if (process.platform === 'win32') {
    execFile('taskkill', ['/pid', String(child.pid), '/T', '/F'], () => {});
  } else {
    child.kill('SIGTERM');
  }
}

module.exports = { LiveWatch, SERVING, FAILED };
