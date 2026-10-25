'use strict';

const { asText } = require('./text');
const { splitFrontMatter } = require('./frontmatter');

// Front matter keys only a poster has (see py_doc/poster_settings.py)
const POSTER_KEYS = ['paper', 'byline', 'orientation', 'theme', 'columns', 'width', 'colours', 'palette', 'embed_fonts', 'logo'];
const SLIDE_DIVS = /^:{3,4}\s*\{?\.?(columns|column|notes|incremental)\}?\s*$/;

/**
 * Which py-doc command a Markdown file is for: 'poster', 'slides' or 'docx'.
 * Decided from the front matter, then from blocks only a deck has (columns, speaker notes, incremental lists).
 * The live preview runs this command when the file does not name one.
 */
function detectFormat(meta, body) {
  meta = meta || {};
  const fmt = asText(meta.format || meta.output || meta.type || meta.layout).toLowerCase();
  if (fmt.includes('pptx') || fmt.includes('slide') || meta.split_level) return 'slides';
  if (fmt.includes('poster') || POSTER_KEYS.some((k) => meta[k] !== undefined && meta[k] !== '')) return 'poster';

  let fence = null;
  for (const line of (body || '').split(/\r?\n/)) {
    const trimmed = line.trim();
    const fenceMatch = trimmed.match(/^(`{3,}|~{3,})/);
    if (fenceMatch) {
      if (!fence) fence = fenceMatch[1][0];
      else if (trimmed[0] === fence) fence = null;
      continue;
    }
    if (fence) continue;
    if (SLIDE_DIVS.test(trimmed) || /^<!--\s*notes:/i.test(trimmed)) return 'slides';
  }
  return 'docx';
}


function detectDocumentFormat(document) {
  const text = document && typeof document.getText === 'function' ? document.getText() : String(document);
  const { meta, body } = splitFrontMatter(text);
  return detectFormat(meta, body);
}

module.exports = { detectFormat, detectDocumentFormat, POSTER_KEYS };
