# py-doc web on your own Docker server

`py-doc web` is py-doc in the browser, for a server on your own network:

- **Explorer.** Every folder of the workspace is a project. Drag files and whole folders from your computer onto a project or folder to upload them. Drop a folder on the empty space to make it a new project. Drag files inside the explorer to move them. Right-click anything for what you can do with it: new file or folder, upload, download (a folder as a zip), rename, delete.
- **Editor.** Markdown, YAML, PlantUML and the rest, with tabs, autosave and Ctrl+S.
- **Live preview.** A Markdown file as a document, slides or a poster, built again a moment after every save, with every diagram drawn. A build that fails keeps the last good page and shows why.
- **Convert.** One file to Word, PowerPoint, PDF, an HTML page, an HTML deck or a poster, written to the project's `out` folder.
- **Build.** A project with a `py-doc.yml` builds as a whole (`py-doc build`), or one format of it, with lint first or the site after.
- **Lint.** A file, a folder or a project, with every issue listed. Click one to go to its line.

It runs the same commands as the command line. Each tool still runs in a fresh container of the tool image, with no network.

## What the server needs

- Linux with Docker Engine and Docker Compose v2 (`docker compose version`)
- About 4 GB of free memory and 15 GB of disk for the tool image (and 5 to 30 minutes to build it the first time)
- This repository cloned on it

## Install

```bash
git clone https://github.com/markbac/py-doc.git
cd py-doc/deploy/web
./deploy.sh            # the first run writes .env and stops
nano .env              # check PYDOC_DATA, set PYDOC_WEB_PASSWORD
./deploy.sh            # builds both images, checks them, starts the service
```

Then open `http://<server>:8080/`. Sign in with any user name and the password from `.env`.

To update later, run `./update.sh`. It pulls, rebuilds the web image, rebuilds the tool image only if it changed, and restarts.

## How it works

```
browser ──► py-doc-web container ──(Docker socket)──► docker run py-doc-tools … (one per tool, --network none)
                 │                                          │
                 └──── PYDOC_DATA, same path in both ───────┘
```

- The `py-doc-web` container holds the page and py-doc itself. It starts tool containers through the host's Docker socket, as py-doc does on a PC.
- Tool containers are handed folders by their path, so `PYDOC_DATA` (the workspace, temporary files and caches) is mounted at the **same path** on the host and in the container. Don't change one without the other.
- It runs as `PUID:PGID`, the owner of `PYDOC_DATA`, and joins the socket's group (`DOCKER_GID`). Files it writes are yours on the host.
- The workspace is `PYDOC_DATA/workspace`. You can also copy projects straight into it, or put a Git clone there.

## Behind Nginx Proxy Manager

Add a proxy host such as `py-doc.lan`, forwarding to `http://<server>:8080`. Then either keep the app's password, or remove it and add an Access List in NPM.

- If the proxy runs on the same server, set `PYDOC_WEB_BIND=127.0.0.1` so the port isn't reachable any other way.
- Big uploads need a larger body size. In the proxy host's Advanced tab, add `client_max_body_size 512m;`.
- Long builds keep a request open for no more than a second, because the page polls. Nothing else needs changing.

## Security

The server runs py-doc on whatever is uploaded, and it can start containers on the host through the Docker socket. Treat it like SSH access to the server:

- Keep it on your own network. For access from outside, use Tailscale or a VPN, not a port forward.
- Always set a password, or put an Access List in front of it.
- Tool containers run without network, capabilities or new privileges, as py-doc always runs them. The page refuses any path outside the workspace, and HTML previews run in a sandbox of their own.

## Settings (`.env`)

| Setting | Default | What it is |
|---|---|---|
| `PYDOC_DATA` | `/srv/py-doc` | The data folder, at the same path on the host and in the container |
| `PUID`, `PGID` | your ids | The user the server runs as: the owner of `PYDOC_DATA` |
| `DOCKER_GID` | the socket's group | The group that may use `/var/run/docker.sock` |
| `PYDOC_WEB_PORT`, `PYDOC_WEB_BIND` | `8080`, `0.0.0.0` | Where it listens on the host |
| `PYDOC_WEB_PASSWORD` | empty | The page's password (any user name) |
| `PYDOC_WEB_WORKERS` | `1` | Jobs that run at the same time |
| `PYDOC_WEB_TIMEOUT` | `1800` | Seconds a job may take before it is stopped |

## Without Docker for the web part

On any machine where py-doc already works, including a Windows PC with WSL:

```bash
pip install -e ".[web]"
py-doc web --root ~/py-doc-workspace          # http://127.0.0.1:8080, this computer only
```
