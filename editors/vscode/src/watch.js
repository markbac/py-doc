'use strict';

// The live preview: runs `py-doc <command> FILE --watch --no-open` as a child process, shows what it prints
// in an output channel, reads the address it serves from its "serving http://..." line, and opens that in
// VS Code's Simple Browser beside the editor. py-doc picks a free port unless the pydoc.watch.port setting
// names one, so two windows never fight over a port. One preview runs at a time: starting another stops it
// first. A build that fails after the preview opened ("Error: ..." on a line) is also shown as a warning.

const path = require('path');
const { spawn, execFile } = require('child_process');

const START_TIMEOUT = 180000;  // ms: a first build may have to start the tool container
const STOP_TIMEOUT = 5000;
const SERVING = /^serving (http:\/\/127\.0\.0\.1:\d+\/)/m;
const FAILED = /^Error: (.+?)\r?$/m;  // what py-doc --watch prints when a build on save fails
const BUILT = /^built in /m;

class LiveWatch {
  /**
   * @param vscode the vscode module
   * @param options.command the program and its first arguments, in place of the pydoc.executable setting (tests)
   */
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.command = options.command || null;
    this.child = null;
    this.filePath = null;  // the file being previewed
    this.lastError = null;  // the build error last shown, so a repeated one is not shown again
    this.output = vscode.window.createOutputChannel('py-doc live preview');
  }

  get running() {
    return this.child !== null;
  }

  /** Start the preview of filePath with py-doc's `command` (docx, slides or poster). Resolves to its address, or null. */
  async start(command, filePath, cwd) {
    await this.stop();
    const config = this.vscode.workspace.getConfiguration('pydoc');
    const [program, ...first] = this.command || [config.get('executable', 'py-doc')];
    const port = config.get('watch.port', 0);
    const args = [...first, command, filePath, '--watch', '--no-open', ...(port ? ['--port', String(port)] : [])];

    this.filePath = filePath;
    this.lastError = null;
    this.output.clear();
    this.output.appendLine(`> ${program} ${args.join(' ')}`);
    const child = spawn(program, args, {
      cwd: cwd || path.dirname(filePath),
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' },
      windowsHide: true,
    });
    this.child = child;

    const started = new Promise((resolve) => {
      let seen = '';
      const timer = setTimeout(() => resolve(null), START_TIMEOUT);
      const done = (address) => {
        clearTimeout(timer);
        resolve(address);
      };
      child.stdout.on('data', (chunk) => {
        const text = chunk.toString();
        this.output.append(text);
        if (seen === null) this.report(text);
        if (seen !== null) {
          seen += text;
          const m = seen.match(SERVING);
          if (m) {
            seen = null;  // found: the rest of the output is only shown
            done(m[1]);
          }
        }
      });
      child.stderr.on('data', (chunk) => this.output.append(chunk.toString()));
      child.on('error', (err) => {
        this.output.appendLine(`Cannot start ${program}: ${err.message}. Set pydoc.executable to the py-doc program.`);
        done(null);
      });
      child.on('exit', (code, signal) => {
        this.output.appendLine(`py-doc stopped (${signal || `exit status ${code}`})`);
        if (this.child === child) this.child = null;
        done(null);
      });
    });

    const address = await this.vscode.window.withProgress(
      { location: this.vscode.ProgressLocation.Window, title: `py-doc: building the ${command} preview` },
      () => started
    );
    if (child.stoppedByUs) return null;  // stopped, or replaced by another preview, while it started
    if (address) {
      const { Uri, ViewColumn } = this.vscode;
      await this.vscode.commands.executeCommand('simpleBrowser.api.open', Uri.parse(address), {
        viewColumn: ViewColumn.Beside,
        preserveFocus: true,
      });
      return address;
    }
    await this.stop();
    this.output.show(true);
    this.vscode.window.showErrorMessage(`The py-doc ${command} preview did not start. See the "py-doc live preview" output.`);
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
    if (child) child.stoppedByUs = true;
    if (!child || child.exitCode !== null || child.signalCode !== null) return Promise.resolve(false);
    return new Promise((resolve) => {
      const timer = setTimeout(() => resolve(true), STOP_TIMEOUT);
      child.once('exit', () => {
        clearTimeout(timer);
        resolve(true);
      });
      if (process.platform === 'win32') {
        // py-doc.exe is a launcher that starts Python: /T ends the tree, not only the launcher
        execFile('taskkill', ['/pid', String(child.pid), '/T', '/F'], () => {});
      } else {
        child.kill('SIGTERM');
      }
    });
  }

  dispose() {
    this.stop();
    this.output.dispose();
  }
}

module.exports = { LiveWatch, SERVING, FAILED };
