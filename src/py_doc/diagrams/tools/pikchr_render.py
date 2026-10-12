"""Render a Pikchr diagram to SVG. Runs inside the tool container: pikchr_render.py SOURCE OUTPUT."""

import sys

from pypikchr.util.pikchr import create_pikchr

source, output = sys.argv[1:3]
with open(source, encoding="utf-8") as handle:
    text = handle.read()
svg = create_pikchr(text, "", 0, 0, 0)
if "<svg" not in svg:
    # Pikchr reports a syntax error as text or as an error block, never as a picture
    sys.exit("pikchr: " + svg.strip()[:2000])
with open(output, "w", encoding="utf-8") as handle:
    handle.write(svg)
