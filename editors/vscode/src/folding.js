'use strict';

// Folding for py-doc's blocks in Markdown, beside VS Code's own folding of headings and lists:
// [[IF:]] or [[NOT:]] to [[ENDIF]], [[BLOCK: name]] to [[ENDBLOCK]], [[LANDSCAPE]] to [[PORTRAIT]], a
// [[LISTTABLE]] with its rows, and ::: fenced divs. Nothing inside a code fence counts.

const FENCE = /^ {0,3}(`{3,}|~{3,})/;
const IF = /^\[\[(IF|NOT):[^\]]*\]\]\s*$/;
const ENDIF = /^\[\[ENDIF\]\]\s*$/;
const BLOCK = /^\[\[BLOCK:[^\]]*\]\]\s*$/;
const ENDBLOCK = /^\[\[ENDBLOCK\]\]\s*$/;
const LANDSCAPE = /^\[\[LANDSCAPE\]\]\s*$/;
const PORTRAIT = /^\[\[PORTRAIT\]\]\s*$/;
const LISTTABLE = /^\[\[LISTTABLE(:[^\]]*)?\]\]\s*$/;
const ROW = /^\|.*\|\s*$/;
const DIV_OPEN = /^(:{3,})\s*(\{[^}]*\}|[\w-]+)\s*$/;
const DIV_CLOSE = /^(:{3,})\s*$/;

// The ranges to fold in `lines`, as {start, end} line numbers (0-based, end included)
function foldingRanges(lines) {
  const ranges = [];
  const open = { if: [], block: [], landscape: [], div: [] };
  let fence = null;
  const close = (stack, end) => {
    const start = stack.pop();
    if (start !== undefined && end > start) ranges.push({ start, end });
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const marker = line.match(FENCE);
    if (fence) {
      if (marker && marker[1][0] === fence[0] && marker[1].length >= fence.length && !line.trim().replace(/[`~]/g, '')) {
        fence = null;
      }
      continue;
    }
    if (marker) {
      fence = marker[1];
      continue;
    }
    if (IF.test(line)) open.if.push(i);
    else if (ENDIF.test(line)) close(open.if, i);
    else if (BLOCK.test(line)) open.block.push(i);
    else if (ENDBLOCK.test(line)) close(open.block, i);
    else if (LANDSCAPE.test(line)) open.landscape.push(i);
    else if (PORTRAIT.test(line)) close(open.landscape, i);
    else if (DIV_OPEN.test(line)) open.div.push(i);
    else if (DIV_CLOSE.test(line)) close(open.div, i);
    else if (LISTTABLE.test(line)) {
      let end = i;
      while (end + 1 < lines.length && ROW.test(lines[end + 1])) end++;
      if (end > i) ranges.push({ start: i, end });
      i = end;
    }
  }
  return ranges.sort((a, b) => a.start - b.start || b.end - a.end);
}

module.exports = { foldingRanges };
