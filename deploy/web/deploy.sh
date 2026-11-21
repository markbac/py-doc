#!/usr/bin/env bash
# Install, start or update py-doc web on this Docker server. Run it again any time: it pulls the latest
# py-doc, rebuilds only what changed (the tool image only when its definition changed) and restarts.
#   ./deploy.sh              pull, build, start
#   ./deploy.sh --no-pull    build and start what is here
set -euo pipefail
cd "$(dirname "$0")"

pull=yes
[ "${1:-}" = "--no-pull" ] && pull=no

command -v docker >/dev/null || { echo "Docker is not installed" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is needed (docker compose version)" >&2; exit 1; }

# --- the latest py-doc -------------------------------------------------------------------------
if [ "$pull" = yes ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  before=$(git rev-parse HEAD)
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "The repository has local changes, so it is not pulled (git stash them to update). Deploying what is here."
  else
    echo "== Pulling the latest py-doc"
    git pull --ff-only || echo "git pull failed, so what is here is deployed" >&2
  fi
  if [ "$(git rev-parse HEAD)" != "$before" ]; then
    git log --oneline "$before..HEAD" | head -20
    exec "$0" --no-pull  # this script may have changed too: run the new one
  fi
fi

# --- settings ----------------------------------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s/^PUID=.*/PUID=$(id -u)/; s/^PGID=.*/PGID=$(id -g)/" .env
  sed -i "s/^DOCKER_GID=.*/DOCKER_GID=$(stat -c %g /var/run/docker.sock)/" .env
  echo "Wrote .env. Check PYDOC_DATA and set PYDOC_WEB_PASSWORD, then run ./deploy.sh again."
  exit 0
fi
set -a; . ./.env; set +a

case "$PYDOC_DATA" in /*) ;; *) echo "PYDOC_DATA must be an absolute path" >&2; exit 1;; esac
if ! mkdir -p "$PYDOC_DATA/workspace" "$PYDOC_DATA/tmp" "$PYDOC_DATA/home" 2>/dev/null; then
  echo "Cannot create $PYDOC_DATA as $(id -un). Either make it yours once:" >&2
  echo "    sudo mkdir -p $PYDOC_DATA && sudo chown $PUID:$PGID $PYDOC_DATA" >&2
  echo "or put it in your home folder: set PYDOC_DATA=$HOME/py-doc-data in .env. Then run ./deploy.sh again." >&2
  exit 1
fi
if [ "$(stat -c %u "$PYDOC_DATA")" != "$PUID" ]; then
  echo "$PYDOC_DATA is not owned by user $PUID; run: sudo chown -R $PUID:$PGID $PYDOC_DATA" >&2
  exit 1
fi
[ -n "${PYDOC_WEB_PASSWORD:-}" ] || echo "Note: no PYDOC_WEB_PASSWORD, so put a proxy that asks for one in front of it."

# --- build and start ---------------------------------------------------------------------------
echo "== Building the web image"
docker compose build

echo "== Making sure the tool image is there (the first build takes 5 to 30 minutes)"
docker compose run --rm --no-deps py-doc-web python -c "from py_doc.runtime import connect; connect()"
docker compose run --rm --no-deps py-doc-web py-doc doctor

echo "== Starting"
docker compose up -d   # recreates the container only when its image or settings changed
docker image prune -f >/dev/null
echo "py-doc web is on http://$(hostname -I 2>/dev/null | awk '{print $1}'):${PYDOC_WEB_PORT:-8888}/"
echo "Old tool images can be removed with: docker compose run --rm py-doc-web py-doc tools prune"
