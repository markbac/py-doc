---
title: Web sites
---

# Web sites with MkDocs or Astro + Starlight

`py-doc site` publishes the documents of a project as a web site. The same Markdown sources build the Word, PowerPoint and PDF files and the site. py-doc writes the pages and the navigation, and the site's own tool builds the site: [MkDocs](https://www.mkdocs.org) with the Material theme, or [Astro](https://astro.build) with [Starlight](https://starlight.astro.build).

```yaml
site:
  engine: mkdocs              # or starlight
  dir: site                   # the site project (default: site)
  title: Sensor documentation # default: project.name
  documents: [guide, architecture]   # default: every document, in the order of py-doc.yml
```

```bash
py-doc site init        # make the site project once, if it is not there
py-doc site generate    # write the pages and the navigation
py-doc site build       # write them, then build the site in the tool container
py-doc site build --var version=2.0 --condition internal=true
```

## The site project

`py-doc site init` makes a new site, and leaves an existing one as it is: a file that is there is never replaced.

| Engine | Files `init` writes | The site is built into |
|---|---|---|
| `mkdocs` | `mkdocs.yml` (Material theme, admonitions, task lists, maths), `docs/index.md`, `.gitignore` | `site/build` |
| `starlight` | `package.json`, `astro.config.mjs`, `src/content.config.ts`, `src/content/docs/index.md`, `src/py-doc-sidebar.json`, `tsconfig.json`, `.gitignore` | `site/dist` |

The configuration is yours to change: theme, colours, logo, plugins, extra pages. py-doc never edits it. It writes the navigation into a file of its own, which the configuration takes in:

- **MkDocs**: `py-doc-nav.yml`, with a section per document and a page per source file. `mkdocs.yml` takes it in with `INHERIT: py-doc-nav.yml`. A `nav:` written in `mkdocs.yml` itself wins, so a hand-made navigation is kept. `py-doc site generate` says what is missing when `mkdocs.yml` neither inherits nor has a `nav`.
- **Starlight**: `src/py-doc-sidebar.json`, a group per document that lists the document's folder. `astro.config.mjs` passes it to Starlight as `sidebar`, and each page carries its place in the front matter (`sidebar.order`).

An existing site works the same way: point `site.dir` at it and add the `INHERIT` line or the sidebar import.

## The pages

Each source file of each document becomes one page, in a folder named after the document: `docs/guide/01-overview.md` for MkDocs, `src/content/docs/guide/01-overview.md` for Starlight. The pages go through the same steps as every other output, then through pandoc with the `site.lua` filter.

- **Includes, conditions and variables** are expanded, and C4 chapters are generated from `structurizr:` sources.
- **Diagrams** are drawn as SVG where the tool can, and copied beside the page. Pictures the Markdown shows are copied into `media/`.
- **Callouts** become MkDocs admonitions (`!!! note`) or Starlight asides (`:::note`).
- **Captions** become an italic line under the picture or table.
- **Links between source files** point at the pages made from them, anchors included.
- **Titles**: the first heading is the page title. Starlight shows the title itself, so the heading is not repeated there.
- **Page breaks and heading offsets** mean nothing on a site and are left out.

The pages are built from the sources, so py-doc puts a `.gitignore` in each document folder and they stay out of Git. A manifest, `.py-doc-site.json`, lists what py-doc wrote. A page whose source is gone is removed. A file py-doc did not write is never replaced: the build stops and names it.

## Building

`py-doc site build` runs the site's tool in the tool container, so neither MkDocs nor Node.js has to be installed:

- **MkDocs**: `mkdocs build` with MkDocs Material, which is in the tool image.
- **Starlight**: `npm install` (with the network, the only site step that downloads anything), then `astro build` with telemetry off. `package-lock.json` is used and kept up to date.

To work on the site with live reload, install the site's own tool and run `mkdocs serve` in `site/`, or `npm run dev`, after `py-doc site generate`.
