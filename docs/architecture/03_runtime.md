---
title: The tool runtime
---

# The tool runtime

## The tool image

The files in `src/py_doc/runtime/definition` define the image:

| File | Holds |
|---|---|
| `Dockerfile` | The image, on Debian 12 |
| `requirements.txt` | The Python diagram tools and MkDocs |
| `package.json` | Mermaid, markdownlint, WaveDrom, bytefield-svg, Vega and Puppeteer, and for API documentation Redocly CLI, Widdershins, the AsyncAPI generator and its Markdown and HTML templates |
| `asyncapi-docs.js` | Runs the AsyncAPI generator with the installed templates, so it needs no network |
| `tools.lock` | Downloads with their SHA-256: pandoc, PlantUML, ditaa, Vale, `structurizr-cli` and Node.js |
| `fetch.sh` | Downloads one of them and checks it |
| `export-diagrams.js` | Draws Structurizr views in Chromium |

`requirements.txt` also has schemdraw and python-chess, and `package.json` abcjs, for the `circuit`, `chess` and `music` fences.

The tag is a hash of the folder (`runtime/image.py`). A change to any of these files builds a new image, and a release that changes none of them reuses the old one. Node.js comes from nodejs.org rather than Debian, whose version is too old for the current Vega, markdownlint and Astro packages. The AsyncAPI generator needs Node.js 24.

## The science image

`src/py_doc/runtime/science` defines a second, optional image, `py-doc-science`: the tool image (its `Dockerfile` starts `FROM` the tool image's tag) with the scientific Python libraries of its `requirements.txt`, such as RDKit, matplotlib, CoolProp and pvlib. Its tag is a hash of its folder and of the tool image's definition (`image.science_ref()`). A renderer with `image="science"` runs in it: `diagrams/render.py` asks `image.ensure_science()` for its tag, which builds it when it is not there, and passes it to `Runtime.run(image=...)`. The diagram cache keys such a picture by the science image's tag. `py-doc tools build --science` builds it ahead of time.

It is a second image, not part of the first. A project that draws none of these fences never downloads their few hundred MB of libraries.

## Running a tool

`runtime/engine.py` starts every program in a fresh container:

- as the calling user (`--user uid:gid`), so files it writes belong to the user;
- with `--cap-drop ALL`, `no-new-privileges` and no network unless the step asks (the Astro site build and Vale package downloads do);
- with only the folders the step needs mounted, read-only unless the step writes there, at the same path inside the container, so error messages name real paths;
- with a shared volume for caches that live inside the container (fonts, TeX, Chromium profiles, npm).

Arguments are a list, never a shell string. A path in the arguments must lie under a mount, so a tool cannot be pointed at a file it was not given. A tool that fails raises an error with its whole output. A timeout kills the container.

## Windows and WSL

On Windows, Docker Engine runs in a WSL 2 distribution, and every engine command goes through `wsl.exe -d <distro> --exec`. Paths are translated with `wslpath`. WSL stops a distribution soon after its last `wsl.exe` exits, and Docker and its containers with it. Short steps are not affected, because each runs through `wsl.exe` until it ends. A container that must outlive the command that started it, such as Structurizr Local for `py-doc c4 up`, is kept alive by `Runtime.keep_alive()`: a `sleep` in the distro that ends when Local stops. A detached Local records that process in `.py-doc/c4-keepalive.pid`, and `py-doc c4 down` ends it after checking that the number still belongs to `wsl.exe`.

## Structurizr Local

`c4/stack.py` starts Structurizr Local on a private Docker network. The tool container joins Local's network namespace, because Local answers only requests for `localhost`. Two modes share the code:

| Mode | Folder Local reads | Settings | Used by |
|---|---|---|---|
| Drawing | A temporary copy of the workspace folder, with the named workspace as the only `workspace.*`, and its `workspace.json` layouts when the workspace is a `.dsl` | Not editable, no auto-save | `py-doc build`, `c4 export`, `site` |
| Live | The project folder | Editable, auto-save | `py-doc c4 up` |

Drawing works on a copy because Local writes `workspace.json` whenever it reads a DSL, and prefers a `.dsl` when both files are there. Given the project folder, it once drew the DSL in place of the JSON a document named and wrote over the hand-written JSON. Live editing needs the project folder, because the layouts arranged in the browser must be saved where the project keeps them.
