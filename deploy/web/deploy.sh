#!/usr/bin/env bash
# Install or start py-doc web on this Docker server: write .env, build the images, start the service.
# Run it from anywhere; it works beside this file. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")"

command -v docker >/dev/null || { echo "Docker is not installed" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is needed (docker compose version)" >&2; exit 1; }

if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s/^PUID=.*/PUID=$(id -u)/; s/^PGID=.*/PGID=$(id -g)/" .env
  sed -i "s/^DOCKER_GID=.*/DOCKER_GID=$(stat -c %g /var/run/docker.sock)/" .env
  echo "Wrote .env. Check PYDOC_DATA and set PYDOC_WEB_PASSWORD, then run ./deploy.sh again."
  exit 0
fi
set -a; . ./.env; set +a

case "$PYDOC_DATA" in /*) ;; *) echo "PYDOC_DATA must be an absolute path" >&2; exit 1;; esac
mkdir -p "$PYDOC_DATA/workspace" "$PYDOC_DATA/tmp" "$PYDOC_DATA/home"
if [ "$(stat -c %u "$PYDOC_DATA")" != "$PUID" ]; then
  echo "$PYDOC_DATA is not owned by user $PUID; run: sudo chown -R $PUID:$PGID $PYDOC_DATA" >&2
  exit 1
fi
[ -n "${PYDOC_WEB_PASSWORD:-}" ] || echo "Note: no PYDOC_WEB_PASSWORD, so put a proxy that asks for one in front of it."

echo "== Building the web image"
docker compose build

echo "== Making sure the tool image is there (the first build takes 5 to 30 minutes)"
docker compose run --rm --no-deps py-doc-web python -c "from py_doc.runtime import connect; connect()"
docker compose run --rm --no-deps py-doc-web py-doc doctor

echo "== Starting"
docker compose up -d
echo "py-doc web is on http://$(hostname -I 2>/dev/null | awk '{print $1}'):${PYDOC_WEB_PORT:-8888}/"
