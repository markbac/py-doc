"""Render a railroad (syntax) diagram to SVG. Runs inside the tool container: railroad_render.py SOURCE OUTPUT.

The source is either a ``Diagram(...)`` expression of the railroad-diagrams library, or an indented list:

    Sequence
      Terminal "SELECT"
      Optional
        Terminal "*"
      NonTerminal table_name

The expression form is evaluated, so it can run any Python. That is safe only because this script runs in
the tool container, which has no network and cannot write outside its work folder.
"""

import io
import shlex
import sys

import railroad
from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
ALIASES = {
    "terminal": "Terminal", "nonterminal": "NonTerminal", "comment": "Comment", "skip": "Skip",
    "sequence": "Sequence", "choice": "Choice", "optional": "Optional", "oneormore": "OneOrMore",
    "zeroormore": "ZeroOrMore", "group": "Group", "diagram": "Diagram", "stack": "Stack",
    "horizontalchoice": "HorizontalChoice", "multiplechoice": "MultipleChoice",
    "optionalsequence": "OptionalSequence", "alternatingsequence": "AlternatingSequence",
}  # fmt: skip


def parse(lines):
    stack = [(-1, [])]
    for raw in lines:
        stripped = raw.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip())
        parts = stripped.split()
        kind = ALIASES.get(parts[0].lower(), parts[0])
        try:
            words = shlex.split(" ".join(parts[1:]))
        except ValueError:
            words = parts[1:]
        node = (kind, [w.rstrip(",") for w in words if w.rstrip(",")], [])
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        stack[-1][1].append(node)
        stack.append((indent, node[2]))
    return stack[0][1]


def build(node):
    kind, args, children = node
    cls = getattr(railroad, kind, None)
    if cls is None:
        raise ValueError(f"Unknown railroad node: {kind!r}")
    if kind in ("Choice", "MultipleChoice"):
        # The library takes the index of the default branch first: `Choice 1` names it, plain `Choice` is the first
        default = int(args[0]) if args and args[0].isdigit() else 0
        args = [default, *(args[1:] if args and args[0].isdigit() else args)]
        if kind == "MultipleChoice" and len(args) < 2:
            args.append("any")
    return cls(*args, *[build(child) for child in children])


def inline_styles(svg_text):
    """Replace the stylesheet by attributes, so the picture looks the same wherever it is embedded."""
    root = etree.fromstring(svg_text.encode("utf-8"))
    for style in list(root.iter(f"{{{SVG_NS}}}style")) + list(root.iter("style")):
        style.getparent().remove(style)
    box = [p for p in root.get("viewBox", "").replace(",", " ").split()]
    width, height = (box[2], box[3]) if len(box) >= 4 else (root.get("width", "100%"), root.get("height", "100%"))
    background = etree.Element(f"{{{SVG_NS}}}rect", x="0", y="0", width=width, height=height, fill="hsl(30,20%,95%)")
    root.insert(0, background)

    def default(element, name, value):
        if element.get(name) is None:
            element.set(name, value)

    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        tag = element.tag.split("}")[-1]
        cls = element.get("class", "")
        if tag == "path":
            default(element, "fill", "none")
            default(element, "stroke", "black")
            default(element, "stroke-width", "3")
        elif tag == "rect" and element is not background:
            if "group-box" in cls:
                default(element, "fill", "none")
                default(element, "stroke", "gray")
                default(element, "stroke-dasharray", "10 5")
            else:
                default(element, "fill", "hsl(120,100%,90%)")
                default(element, "stroke", "black")
            default(element, "stroke-width", "3")
        elif tag == "text":
            default(element, "font-family", "monospace")
            if "comment" in cls:
                default(element, "font-size", "12")
                default(element, "font-style", "italic")
            else:
                default(element, "font-size", "14")
                default(element, "font-weight", "bold")
            default(element, "text-anchor", "start" if "label" in cls else "middle")
    return etree.tostring(root, encoding="unicode")


source, output = sys.argv[1:3]
with open(source, encoding="utf-8") as handle:
    code = handle.read().strip()
if code.startswith("Diagram("):
    diagram = eval(code, vars(railroad))  # noqa: S307
else:
    top = [build(node) for node in parse(code.splitlines())]
    if not top:
        sys.exit("railroad: the diagram is empty")
    diagram = top[0] if len(top) == 1 and isinstance(top[0], railroad.Diagram) else railroad.Diagram(*top)
buffer = io.StringIO()
diagram.writeStandalone(buffer.write)
with open(output, "w", encoding="utf-8") as handle:
    handle.write(inline_styles(buffer.getvalue()))
