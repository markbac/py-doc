'use strict';

const yaml = require('js-yaml');

// The core schema reads dates as text, as written, where the default one would make Date objects
function parseFrontMatter(text) {
  try {
    const data = yaml.load(text, { schema: yaml.CORE_SCHEMA });
    return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
  } catch (e) {
    return {};  // the build reports a front matter that is not valid YAML; the preview shows the body
  }
}

// The front matter between --- lines at the top of a file, and the text after it
function splitFrontMatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/);
  return m ? { meta: parseFrontMatter(m[1]), body: text.slice(m[0].length) } : { meta: {}, body: text };
}

module.exports = { parseFrontMatter, splitFrontMatter };
