#!/usr/bin/env bash
# The same as ./deploy.sh, which pulls, rebuilds what changed and restarts. Kept for the name.
exec "$(dirname "$0")/deploy.sh" "$@"
