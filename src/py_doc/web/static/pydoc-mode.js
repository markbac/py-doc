/* py-doc's own Markdown in the web editor: an overlay on CodeMirror's GitHub Markdown mode.
 *
 * It marks what the VS Code extension's grammar marks (editors/vscode/syntaxes/pydoc.markdown.tmLanguage.json):
 * directives such as [[LANDSCAPE]] and [[INCLUDE: a.md]], conditions, {{variables}}, callouts, ::: divs,
 * {#id .class key=value} attributes, and the cells of a [[LISTTABLE]] table. Nothing is marked inside a
 * fenced code block or an inline code span, where py-doc leaves the text alone too.
 * tests/test_web.py checks the patterns below against the grammar's.
 */
(function () {
  "use strict";
  if (!window.CodeMirror) return;

  // The patterns, as in the grammar. DIRECTIVE is anchored at the start of a line, as py-doc reads it.
  const DIRECTIVE = /^(\[\[)([A-Z][A-Z-]*)(?:(:)\s*([^\]]*))?(\]\])/;
  const VARIABLE = /\{\{\s*[A-Za-z_][A-Za-z0-9_]*\s*\}\}/;
  const CALLOUT = /(\[!)(note|tip|important|warning|caution)(\])/i;
  const CALLOUT_BOLD = /\*\*(Note|Tip|Important|Warning|Caution):\*\*/;
  const SLOT = /(\[\[)(BLOCK)(:)\s*([\w-]+)\s*(\]\])/;
  const CELL_STYLE = /\s*\{(?:\s*(?:bg|valign)=[^\s}]+)+\s*\}/;
  const MERGE = /\s*[<^]\s*(?=\|)/;

  // py-doc's directives. Others are marked too, but differently, so a typo such as [[LANDSCAPEE]] stands out.
  const KNOWN = new Set(["INCLUDE", "INCLUDE-CODE", "INSERTCONTENT", "IF", "NOT", "ENDIF", "PAGEBREAK", "LANDSCAPE",
    "PORTRAIT", "LISTTABLE", "BLOCK", "ENDBLOCK", "CAPTION", "STYLE"]);
  const CONDITIONS = new Set(["IF", "NOT", "ENDIF"]);
  const PATHS = new Set(["INCLUDE", "INCLUDE-CODE", "INSERTCONTENT"]);
  const TOOLTIPS = {
    INCLUDE: "Put another Markdown file here", "INCLUDE-CODE": "Put a file here as a code block",
    INSERTCONTENT: "Put another file's content here", IF: "Keep what follows when the condition holds",
    NOT: "Keep what follows when the condition does not hold", ENDIF: "End of an [[IF:]] or [[NOT:]]",
    PAGEBREAK: "A page break, or a new slide in a deck", LANDSCAPE: "Landscape pages from here",
    PORTRAIT: "Portrait pages from here", LISTTABLE: "A table whose cells hold paragraphs, lists and blocks",
    BLOCK: "A block placed in a [[LISTTABLE]] cell", ENDBLOCK: "End of a [[BLOCK:]]",
    CAPTION: "The caption of the next table or figure", STYLE: "A Word style for what follows",
  };

  function directiveTokens(state, match) {
    const name = match[2];
    const kind = !KNOWN.has(name) ? "pydoc-unknown" : CONDITIONS.has(name) ? "pydoc-condition" : "pydoc-directive";
    // The parts, in order: [[  NAME  :  argument  ]]
    state.queue = [[match[1], "pydoc-bracket"], [name, kind]];
    if (match[3]) {
      const argument = match[4] || "";
      // The colon and the spaces after it: everything between the name and the argument
      state.queue.push([match[0].slice(2 + name.length, match[0].length - 2 - argument.length), "pydoc-bracket"]);
      if (argument) state.queue.push([argument, PATHS.has(name) ? "pydoc-path" : "pydoc-argument"]);
    }
    state.queue.push([match[5], "pydoc-bracket"]);
  }

  // A line of a fenced code block: Markdown's mode colours the code by its language, and this only gives
  // the line a background. Combined, so the code's own colours stay.
  // (CodeMirror's overlay reads combineTokens from the overlay's state, for the token just returned.)
  function codeLine(state) {
    state.combineTokens = true;
    return "line-background-pydoc-code";
  }

  const overlay = {
    startState: () => ({ fence: null, listtable: false, queue: [], inCode: 0 }),
    copyState: (s) => ({ fence: s.fence, listtable: s.listtable, queue: s.queue.slice(), inCode: s.inCode }),
    blankLine: (state) => { state.listtable = false; },
    token(stream, state) {
      state.combineTokens = false;  // py-doc's styles replace Markdown's; codeLine() asks for both
      if (state.queue.length) {
        const [text, style] = state.queue.shift();
        for (let i = 0; i < text.length; i++) stream.next();
        return style;
      }
      if (stream.sol()) {
        const line = stream.string;
        const fence = /^\s{0,3}(`{3,}|~{3,})/.exec(line);
        if (state.fence) {
          if (fence && fence[1][0] === state.fence[0] && fence[1].length >= state.fence.length && /^\s*(`+|~+)\s*$/.test(line)) state.fence = null;
          stream.skipToEnd();
          return codeLine(state);
        }
        if (fence) { state.fence = fence[1]; stream.skipToEnd(); return codeLine(state); }
        if (!line.startsWith("|")) state.listtable = false;
        const directive = DIRECTIVE.exec(line);
        if (directive && /^\s*$/.test(line.slice(directive[0].length))) {
          if (directive[2] === "LISTTABLE") state.listtable = true;
          directiveTokens(state, directive);
          return this.token(stream, state);
        }
        const div = /^(:{3,})(\s*(?:\{[^}]*\}|[\w-]+)?\s*)$/.exec(line);
        if (div) {
          stream.match(div[1]);
          state.queue = div[2] ? [[div[2], "pydoc-div-name"]] : [];
          return "pydoc-div";
        }
      }
      // Inline code: py-doc leaves it alone
      if (stream.peek() === "`") {
        const ticks = stream.match(/^`+/)[0];
        const close = stream.string.indexOf(ticks, stream.pos);
        if (close >= 0) stream.pos = close + ticks.length; else stream.skipToEnd();
        return null;
      }
      const rest = stream.string.slice(stream.pos);
      let m;
      if ((m = rest.match(VARIABLE)) && m.index === 0) { stream.pos += m[0].length; return "pydoc-variable"; }
      if ((m = rest.match(CALLOUT)) && m.index === 0) { stream.pos += m[0].length; return "pydoc-callout"; }
      if (/^>\s?$/.test(stream.string.slice(0, stream.pos)) && (m = rest.match(CALLOUT_BOLD)) && m.index === 0) {
        stream.pos += m[0].length; return "pydoc-callout";
      }
      if (state.listtable) {
        const before = stream.string[stream.pos - 1];
        if ((m = rest.match(SLOT)) && m.index === 0) { directiveTokens(state, m); return this.token(stream, state); }
        if (before === "|" && (m = rest.match(CELL_STYLE)) && m.index === 0) { stream.pos += m[0].length; return "pydoc-attributes"; }
        if (before === "|" && (m = rest.match(MERGE)) && m.index === 0) { stream.pos += m[0].length; return "pydoc-merge"; }
        if (stream.peek() === "|") { stream.next(); return "pydoc-cell"; }
      }
      // {#id .class key=value}: after ], ) or `, or at the end of a heading
      if (stream.peek() === "{" && stream.string[stream.pos + 1] !== "{") {
        const before = stream.string[stream.pos - 1];
        const attrs = /^\{[^{}\n]*\}(?!\})/.exec(rest);
        const heading = /^#{1,6}\s/.test(stream.string) && /^\{[#.][^{}]*\}\s*$/.test(rest);
        if (attrs && ("])`".includes(before) || heading)) { stream.pos += attrs[0].length; return "pydoc-attributes"; }
      }
      stream.next();
      // Skip ahead to the next character that could start something, so long lines stay fast
      while (!stream.eol() && !"[{`!*|<^".includes(stream.peek())) stream.next();
      return null;
    },
  };

  // GitHub Markdown, with the YAML front matter at the top of a file read as YAML
  const gfm = { name: "gfm", highlightFormatting: true, fencedCodeBlockHighlighting: true };
  const markdown = CodeMirror.modes["yaml-frontmatter"] ? { name: "yaml-frontmatter", base: gfm } : gfm;
  CodeMirror.defineMode("pydoc-markdown", (config) => CodeMirror.overlayMode(
    // Not combined: where py-doc marks text, its style replaces Markdown's (which reads [[...]] as a link)
    CodeMirror.getMode(config, markdown), overlay, false));
  window.PYDOC_TOOLTIPS = TOOLTIPS;
})();
