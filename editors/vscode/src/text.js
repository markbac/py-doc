'use strict';

// Front matter values may be lists (author: [- Jane, - Joe]) or mappings, so anything is turned into text first
function asText(val) {
  if (val === null || val === undefined) return '';
  if (Array.isArray(val)) return val.map(asText).join(', ');
  if (typeof val === 'object') return Object.values(val).map(asText).join(', ');
  return String(val);
}

module.exports = { asText };
