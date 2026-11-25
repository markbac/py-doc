"""Write src/py_doc/web/static/diagram-modes.js from the VS Code extension's grammars.

The web editor colours py-doc's diagram fences (Mermaid, PlantUML, Graphviz and its family, poster blocks,
BPMN text, arch-text) as the VS Code extension does. Rather than keep two sets of patterns by hand, this script reads
the TextMate grammars in editors/vscode/syntaxes and writes them out as rules for a small CodeMirror
tokenizer, with the table of which fence is written in which language. tests/test_web.py fails when the
file is not what this script writes, so run it after changing a grammar:

    python scripts/web_editor_modes.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNTAXES = ROOT / "editors" / "vscode" / "syntaxes"
OUTPUT = ROOT / "src" / "py_doc" / "web" / "static" / "diagram-modes.js"

# The grammars of the languages py-doc draws, and the CodeMirror mode each becomes
LANGUAGES = {
    "pydoc-mermaid": "mermaid.tmLanguage.json",
    "pydoc-plantuml": "plantuml.tmLanguage.json",
    "pydoc-dot": "dot.tmLanguage.json",
    "pydoc-block": "block.tmLanguage.json",
    "pydoc-bpmnt": "bpmnt.tmLanguage.json",
    "pydoc-archt": "archt.tmLanguage.json",
}
# Fences with a grammar of their own, <fence>.markdown.tmLanguage.json, highlighted with mode pydoc-<fence>
OWN_GRAMMARS = ("bpmnt", "archt")
# A fence group of pydoc-fences.markdown.tmLanguage.json, and the mode its fences are highlighted with
GROUPS = {
    "dot": "pydoc-dot",
    "mermaid": "pydoc-mermaid",
    "plantuml": "pydoc-plantuml",
    "json": "application/json",
    "javascript": "javascript",
    "yaml": "yaml",
    "clojure": "clojure",
    "block": "pydoc-block",
    "plain": "text/plain",
}
# A TextMate scope, by its first parts, and the CodeMirror style it is shown with. The first that fits wins.
STYLES = [
    ("comment", "comment"),
    ("string", "string"),
    ("keyword.operator", "operator"),
    ("keyword", "keyword"),
    ("storage", "def"),
    ("constant.numeric", "number"),
    ("constant.character", "string-2"),
    ("constant", "atom"),
    ("entity.name.tag", "tag"),
    ("entity.name", "def"),
    ("entity.other.attribute-name", "attribute"),
    ("support", "builtin"),
    ("variable", "variable-2"),
    ("meta", "meta"),
    ("punctuation", "bracket"),
]


def style_of(scope: str | None) -> str | None:
    if not scope:
        return None
    first = scope.split()[0]
    for prefix, style in STYLES:
        if first == prefix or first.startswith(prefix + "."):
            return style
    return None


def js_regex(pattern: str) -> tuple[str, str]:
    """An Oniguruma pattern as a JavaScript one, and its flags. Only what these grammars use is handled."""
    flags = ""
    if pattern.startswith("(?i)"):
        pattern, flags = pattern[4:], "i"
    if "(?i" in pattern or "\\G" in pattern or "\\A" in pattern or "\\h" in pattern:
        raise ValueError(f"a pattern this script cannot translate: {pattern}")
    re.compile(pattern)  # the grammars' patterns are also valid Python ones; JavaScript reads them the same
    return pattern, flags


def rule_style(rule: dict) -> str | None:
    """The style of a rule: its own name, else that of its first named capture."""
    if rule.get("name"):
        return style_of(rule["name"])
    for key in ("captures", "beginCaptures"):
        for _, capture in sorted(rule.get(key, {}).items(), key=lambda item: int(item[0])):
            if capture.get("name"):
                return style_of(capture["name"])
    return None


def flatten(patterns: list, repository: dict, seen: set[str] | None = None) -> list[dict]:
    """The rules of ``patterns`` in order, with every #include from the repository put in its place."""
    seen = seen or set()
    rules: list[dict] = []
    for item in patterns:
        if "include" in item:
            name = item["include"].lstrip("#")
            if item["include"].startswith("#") and name not in seen and name in repository:
                target = repository[name]
                inner = target.get("patterns") if "match" not in target and "begin" not in target else [target]
                rules += flatten(inner or [], repository, seen | {name})
            continue
        if "match" in item:
            source, flags = js_regex(item["match"])
            rule = {"match": source, "flags": flags, "style": style_of(item.get("name")) or rule_style(item)}
            if item.get("captures"):  # each group its own style: name, =, value
                count = max(int(key) for key in item["captures"])
                rule["captures"] = [None] + [
                    style_of(item["captures"].get(str(index), {}).get("name")) for index in range(1, count + 1)
                ]
            rules.append(rule)
        elif "begin" in item and "end" in item:
            begin, begin_flags = js_regex(item["begin"])
            end, end_flags = js_regex(item["end"])
            style = rule_style(item) or style_of(item.get("contentName"))
            rules.append({"begin": begin, "end": end, "flags": begin_flags or end_flags, "style": style})
        elif "patterns" in item:
            rules += flatten(item["patterns"], repository, seen)
    return rules


def fence_names() -> dict[str, str]:
    """Every fence name py-doc draws, and the mode to highlight it with."""
    names: dict[str, str] = {}
    grammar = json.loads((SYNTAXES / "pydoc-fences.markdown.tmLanguage.json").read_text(encoding="utf-8"))
    sources = [
        (key.removesuffix("-fence"), rule) for key, rule in grammar["repository"].items() if key.endswith("-fence")
    ]
    for fence in OWN_GRAMMARS:
        own = json.loads((SYNTAXES / f"{fence}.markdown.tmLanguage.json").read_text(encoding="utf-8"))
        sources += [(fence, rule) for rule in own["repository"].values()]
    for group, rule in sources:
        found = re.search(r"\(\?i:\(([^)]*)\)", rule["begin"])
        if not found:
            raise ValueError(f"no fence names in {group}")
        mode = f"pydoc-{group}" if group in OWN_GRAMMARS else GROUPS[group]
        for name in found.group(1).split("|"):
            names[name.replace("\\", "")] = mode
    return dict(sorted(names.items()))


def render() -> str:
    modes = {}
    for mode, file in LANGUAGES.items():
        grammar = json.loads((SYNTAXES / file).read_text(encoding="utf-8"))
        modes[mode] = flatten(grammar.get("patterns", []), grammar.get("repository", {}))
    data = json.dumps({"modes": modes, "fences": fence_names()}, indent=1, ensure_ascii=False)
    return HEAD + "const DATA = " + data + ";\n" + TAIL


HEAD = """/* GENERATED by scripts/web_editor_modes.py from editors/vscode/syntaxes: do not edit by hand.
 *
 * CodeMirror modes for the languages py-doc draws, so a fenced diagram in the web editor is coloured as in
 * VS Code, and the table of which fence is written in which language (vega is JSON, wavedrom JavaScript).
 */
(function () {
  "use strict";
  if (!window.CodeMirror) return;
"""

TAIL = """
  // A small tokenizer for the rules: single-line matches, and begin ... end spans that may cross lines.
  // Patterns are run with the sticky flag against the whole line, so look-behinds see what came before.
  function compile(rules) {
    return rules.map((rule) => rule.match
      ? { match: new RegExp(rule.match, rule.flags + (rule.captures ? "yd" : "y")), style: rule.style, captures: rule.captures }
      : { begin: new RegExp(rule.begin, rule.flags + "y"), end: new RegExp(rule.end, rule.flags + "g"), style: rule.style });
  }
  // A match cut into parts at its styled groups, each [end, style]; what is between them has the rule's style
  function split(found, rule) {
    const parts = [];
    let at = found.index;
    const end = found.index + found[0].length;
    for (let group = 1; group < found.indices.length; group++) {
      const span = found.indices[group];
      const style = rule.captures[group];
      if (!span || !style || span[0] < at || span[1] <= span[0]) continue;
      if (span[0] > at) parts.push([span[0], rule.style]);
      parts.push([span[1], style]);
      at = span[1];
    }
    if (at < end) parts.push([end, rule.style]);
    return parts;
  }
  function ruleMode(rules) {
    const compiled = compile(rules);
    return {
      startState: () => ({ open: null, parts: [] }),
      copyState: (state) => ({ open: state.open, parts: state.parts.slice() }),
      token(stream, state) {
        if (state.parts.length) {  // the rest of a match whose groups have styles of their own
          const [end, style] = state.parts.shift();
          stream.pos = end;
          return style;
        }
        if (state.open) {
          const end = state.open.end;
          end.lastIndex = stream.pos;
          const found = end.exec(stream.string);
          const style = state.open.style;
          if (found) { stream.pos = Math.max(found.index + found[0].length, Math.min(stream.pos + 1, stream.string.length)); state.open = null; }
          else stream.skipToEnd();
          return style;
        }
        for (const rule of compiled) {
          const pattern = rule.match || rule.begin;
          pattern.lastIndex = stream.pos;
          const found = pattern.exec(stream.string);
          if (!found || found[0].length === 0) continue;
          if (rule.captures && found.indices) {
            state.parts = split(found, rule);
            return this.token(stream, state);
          }
          stream.pos += found[0].length;
          if (rule.begin) { state.open = rule; return this.token(stream, state) || rule.style; }
          return rule.style;
        }
        stream.next();
        return null;
      },
      lineComment: "#",
    };
  }

  for (const [name, rules] of Object.entries(DATA.modes)) CodeMirror.defineMode(name, () => ruleMode(rules));
  // Each fence name as a mode of its own, which Markdown's fenced code highlighting asks for by name.
  // A name CodeMirror already has (such as yaml) keeps its own.
  for (const [fence, mode] of Object.entries(DATA.fences)) {
    if (!CodeMirror.modes[fence]) CodeMirror.defineMode(fence, (config) => CodeMirror.getMode(config, mode));
  }
  window.PYDOC_FENCES = DATA.fences;
})();
"""


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        if OUTPUT.read_text(encoding="utf-8") != text:
            print(f"{OUTPUT.relative_to(ROOT)} is out of date: run python scripts/web_editor_modes.py", file=sys.stderr)
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(LANGUAGES)} languages, {len(fence_names())} fence names")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
