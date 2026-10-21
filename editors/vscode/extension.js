/**
 * vscode-py-doc-preview: previews of py-doc Markdown in VS Code.
 *
 *  - The instant preview (src/plugin.js) extends VS Code's built-in Markdown preview as you type.
 *  - The live preview (src/watch.js) runs `py-doc docx|slides|poster --watch` on the open file and shows
 *    the page it serves beside the editor, rebuilt with every diagram on each save.
 *  - Both choose the format of a file the same way (src/detect.js).
 */

'use strict';

const { pyDocPlugin } = require('./src/plugin');
const { detectFormat, detectDocumentFormat } = require('./src/detect');
const { parseFrontMatter } = require('./src/frontmatter');

let vscode;
try { vscode = require('vscode'); } catch (e) { vscode = null; }  // absent when the tests run in Node

let live = null;

function activate(context) {
  if (!vscode) return;
  const { LiveWatch } = require('./src/watch');
  live = new LiveWatch(vscode);

  // Run a live preview command on the Markdown file of the active editor
  const onActiveFile = (command) => async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No active Markdown file to preview.');
      return;
    }
    const doc = editor.document;
    if (doc.isUntitled) {
      vscode.window.showErrorMessage('Save the file first: py-doc builds it from disk.');
      return;
    }
    const folder = vscode.workspace.getWorkspaceFolder(doc.uri);  // where py-doc.yml and themes are found
    await live.start(command || detectDocumentFormat(doc), doc.uri.fsPath, folder ? folder.uri.fsPath : undefined);
  };

  context.subscriptions.push(
    vscode.commands.registerCommand('pydoc.openLiveWatch', onActiveFile(null)),
    vscode.commands.registerCommand('pydoc.openDocxWatch', onActiveFile('docx')),
    vscode.commands.registerCommand('pydoc.openSlidesWatch', onActiveFile('slides')),
    vscode.commands.registerCommand('pydoc.openPosterWatch', onActiveFile('poster')),
    vscode.commands.registerCommand('pydoc.stopLiveWatch', async () => {
      if (await live.stop()) vscode.window.showInformationMessage('py-doc live preview stopped.');
    }),
    live
  );
}

function deactivate() {
  return live ? live.stop() : undefined;
}

function extendMarkdownIt(md) {
  return md.use(pyDocPlugin);
}

module.exports = {
  activate,
  deactivate,
  extendMarkdownIt,
  pyDocPlugin,
  parseFrontMatter,
  detectFormat,
  detectDocumentFormat
};
