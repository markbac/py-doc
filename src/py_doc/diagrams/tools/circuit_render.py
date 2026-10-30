"""Draw a circuit with schemdraw, from the JSON py-doc wrote from a ``circuit`` fence (see diagrams/declarative.py).

    python3 circuit_render.py <circuit.json> <circuit.svg>

Each element continues from the end of the one before. ``at`` and ``to`` name an anchor of an element drawn
earlier. A mistake (an anchor an element does not have) stops with a message naming the line of the fence.
"""

import json
import sys

import schemdraw
import schemdraw.elements as elm
import schemdraw.logic as logic


def main(source, output):
    with open(source, encoding="utf-8") as f:
        spec = json.load(f)
    schemdraw.use("svg")
    named = {}
    drawing = schemdraw.Drawing(show=False)
    drawing.config(unit=3, fontsize=13, font="sans-serif")
    for item in spec["elements"]:
        line = item["line"]
        # the gates are in schemdraw.logic, the rest in schemdraw.elements
        element = (getattr(elm, item["element"], None) or getattr(logic, item["element"]))()

        def anchor(ref):
            target = named[ref[0]]
            if not hasattr(target, ref[1]) and ref[1] not in getattr(target, "anchors", {}):
                sys.exit(f"line {line}: {ref[0]} has no anchor '{ref[1]}' (it has start, end, center and its own)")
            return getattr(target, ref[1])

        if "at" in item:
            element = element.at(anchor(item["at"]))
        if "direction" in item:
            element = getattr(element, item["direction"])()
        if "length" in item:
            element = element.length(drawing.unit * item["length"])
        if "to" in item:
            element = element.to(anchor(item["to"]))
        if item.get("flip"):
            element = element.flip()
        if item["label"]:
            element = element.label(item["label"])
        drawing.add(element)
        if "name" in item:
            named[item["name"]] = element
    drawing.save(output)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
