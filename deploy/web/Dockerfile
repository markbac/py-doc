# py-doc web: the page and the py-doc commands, in a small image. The tools themselves run in the
# py-doc tool image, which this container starts through the host's Docker socket.
# Built from the repository root: docker compose -f deploy/web/docker-compose.yml build

FROM docker:27.5.1-cli AS docker-cli

FROM python:3.12.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git: the py-logkit dependency installs from Git, and generators read project history.
# The Docker CLI and its buildx plugin: py-doc starts tool containers and builds the tool image with them.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx

WORKDIR /opt/py-doc
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install ".[web]" \
 && python -c "import uuid; print(uuid.uuid4().hex[:12])" > /opt/py-doc/build-id
COPY deploy/web/entrypoint.sh /usr/local/bin/py-doc-entrypoint
RUN chmod 755 /usr/local/bin/py-doc-entrypoint

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PYDOC_WEB_PORT','8080'), timeout=4)"
ENTRYPOINT ["py-doc-entrypoint"]
CMD ["py-doc", "web"]
