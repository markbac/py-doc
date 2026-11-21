#!/bin/sh
# py-doc hands tool containers some files of its own package (the diagram scripts) by their path, and the
# host's Docker must find them there. So the package is copied to the shared data folder, which has the
# same path on the host and in here, and run from that copy. One copy per image build; old ones are removed.
set -e
if [ -n "${PYDOC_DATA:-}" ]; then
  build=$(cat /opt/py-doc/build-id)
  app="$PYDOC_DATA/app/$build"
  if [ ! -d "$app/py_doc" ]; then
    source=$(python -c "import os, py_doc; print(os.path.dirname(py_doc.__file__))")
    mkdir -p "$PYDOC_DATA/app"
    rm -rf "$app.partial"
    mkdir -p "$app.partial"
    cp -R "$source" "$app.partial/py_doc"
    mv "$app.partial" "$app"
  fi
  find "$PYDOC_DATA/app" -mindepth 1 -maxdepth 1 -type d ! -name "$build" -mtime +1 -exec rm -rf {} + 2>/dev/null || true
  export PYTHONPATH="$app${PYTHONPATH:+:$PYTHONPATH}"
fi
exec "$@"
