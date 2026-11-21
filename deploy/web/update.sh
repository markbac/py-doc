#!/usr/bin/env bash
# Update py-doc web: pull, rebuild the web image, build the tool image only if it changed, restart.
set -euo pipefail
cd "$(dirname "$0")"
git pull --ff-only
docker compose build
docker compose run --rm --no-deps py-doc-web python -c "from py_doc.runtime import connect; connect()"
docker compose up -d
docker image prune -f >/dev/null
echo "Updated. Old tool images can be removed with: docker compose run --rm py-doc-web py-doc tools prune"
