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
  downloads: [pdf, docx]      # link these built files from each document's pages (default: none)
  targets:                    # MkDocs only: more than one site from the same pages (default: one site)
    github: mkdocs.yml
    tarf: mkdocs.tarf.yml
  pages:                      # pages of your own, added to the navigation after the documents
    Blog: blog/index.md
```

```bash
py-doc site init        # make the site project once, if it is not there
py-doc site generate    # write the pages and the navigation
py-doc site build       # write them, then build the site in the tool container
py-doc site build --var version=2.0 --condition internal=true
py-doc site build --target tarf   # one site of site.targets (default: every one)
```

## The site project

`py-doc site init` makes a new site, and leaves an existing one as it is: a file that is there is never replaced.

| Engine | Files `init` writes | The site is built into |
|---|---|---|
| `mkdocs` | `mkdocs.yml` (Material theme, admonitions, task lists, maths), `docs/index.md`, `.gitignore` | `site/build` |
| `starlight` | `package.json`, `astro.config.mjs`, `src/content.config.ts`, `src/content/docs/index.md`, `src/py-doc-sidebar.json`, `tsconfig.json`, `.gitignore` | `site/dist` |

The configuration is yours to change: theme, colours, logo, plugins, extra pages. py-doc never edits it. It writes the navigation into a file of its own, which the configuration takes in:

- **MkDocs**: `py-doc-nav.yml`, with a section per document and a page per source file, nested by folder. `mkdocs.yml` takes it in with `INHERIT: py-doc-nav.yml`. A `nav:` written in `mkdocs.yml` itself wins, so a hand-made navigation is kept. `py-doc site generate` says what is missing when `mkdocs.yml` neither inherits nor has a `nav`.
- **Starlight**: `src/py-doc-sidebar.json`, a group per document. A document with all its pages in one folder lists that folder. A document with subfolders lists its pages, in groups by folder. `astro.config.mjs` passes it to Starlight as `sidebar`, and each page carries its place in the front matter (`sidebar.order`).

An existing site works the same way: point `site.dir` at it and add the `INHERIT` line or the sidebar import.

Pages you write yourself, such as an about page or a blog, go in the content folder beside py-doc's document folders, and py-doc leaves them alone. `site.pages` adds them to the navigation py-doc writes, after the documents, as title and path below the content folder. `py-doc site generate` warns when a listed page is not there.

## The pages

Each source file of each document becomes one page, in a folder named after the document: `docs/guide/01-overview.md` for MkDocs, `src/content/docs/guide/01-overview.md` for Starlight. The pages go through the same steps as every other output, then through pandoc with the `site.lua` filter.

A page keeps the place of its source below the folder that holds all of the document's sources. Names are made lower case, with `-` in place of other characters. For these sources:

```yaml
documents:
  primers:
    sources:
      - content/primers/index.md
      - content/primers/cloud/index.md
      - content/primers/cloud/kafka.md
      - content/primers/architecture/c4.md
```

the pages are `docs/primers/index.md`, `docs/primers/cloud/index.md`, `docs/primers/cloud/kafka.md` and `docs/primers/architecture/c4.md`. The navigation nests the same way, in the order of `sources`. Each folder is a group:

- **Landing page**: the folder's `index.md`, when it is listed, comes first in its group wherever it is in `sources`. With the Material feature `navigation.indexes`, which `py-doc site init` turns on, the group's title opens that page.
- **Group title**: the index page's title. A folder without one is named after the folder, so `iot-and-embedded` becomes "Iot and embedded".
- **Flat documents**: a document whose sources are all in one folder gives flat pages, as before.

`site_path` on a source puts its page somewhere else on the site without moving the file. It is the path below the document's folder, without `.md`:

```yaml
      - {file: content/primers/c4.md, site_path: architecture/c4}
```

Two sources that would give the same page, such as `Kafka.md` and `kafka.md` in one folder, stop the run with both named. Rename one, or give one a `site_path`. Generated C4 chapters go at the top of the document's folder.

Word, PowerPoint and PDF ignore the folders and `site_path`. `heading_offset` and `page_break` still set how the sources nest there.

- **Includes, conditions and variables** are expanded, and C4 chapters are generated from `structurizr:` sources.
- **Diagrams** are drawn as SVG where the tool can, and copied beside the page. Pictures the Markdown shows are copied into a `media/` folder beside the page.
- **Callouts** become MkDocs admonitions (`!!! note`) or Starlight asides (`:::note`).
- **Captions** become an italic line under the picture or table.
- **Links between source files** point at the pages made from them, anchors included, across folders too.
- **Titles**: the first heading is the page title. Starlight shows the title itself, so the heading is not repeated there.
- **Page breaks and heading offsets** mean nothing on a site and are left out.

The pages are built from the sources, so py-doc puts a `.gitignore` in each document folder and they stay out of Git. A manifest, `.py-doc-site.json`, lists what py-doc wrote. A page whose source is gone is removed. A file py-doc did not write is never replaced: the build stops and names it.

## Downloads

`site.downloads` lists the formats whose built files each document's pages link: `pdf`, `docx`, `pptx` or `html`. A document links only the formats it builds (its `outputs`), and only once `py-doc build` has made them, so run that first. py-doc copies each file beside the site and puts a line such as "Download: PDF · Word" under the first heading of the document's first page. A file that is not built yet is left out with a warning that names the `py-doc build` command to run. With MkDocs the files go in a `downloads/` folder beside the document's pages. With Starlight they go in `public/<document>/downloads/`, which Starlight serves from the site root.

## More than one site

`site.targets` builds several MkDocs sites from one site project, for example the same documents at two addresses with different home pages. Each target names a MkDocs config file in `site.dir`. The pages and the navigation are written once and shared, so each config file takes in `mkdocs.yml` (or `py-doc-nav.yml`) with `INHERIT` and changes only what differs:

```yaml
# site/mkdocs.tarf.yml
INHERIT: mkdocs.yml
site_url: https://tarf.co.uk/
site_dir: build-tarf
theme:
  name: material
  custom_dir: overrides-tarf   # its own home page template
```

Each target needs its own `site_dir`, and all of them read the pages from the `docs_dir` of `mkdocs.yml`. `py-doc site build` stops before building when two targets share a folder, and `py-doc site generate` says when a target's file is missing or does not take in the navigation. `py-doc site build` builds every target in order. `--target NAME` builds only that one, and can be given more than once.

## Building

`py-doc site build` runs the site's tool in the tool container, so neither MkDocs nor Node.js has to be installed:

- **MkDocs**: `mkdocs build` with MkDocs Material and `mkdocs-redirects` (for moved pages), which are in the tool image. Material's own blog plugin works too: posts are files of your own in the site's `docs` folder, so py-doc leaves them alone.
- **Starlight**: `npm install` (with the network, the only site step that downloads anything), then `astro build` with telemetry off. `package-lock.json` is used and kept up to date.

To work on the site with live reload, install the site's own tool and run `mkdocs serve` in `site/`, or `npm run dev`, after `py-doc site generate`.
