/**
 * vscode-py-doc-preview extension
 *
 * Extends VS Code's built-in Markdown preview for all py-doc outputs:
 *  1. Word Technical Documents (.docx):
 *     - Numbered captions: [[CAPTION:Figure]] text, [[CAPTION:Table]] text
 *     - Word callout boxes: > [!NOTE] and > **Note:** text (Note, Tip, Important, Warning, Caution)
 *     - Page breaks: [[PAGEBREAK]] and ::: {.pagebreak}
 *     - Section breaks: [[LANDSCAPE]] and [[PORTRAIT]]
 *     - Paragraph Word styles: [[STYLE:StyleName]] text
 *     - Directives: [[INCLUDE:...]], [[INCLUDE-CODE:...]], [[IF:...]], [[ENDIF]]
 *  2. PowerPoint Slide Decks (.pptx):
 *     - Section Header slides (# Section Title)
 *     - Content slide cards (## Slide Title) with slide footers
 *     - Responsive two-column layouts (:::: columns / ::: column)
 *     - Speaker notes (::: notes and <!-- notes: ... -->)
 *     - Incremental lists (::: incremental)
 *  3. HTML & PDF Posters (py-doc poster):
 *     - Stat strip (## ... {.stats}) with KPI cards & trend indicators
 *     - Abstract introduction banner (## ... {.abstract})
 *     - Headings with colon accent (## 1. Title: Accent) and class stripping
 *     - Card grid blocks (```cards cols=N style=...```)
 *     - Segments bar blocks (```segments```)
 *     - Flow sequence blocks (```flow```)
 *     - Summary closing banner (## ... {.summary})
 *     - Poster header & footer (paper size, byline, QR code label)
 */

'use strict';

const KINDS = {
  NOTE: { title: 'Note', icon: 'ℹ️', class: 'note' },
  TIP: { title: 'Tip', icon: '💡', class: 'tip' },
  IMPORTANT: { title: 'Important', icon: '❗', class: 'important' },
  WARNING: { title: 'Warning', icon: '⚠️', class: 'warning' },
  CAUTION: { title: 'Caution', icon: '🛑', class: 'caution' },
};

function parseSimpleYaml(yamlStr) {
  const result = {};
  const lines = yamlStr.split('\n');
  let currentKey = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    // Check for nested keys (e.g. footer.left, footer.qr)
    if (line.startsWith('  ') && currentKey) {
      const subColon = trimmed.indexOf(':');
      if (subColon > 0) {
        const subKey = trimmed.slice(0, subColon).trim();
        let subVal = trimmed.slice(subColon + 1).trim();
        if ((subVal.startsWith('"') && subVal.endsWith('"')) || (subVal.startsWith("'") && subVal.endsWith("'"))) {
          subVal = subVal.slice(1, -1);
        }
        if (typeof result[currentKey] !== 'object' || result[currentKey] === null) {
          result[currentKey] = {};
        }
        result[currentKey][subKey] = subVal;
      }
      continue;
    }

    const colonIdx = trimmed.indexOf(':');
    if (colonIdx > 0) {
      const key = trimmed.slice(0, colonIdx).trim();
      let val = trimmed.slice(colonIdx + 1).trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      if (val === '') {
        currentKey = key;
        result[key] = {};
      } else {
        currentKey = key;
        result[key] = val;
      }
    }
  }
  return result;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
}

function renderFrontMatterBlock(meta, docMode) {
  if (!meta || Object.keys(meta).length === 0) return '';

  if (docMode === 'poster') {
    let html = '<div class="pydoc-poster-header">\n';
    if (meta.title) {
      html += `  <h1 class="pydoc-poster-title">${escapeHtml(meta.title)}</h1>\n`;
    }
    if (meta.subtitle) {
      html += `  <div class="pydoc-poster-subtitle">${escapeHtml(meta.subtitle)}</div>\n`;
    }
    if (meta.byline) {
      html += `  <div class="pydoc-poster-byline">${escapeHtml(meta.byline)}</div>\n`;
    }
    html += '  <div class="pydoc-poster-meta">\n';
    if (meta.paper) {
      html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Paper:</span> ${escapeHtml(meta.paper.toUpperCase())}</span>\n`;
    }
    if (meta.document_number) {
      html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Doc #:</span> ${escapeHtml(meta.document_number)}</span>\n`;
    }
    if (meta.version) {
      html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Version:</span> ${escapeHtml(meta.version)}</span>\n`;
    }
    html += '  </div>\n';
    html += '</div>\n';
    return html;
  }

  const isSlide = (docMode === 'slide');
  let html = `<div class="pydoc-frontmatter ${isSlide ? 'pydoc-slide-title' : ''}">\n`;
  if (meta.title) {
    html += `  <h1 class="pydoc-doc-title">${escapeHtml(meta.title)}</h1>\n`;
  }
  if (meta.subtitle) {
    html += `  <div class="pydoc-doc-subtitle">${escapeHtml(meta.subtitle)}</div>\n`;
  }
  html += '  <div class="pydoc-doc-meta">\n';
  if (meta.document_number) {
    html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Doc #:</span> ${escapeHtml(meta.document_number)}</span>\n`;
  }
  if (meta.version) {
    html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Version:</span> ${escapeHtml(meta.version)}</span>\n`;
  }
  if (meta.status) {
    const statusClass = meta.status.toLowerCase() === 'draft' ? 'draft' : 'released';
    html += `    <span class="pydoc-meta-item pydoc-status-${statusClass}"><span class="pydoc-meta-key">Status:</span> ${escapeHtml(meta.status)}</span>\n`;
  }
  if (meta.author) {
    html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Author:</span> ${escapeHtml(meta.author)}</span>\n`;
  }
  if (meta.date) {
    html += `    <span class="pydoc-meta-item"><span class="pydoc-meta-key">Date:</span> ${escapeHtml(meta.date)}</span>\n`;
  }
  html += '  </div>\n';
  html += '</div>\n';
  return html;
}

function pyDocPlugin(md) {
  // 1. Block rule to parse Front Matter at line 0
  md.block.ruler.before('table', 'pydoc_front_matter', (state, startLine, endLine, silent) => {
    if (startLine !== 0) return false;
    const start = state.bMarks[startLine] + state.tShift[startLine];
    const max = state.eMarks[startLine];
    if (state.src.slice(start, max).trim() !== '---') return false;

    let nextLine = startLine + 1;
    let found = false;
    while (nextLine < endLine) {
      const s = state.bMarks[nextLine] + state.tShift[nextLine];
      const m = state.eMarks[nextLine];
      if (state.src.slice(s, m).trim() === '---') {
        found = true;
        break;
      }
      nextLine++;
    }
    if (!found) return false;
    if (silent) return true;

    const yamlContent = state.src.slice(state.eMarks[startLine] + 1, state.bMarks[nextLine]);
    state.line = nextLine + 1;

    const token = state.push('pydoc_front_matter', '', 0);
    token.meta = parseSimpleYaml(yamlContent);
    return true;
  });

  // 2. Block rule for fenced divs (:::: columns, ::: column, ::: notes, ::: incremental)
  md.block.ruler.before('fence', 'pydoc_fenced_div', (state, startLine, endLine, silent) => {
    const start = state.bMarks[startLine] + state.tShift[startLine];
    const max = state.eMarks[startLine];
    const lineText = state.src.slice(start, max).trim();

    const openMatch = lineText.match(/^(:{3,4})\s*(?:\{\.([\w-]+)\}|([\w-]+))?(?:\s+(.*))?$/);
    if (!openMatch) return false;

    const colons = openMatch[1];
    const tag = (openMatch[2] || openMatch[3] || '').trim().toLowerCase();
    const isClosing = !tag && lineText === colons;

    if (isClosing) return false;
    if (silent) return true;

    let nextLine = startLine + 1;
    let found = false;
    let depth = 1;

    while (nextLine < endLine) {
      const s = state.bMarks[nextLine] + state.tShift[nextLine];
      const m = state.eMarks[nextLine];
      const cur = state.src.slice(s, m).trim();

      if (cur.startsWith(colons)) {
        const subMatch = cur.match(/^(:{3,4})\s*(?:\{\.([\w-]+)\}|([\w-]+))?/);
        if (subMatch && subMatch[1] === colons) {
          if (!subMatch[2] && !subMatch[3]) {
            depth--;
            if (depth === 0) {
              found = true;
              break;
            }
          } else {
            depth++;
          }
        }
      }
      nextLine++;
    }

    if (!found) return false;

    if (tag === 'pagebreak') {
      const pbreak = state.push('html_block', '', 0);
      pbreak.content = '<div class="pydoc-pagebreak"><span class="pydoc-pagebreak-line"></span><span class="pydoc-badge">PAGE BREAK</span><span class="pydoc-pagebreak-line"></span></div>\n';
      state.line = nextLine + 1;
      return true;
    }

    const tokenOpen = state.push('pydoc_div_open', 'div', 1);
    tokenOpen.block = true;
    tokenOpen.attrs = [['class', `pydoc-div pydoc-${tag}`]];
    tokenOpen.info = tag;

    if (tag === 'notes') {
      const notesHeader = state.push('html_block', '', 0);
      notesHeader.content = '<div class="pydoc-speaker-notes-header"><span class="pydoc-notes-icon">📝</span> Speaker Notes</div>\n';
    } else if (tag === 'incremental') {
      const incBadge = state.push('html_block', '', 0);
      incBadge.content = '<div class="pydoc-incremental-header"><span class="pydoc-inc-icon">⚡</span> Click-by-click list (incremental)</div>\n';
    }

    state.line = startLine + 1;
    const oldParentType = state.parentType;
    state.parentType = 'div';
    state.md.block.tokenize(state, startLine + 1, nextLine);
    state.parentType = oldParentType;

    const tokenClose = state.push('pydoc_div_close', 'div', -1);
    tokenClose.block = true;

    state.line = nextLine + 1;
    return true;
  });

  // 3. Core rule for py-doc markers, numbered captions, callouts, slides, and posters
  md.core.ruler.push('pydoc_core', (state) => {
    const counters = {};
    const tokens = state.tokens;

    // Detect document mode: 'document' (default), 'slide', or 'poster'
    let docMode = 'document';
    let docTitle = 'py-doc Document';
    let frontMeta = null;

    if (tokens.length > 0 && tokens[0].type === 'pydoc_front_matter' && tokens[0].meta) {
      frontMeta = tokens[0].meta;
      if (frontMeta.title) docTitle = frontMeta.title;

      // Check poster cues
      if (frontMeta.paper || frontMeta.byline || (frontMeta.theme && !frontMeta.split_level)) {
        docMode = 'poster';
      }

      // Check slide cues
      const fmt = (frontMeta.format || frontMeta.output || frontMeta.type || frontMeta.layout || '').toLowerCase();
      if (fmt.includes('pptx') || fmt.includes('slide') || frontMeta.split_level) {
        docMode = 'slide';
      }
    }

    // Check content-based cues if not detected from front matter
    if (docMode === 'document') {
      for (const t of tokens) {
        if (t.type === 'pydoc_div_open' && (t.info === 'columns' || t.info === 'notes' || t.info === 'incremental')) {
          docMode = 'slide';
          break;
        }
        if (t.type === 'heading_open') {
          // Check for poster heading classes
        }
      }
    }

    // Set custom renderer for front matter with docMode
    md.renderer.rules.pydoc_front_matter = (ts, idx) => {
      return renderFrontMatterBlock(ts[idx].meta, docMode);
    };

    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];

      // A. Process HTML comments for speaker notes: <!-- notes: ... -->
      if (token.type === 'html_block') {
        const commentNoteMatch = token.content.match(/<!--\s*notes:\s*([\s\S]*?)\s*-->/i);
        if (commentNoteMatch) {
          const noteText = commentNoteMatch[1].trim();
          token.content = `<div class="pydoc-div pydoc-notes"><div class="pydoc-speaker-notes-header"><span class="pydoc-notes-icon">📝</span> Speaker Notes</div><p>${escapeHtml(noteText)}</p></div>\n`;
          continue;
        }
      }

      // B. Process Headings: {.stats}, {.abstract}, {.summary}, {.references}, and accent colons
      if (token.type === 'heading_open') {
        const next = tokens[i + 1];
        if (next && next.type === 'inline' && next.content) {
          let text = next.content;

          const classMatch = text.match(/\s*\{([.#][\w\s.-]+)\}\s*$/);
          let headingClass = '';
          if (classMatch) {
            headingClass = classMatch[1].replace(/^\./, '').trim();
            text = text.replace(/\s*\{([.#][\w\s.-]+)\}\s*$/, '').trim();
            token.attrs = token.attrs || [];
            token.attrs.push(['class', `pydoc-heading-${headingClass}`]);
          }

          const colonIdx = text.indexOf(':');
          if (colonIdx > 0 && !classMatch) {
            const prefix = text.slice(0, colonIdx + 1);
            const accent = text.slice(colonIdx + 1);
            next.content = '';
            next.children = [new state.Token('html_inline', '', 0)];
            next.children[0].content = `${escapeHtml(prefix)} <span class="pydoc-heading-accent">${escapeHtml(accent)}</span>`;
          } else {
            next.content = text;
            if (classMatch) {
              for (const c of next.children) {
                if (c.type === 'text') {
                  c.content = c.content.replace(/\s*\{([.#][\w\s.-]+)\}\s*$/, '');
                }
              }
            }
          }

          // If heading is {.stats}, transform the table into stat cards
          if (headingClass === 'stats') {
            let tableOpenIdx = -1;
            let tableCloseIdx = -1;
            for (let j = i + 1; j < tokens.length; j++) {
              if (tokens[j].type === 'table_open') tableOpenIdx = j;
              if (tokens[j].type === 'table_close') {
                tableCloseIdx = j;
                break;
              }
              if (tokens[j].type === 'heading_open') break;
            }

            if (tableOpenIdx !== -1 && tableCloseIdx !== -1) {
              const rows = [];
              let curRow = null;
              let inTbody = false;

              for (let k = tableOpenIdx; k <= tableCloseIdx; k++) {
                if (tokens[k].type === 'tbody_open') inTbody = true;
                if (tokens[k].type === 'tbody_close') inTbody = false;
                if (inTbody) {
                  if (tokens[k].type === 'tr_open') curRow = [];
                  if (tokens[k].type === 'tr_close' && curRow) {
                    rows.push(curRow);
                    curRow = null;
                  }
                  if (tokens[k].type === 'inline' && curRow) {
                    curRow.push(tokens[k].content);
                  }
                }
              }

              let statsHtml = '<div class="pydoc-poster-stats">\n';
              for (const r of rows) {
                const val = r[0] || '';
                const label = r[1] || '';
                const change = r[2] || '';
                const verdict = (r[3] || '').toLowerCase().trim();
                const changeClass = verdict ? verdict : (change.startsWith('+') ? 'good' : (change.startsWith('-') ? 'bad' : ''));

                statsHtml += '  <div class="pydoc-stat-card">\n';
                statsHtml += `    <div class="pydoc-stat-value">${escapeHtml(val)}</div>\n`;
                statsHtml += `    <div class="pydoc-stat-label">${escapeHtml(label)}</div>\n`;
                if (change) {
                  statsHtml += `    <div class="pydoc-stat-change ${changeClass}">${escapeHtml(change)}</div>\n`;
                }
                statsHtml += '  </div>\n';
              }
              statsHtml += '</div>\n';

              const replacement = new state.Token('html_block', '', 0);
              replacement.content = statsHtml;
              tokens.splice(tableOpenIdx, (tableCloseIdx - tableOpenIdx + 1), replacement);
            }
          }
        }
      }

      // C. Fenced Poster Blocks: ```cards```, ```segments```, ```flow```
      if (token.type === 'fence') {
        const info = token.info.trim();

        // Cards: ```cards cols=3 style=top```
        if (info.startsWith('cards')) {
          const lines = token.content.split('\n').filter(l => l.trim());
          let cardsHtml = '<div class="pydoc-cards-grid">\n';
          for (const line of lines) {
            const parts = line.split('|').map(s => s.trim());
            if (parts.length >= 2) {
              const title = parts[0];
              const desc = parts[1];
              const color = parts[2] || 'blue';
              cardsHtml += `  <div class="pydoc-card-item pydoc-card-${color}">\n`;
              cardsHtml += `    <div class="pydoc-card-title">${escapeHtml(title)}</div>\n`;
              cardsHtml += `    <div class="pydoc-card-desc">${escapeHtml(desc)}</div>\n`;
              cardsHtml += '  </div>\n';
            }
          }
          cardsHtml += '</div>\n';
          token.type = 'html_block';
          token.content = cardsHtml;
          continue;
        }

        // Segments: ```segments```
        if (info.startsWith('segments')) {
          const lines = token.content.split('\n').filter(l => l.trim());
          let segTitle = '';
          const items = [];
          for (const line of lines) {
            if (line.toLowerCase().startsWith('title:')) {
              segTitle = line.replace(/^title:\s*/i, '');
            } else {
              const parts = line.split('|').map(s => s.trim());
              if (parts.length >= 2) {
                items.push({
                  weight: parts[0],
                  label: parts[1],
                  value: parts[2] || '',
                  color: parts[3] || 'blue'
                });
              }
            }
          }

          let segHtml = '<div class="pydoc-segments-box">\n';
          if (segTitle) {
            segHtml += `  <div class="pydoc-segments-title">${escapeHtml(segTitle)}</div>\n`;
          }
          segHtml += '  <div class="pydoc-segments-bar">\n';
          for (const it of items) {
            segHtml += `    <div class="pydoc-segment-slice pydoc-bg-${it.color}" style="flex: ${it.weight}" title="${escapeHtml(it.label)}: ${escapeHtml(it.value)}"><span class="pydoc-segment-text">${escapeHtml(it.label)}</span></div>\n`;
          }
          segHtml += '  </div>\n';
          segHtml += '</div>\n';
          token.type = 'html_block';
          token.content = segHtml;
          continue;
        }

        // Flow: ```flow```
        if (info.startsWith('flow')) {
          const lines = token.content.split('\n').filter(l => l.trim());
          let flowHtml = '<div class="pydoc-flow-diagram">\n';
          for (const line of lines) {
            const parts = line.split(/-(.*?)->/).map(s => s.trim());
            flowHtml += '  <div class="pydoc-flow-step">\n';
            for (let p = 0; p < parts.length; p++) {
              const item = parts[p];
              if (p % 2 === 0) {
                const nodeMatch = item.match(/^\[(.*?)(?:\|(.*?))?\]$/);
                const nodeText = nodeMatch ? nodeMatch[1] : item;
                const nodeColor = (nodeMatch && nodeMatch[2]) ? nodeMatch[2] : 'blue';
                flowHtml += `    <span class="pydoc-flow-node pydoc-bg-${nodeColor}">${escapeHtml(nodeText)}</span>\n`;
              } else {
                flowHtml += `    <span class="pydoc-flow-arrow">➔ ${escapeHtml(item)}</span>\n`;
              }
            }
            flowHtml += '  </div>\n';
          }
          flowHtml += '</div>\n';
          token.type = 'html_block';
          token.content = flowHtml;
          continue;
        }
      }

      // D. Process Paragraphs containing py-doc markers
      if (token.type === 'paragraph_open') {
        const next = tokens[i + 1];
        if (next && next.type === 'inline' && next.content) {
          const rawLines = next.content.split('\n');
          let hasMarkers = false;

          for (const line of rawLines) {
            const trimmed = line.trim();
            if (
              trimmed === '[[PAGEBREAK]]' ||
              trimmed === '::: {.pagebreak}' ||
              /^\[\[(LANDSCAPE|PORTRAIT)\]\]$/i.test(trimmed) ||
              /^\[\[CAPTION:[A-Za-z0-9 _-]+\]\]/i.test(trimmed) ||
              /^\[\[STYLE:[A-Za-z0-9 _-]+\]\]/i.test(trimmed) ||
              /^\[\[(INCLUDE|INCLUDE-CODE|IF|NOT|ENDIF)(?::.*)?\]\]$/i.test(trimmed)
            ) {
              hasMarkers = true;
              break;
            }
          }

          if (hasMarkers) {
            let renderedHtml = '';
            for (const line of rawLines) {
              const trimmed = line.trim();
              if (!trimmed) continue;

              // Page Break
              if (trimmed === '[[PAGEBREAK]]' || trimmed === '::: {.pagebreak}') {
                renderedHtml += '<div class="pydoc-pagebreak"><span class="pydoc-pagebreak-line"></span><span class="pydoc-badge">PAGE BREAK</span><span class="pydoc-pagebreak-line"></span></div>\n';
                continue;
              }

              // Orientation
              const orientMatch = trimmed.match(/^\[\[(LANDSCAPE|PORTRAIT)\]\]$/i);
              if (orientMatch) {
                const orient = orientMatch[1].toUpperCase();
                renderedHtml += `<div class="pydoc-orientation"><span class="pydoc-pagebreak-line"></span><span class="pydoc-badge">SECTION BREAK (${orient})</span><span class="pydoc-pagebreak-line"></span></div>\n`;
                continue;
              }

              // Directives
              const directiveMatch = trimmed.match(/^\[\[(INCLUDE|INCLUDE-CODE|IF|NOT|ENDIF)(?::\s*([^\]]+))?\]\]$/i);
              if (directiveMatch) {
                const dType = directiveMatch[1].toUpperCase();
                const dArg = (directiveMatch[2] || '').trim();
                renderedHtml += `<div class="pydoc-directive"><span class="pydoc-directive-badge">${escapeHtml(dType)}</span> <code class="pydoc-directive-arg">${escapeHtml(dArg)}</code></div>\n`;
                continue;
              }

              // Numbered Caption
              const capMatch = trimmed.match(/^\[\[CAPTION:([A-Za-z0-9 _-]+)\]\](?:\s*(.*))?$/);
              if (capMatch) {
                const label = capMatch[1].trim();
                const text = (capMatch[2] || '').trim();
                counters[label] = (counters[label] || 0) + 1;
                const num = counters[label];
                renderedHtml += `<div class="pydoc-caption"><span class="pydoc-caption-num">${escapeHtml(label)} ${num}:</span> <span class="pydoc-caption-text">${md.renderInline(text)}</span></div>\n`;
                continue;
              }

              // Style
              const styleMatch = trimmed.match(/^\[\[STYLE:([A-Za-z0-9 _-]+)\]\](?:\s*(.*))?$/);
              if (styleMatch) {
                const styleName = styleMatch[1].trim();
                const text = (styleMatch[2] || '').trim();
                renderedHtml += `<div class="pydoc-styled-block" data-word-style="${escapeHtml(styleName)}"><span class="pydoc-style-pill" title="Word Paragraph Style">${escapeHtml(styleName)}</span>${md.renderInline(text)}</div>\n`;
                continue;
              }

              renderedHtml += `<p>${md.renderInline(line)}</p>\n`;
            }

            tokens[i] = new state.Token('html_block', '', 0);
            tokens[i].content = renderedHtml;
            tokens.splice(i + 1, 2);
            continue;
          }
        }
      }

      // E. Process Blockquotes for Callouts / Admonitions
      if (token.type === 'blockquote_open') {
        let firstInlineIdx = -1;
        for (let j = i + 1; j < tokens.length; j++) {
          if (tokens[j].type === 'blockquote_close') break;
          if (tokens[j].type === 'inline') {
            firstInlineIdx = j;
            break;
          }
        }

        if (firstInlineIdx !== -1) {
          const inlineToken = tokens[firstInlineIdx];
          const rawContent = inlineToken.content.trim();
          const ghMatch = rawContent.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i);
          const boldMatch = rawContent.match(/^\*\*(Note|Tip|Important|Warning|Caution)\s*:\*\*/i)
            || rawContent.match(/^\*\*(Note|Tip|Important|Warning|Caution)\*\*\s*:/i);

          const kindRaw = ghMatch ? ghMatch[1] : (boldMatch ? boldMatch[1] : null);

          if (kindRaw) {
            const kindKey = kindRaw.toUpperCase();
            const info = KINDS[kindKey] || { title: kindKey, icon: 'ℹ️', class: 'note' };

            token.attrs = [['class', `pydoc-callout pydoc-callout-${info.class}`]];

            let bodyText = rawContent;
            if (ghMatch) {
              bodyText = bodyText.replace(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*/i, '');
            } else if (boldMatch) {
              bodyText = bodyText.replace(/^\*\*(Note|Tip|Important|Warning|Caution)\s*:\*\*\s*/i, '')
                                 .replace(/^\*\*(Note|Tip|Important|Warning|Caution)\*\*\s*:\s*/i, '');
            }

            const headerBlock = new state.Token('html_block', '', 0);
            headerBlock.content = `<div class="pydoc-callout-header"><span class="pydoc-callout-icon">${info.icon}</span><span class="pydoc-callout-title">${info.title}</span></div>\n`;

            const pOpenIdx = firstInlineIdx - 1;
            tokens.splice(pOpenIdx, 0, headerBlock);
            i++;

            inlineToken.content = bodyText;
            if (!bodyText) {
              tokens.splice(pOpenIdx + 1, 3);
            } else {
              inlineToken.children = [new state.Token('html_inline', '', 0)];
              inlineToken.children[0].content = md.renderInline(bodyText);
            }
          }
        }
      }
    }

    // F. If in Slide Deck mode, group tokens into presentation slide cards
    if (docMode === 'slide') {
      groupTokensIntoSlides(state, docTitle);
    }

    // G. If in Poster mode, append poster footer if defined
    if (docMode === 'poster' && frontMeta && frontMeta.footer) {
      const footer = frontMeta.footer;
      let footerHtml = '<footer class="pydoc-poster-footer">\n';
      footerHtml += `  <div class="pydoc-poster-footer-left">${escapeHtml(footer.left || '')}</div>\n`;
      footerHtml += `  <div class="pydoc-poster-footer-right">${escapeHtml(footer.right || '')}</div>\n`;
      if (footer.qr || footer['qr-label']) {
        footerHtml += `  <div class="pydoc-poster-qr-badge">📱 ${escapeHtml(footer['qr-label'] || 'QR Code')}</div>\n`;
      }
      footerHtml += '</footer>\n';

      const footToken = new state.Token('html_block', '', 0);
      footToken.content = footerHtml;
      tokens.push(footToken);
    }
  });
}

function groupTokensIntoSlides(state, docTitle) {
  const tokens = state.tokens;
  const newTokens = [];
  let currentSlideTokens = [];
  let slideNum = 0;
  let isCurrentSection = false;

  function flushSlide(isSection) {
    if (currentSlideTokens.length === 0) return;
    slideNum++;
    const cardOpen = new state.Token('html_block', '', 0);
    const slideClass = isSection ? 'pydoc-slide pydoc-slide-section' : 'pydoc-slide pydoc-slide-content';
    cardOpen.content = `<section class="${slideClass}"><div class="pydoc-slide-canvas">\n`;
    newTokens.push(cardOpen);

    for (const t of currentSlideTokens) {
      newTokens.push(t);
    }

    const cardClose = new state.Token('html_block', '', 0);
    cardClose.content = `</div><footer class="pydoc-slide-footer"><span class="pydoc-slide-deck-title">${escapeHtml(docTitle)}</span><span class="pydoc-slide-num">Slide ${slideNum}</span></footer></section>\n`;
    newTokens.push(cardClose);
    currentSlideTokens = [];
  }

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    if (token.type === 'pydoc_front_matter') {
      newTokens.push(token);
      continue;
    }

    if (token.type === 'heading_open') {
      const level = parseInt(token.tag.slice(1), 10);
      if (level <= 2) {
        flushSlide(isCurrentSection);
        isCurrentSection = (level === 1);
      }
    }

    if (token.type === 'html_block' && token.content && token.content.includes('pydoc-pagebreak')) {
      flushSlide(isCurrentSection);
      isCurrentSection = false;
      continue;
    }

    currentSlideTokens.push(token);
  }

  flushSlide(isCurrentSection);
  state.tokens = newTokens;
}

function activate(context) {}
function deactivate() {}

function extendMarkdownIt(md) {
  return md.use(pyDocPlugin);
}

module.exports = {
  activate,
  deactivate,
  extendMarkdownIt,
  pyDocPlugin,
  parseSimpleYaml
};
