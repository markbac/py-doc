'use strict';

// Front matter values may be lists (author: [- Jane, - Joe]) or mappings, so anything is turned into text first
function asText(val) {
  if (val === null || val === undefined) return '';
  if (Array.isArray(val)) return val.map(asText).join(', ');
  if (typeof val === 'object') return Object.values(val).map(asText).join(', ');
  return String(val);
}

// A colour name written in the Markdown, made safe to use as part of a class name
function cssName(val) {
  return asText(val).toLowerCase().replace(/[^a-z0-9_-]/g, '');
}

function escapeHtml(val) {
  const str = asText(val);
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
}

module.exports = { asText, cssName, escapeHtml };
