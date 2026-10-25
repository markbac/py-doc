/**
 * vscode-py-doc-preview: the live preview of py-doc Markdown in VS Code.
 *
 * The preview (src/watch.js) runs `py-doc docx|slides|poster --watch` on the open file and shows the page it
 * serves beside the editor, rebuilt on each save. It is py-doc's own output, so every block, diagram and theme
 * looks as it will in the build. The command for a file is chosen from its content (src/detect.js).
 */

'use strict';

const { detectFormat, detectDocumentFormat } = require('./src/detect');

let vscode;
try { vscode = require('vscode'); } catch (e) { vscode = null; }  // absent when the tests run in Node

let live = null;

// Whether a switch to `doc` should move the running preview to it
function follows(doc) {
  return (
    live.running &&
    doc.languageId === 'markdown' &&
    !doc.isUntitled &&
    doc.uri.scheme === 'file' &&
    doc.uri.fsPath !== live.filePath &&
    vscode.workspace.getConfiguration('pydoc').get('watch.followActiveEditor', true)
  );
}

function activate(context) {
  if (!vscode) return;
  const { LiveWatch } = require('./src/watch');
  live = new LiveWatch(vscode);

  const preview = (command, doc) => {
    const folder = vscode.workspace.getWorkspaceFolder(doc.uri);  // where py-doc.yml and themes are found
    return live.start(command || detectDocumentFormat(doc), doc.uri.fsPath, folder ? folder.uri.fsPath : undefined);
  };

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
    await preview(command, doc);
  };

  context.subscriptions.push(
    vscode.commands.registerCommand('pydoc.openLiveWatch', onActiveFile(null)),
    vscode.commands.registerCommand('pydoc.openDocxWatch', onActiveFile('docx')),
    vscode.commands.registerCommand('pydoc.openSlidesWatch', onActiveFile('slides')),
    vscode.commands.registerCommand('pydoc.openPosterWatch', onActiveFile('poster')),
    vscode.commands.registerCommand('pydoc.stopLiveWatch', async () => {
      if (await live.stop()) vscode.window.showInformationMessage('py-doc live preview stopped.');
    }),
    // The preview follows the editor to another Markdown file, unless pydoc.watch.followActiveEditor is off
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && follows(editor.document)) preview(null, editor.document);
    }),
    live
  );
}

function deactivate() {
  return live ? live.stop() : undefined;
}

module.exports = {
  activate,
  deactivate,
  detectFormat,
  detectDocumentFormat
};
