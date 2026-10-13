---
title: Sites, imports and scaffolding
---

# Sites, imports and scaffolding

## Web sites

The site package keeps what all site generators share in `site/pages.py`, and what differs in `site/engines.py`. There is one class per engine (`MkDocs`, `Starlight`), each with the same five parts: where pages go, the scaffold, the navigation, the check of the site's configuration, and the build command.

1. **Pages**: for each document, the C4 sources are expanded and the sources joined as for a build, but with page breaks and heading offsets left out. Each source becomes one page, with its diagrams drawn as SVG.
1. **Conversion**: every page goes through pandoc with `site.lua` in a single container run (a generated shell script), writing GitHub-flavoured Markdown with dollar maths.
1. **Links and pictures**: links to other source files are pointed at the pages made from them (relative `.md` paths for MkDocs, site URLs for Starlight). Pictures are copied beside the page.
1. **Writing**: the pages, their pictures and a `.gitignore` per document folder are written into the site's content folder. A manifest (`.py-doc-site.json`) lists them, so the next run removes pages whose sources are gone and refuses to replace a file it did not write.
1. **Navigation**: written into a file py-doc owns (`py-doc-nav.yml`, or `src/py-doc-sidebar.json`), which the site's configuration takes in. The site's configuration is never edited.
1. **Build**: MkDocs runs from the tool image. Astro runs `npm install` with the network, then `astro build`, in the container.

## Imports

`docx_import.py` walks the Word body in order: paragraphs, tables and content controls. It keeps tracked insertions, drops deletions, and renders blocks to Markdown. `pptx_import.py` walks each slide's shapes in reading order, including those pandoc wraps in `mc:AlternateContent`. It writes the conventions the slides converter reads, so a deck makes a round trip to the same slides.

Both importers share picture conversion (Pillow for bitmaps, Inkscape in the container for EMF, WMF and SVG), escaping and the reading of document properties. Both count what they cannot carry over.

## Project scaffolding

`init.py` builds the new `py-doc.yml` from a commented template and the choices made. It loads the result with the configuration parser before writing anything, so a project that would not load is never written. Files are written only where none exists. Templates come from pandoc in the container, and when the container is not available the step is skipped with a warning. A site is scaffolded by the site engine, the same code `py-doc site init` uses.
