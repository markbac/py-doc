---
title: Installation
---

# Installation

## Python package

py-doc needs Python 3.10 or later.

```bash
git clone https://github.com/markbac/py-doc.git
cd py-doc
pip install -e .            # ctxlogkit is installed from GitHub with it
pip install -e ".[dev]"     # with pytest, ruff, build and twine
```

## Supported platforms

Linux and Windows. The tool runner refuses to start on any other platform, with exit status `2` and a message that names the two supported ones. Commands that run no external tool work wherever Python does: `lint` with the built-in rules, `template`, `import` of Word and PowerPoint files without vector pictures, and `c4 check` and `c4 export -f markdown` on a `workspace.json`.

## Tool container

Programs that are not Python run inside one container image, so nothing but Python and Docker has to be installed. They include pandoc, TeX, PlantUML, Mermaid, Graphviz, Chromium, `structurizr-cli`, Vale, markdownlint, MkDocs and Node. On Linux that is Docker. On Windows it is Docker Engine inside a WSL 2 distribution, not Docker Desktop.

```bash
py-doc setup             # install Docker Engine (Ubuntu or Debian: in the WSL distro on Windows, or here on Linux)
py-doc tools build       # build the image here (several GB, 5 to 30 minutes the first time, with progress)
py-doc doctor            # check the platform, WSL, Docker, the image and a trivial run
py-doc tools status      # image tag, and the version of each tool inside it
py-doc tools prune       # remove images left by older py-doc versions
py-doc tools lock        # only after changing a tool version in tools.lock
```

`py-doc setup` shows the steps it will run as root and asks first. `--yes` skips the question and `--dry-run` prints the script and runs nothing. It adds Docker's apt repository, installs the engine, adds your user to the `docker` group, turns on systemd in the distro and starts Docker. WSL itself must already be installed (`wsl --install -d Ubuntu`). It does nothing when Docker already works, and a build never runs it. After it, run `wsl --shutdown` once on Windows so the new group takes effect.

The image is built from a `Dockerfile` that ships in the package, and its tag is a hash of that folder. A release that changes the toolchain builds a new image, and one that does not reuses the old one. A command that needs the image and finds none builds it first. Downloads that are not Debian packages (pandoc, PlantUML, ditaa, Vale, structurizr-cli and Node.js) are listed in `tools.lock` with their checksums, and a mismatch stops the build. Builds behind a proxy that re-signs TLS take `--ca-file`. Machines that cannot build can use `py-doc tools save` and `py-doc tools load`.

`py-doc.yml` can name the engine:

```yaml
runtime:
  docker: /usr/bin/docker   # if it is not on the path
  wsl_distro: Ubuntu        # Windows only: the distribution that runs Docker
```

> [!NOTE]
> WSL stops a distribution soon after its last `wsl.exe` process ends, and Docker and its containers with it. py-doc keeps one running for as long as a long-lived container needs it, such as Structurizr Local during `py-doc c4 up`.

## Exit statuses

Environment problems (no engine, no image, an unsupported platform) exit with status `2`. A tool that runs and fails exits with `1`, and its whole output is shown.

## Upgrading from the native renderers

Earlier versions drew Word and PowerPoint files themselves unless a document said `engine: pandoc`. That path is removed, so Docker is needed for every conversion.

- `engine` in `py-doc.yml` is an error, with a message. Delete it.
- `keep_template_body`, `keep_template_slides`, `title_layout` and `content_layout` are errors too, and so are `--keep-template-body`, `--keep-template-slides`, `--title-layout` and `--content-layout`. The document now goes where the template has `[[INSERTCONTENT]]` (at the end without one), and pandoc picks the layouts.
- Output looks different: pandoc's styles replace the old ones. Check your templates, and run `py-doc doctor` first.
- `DocxConverter` and `SlidesConverter` keep their names. They take an optional `runtime` and connect to the container on first use.
