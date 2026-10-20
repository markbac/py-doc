# The py-doc tool image: every external program the document pipeline runs.
# Built locally by `py-doc tools build`. The tag is a hash of this folder, so a change here rebuilds.
FROM debian:12.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PUPPETEER_SKIP_DOWNLOAD=1 \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    PATH=/opt/venv/bin:/opt/node/node_modules/.bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1

# A certificate for builds behind a TLS-inspecting proxy (nothing unless --ca-file was given).
COPY extra-ca/ /usr/local/share/ca-certificates/
COPY tools.lock fetch.sh requirements.txt package.json puppeteer.json export-diagrams.js asyncapi-docs.js /tmp/build/

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git unzip \
 && update-ca-certificates \
 && apt-get install -y --no-install-recommends \
      fontconfig fonts-dejavu fonts-liberation fonts-noto-core fonts-crosextra-caladea fonts-crosextra-carlito lmodern \
      texlive-xetex texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
      texlive-pictures texlive-plain-generic \
      default-jre-headless graphviz inkscape librsvg2-bin chromium \
      python3 python3-venv python3-pip xz-utils \
 && rm -rf /var/lib/apt/lists/*

# Downloaded tools, and Node.js (Debian 12 has Node 18; the AsyncAPI generator needs 24.11 or later).
# Their urls and checksums are in tools.lock, and a mismatch stops the build.
RUN sh /tmp/build/fetch.sh pandoc /tmp/pandoc.deb \
 && apt-get install -y --no-install-recommends /tmp/pandoc.deb \
 && sh /tmp/build/fetch.sh plantuml /opt/plantuml.jar \
 && sh /tmp/build/fetch.sh ditaa /opt/ditaa.jar \
 && sh /tmp/build/fetch.sh vale /tmp/vale.tar.gz \
 && tar -xzf /tmp/vale.tar.gz -C /usr/local/bin vale \
 && sh /tmp/build/fetch.sh structurizr-cli /tmp/structurizr-cli.zip \
 && unzip -q /tmp/structurizr-cli.zip -d /opt/structurizr-cli \
 && printf '#!/bin/sh\nexec /opt/structurizr-cli/structurizr.sh "$@"\n' > /usr/local/bin/structurizr-cli \
 && chmod +x /opt/structurizr-cli/structurizr.sh /usr/local/bin/structurizr-cli \
 && printf '#!/bin/sh\nexec java -Djava.awt.headless=true -jar /opt/plantuml.jar "$@"\n' > /usr/local/bin/plantuml \
 && printf '#!/bin/sh\nexec java -Djava.awt.headless=true -jar /opt/ditaa.jar "$@"\n' > /usr/local/bin/ditaa \
 && chmod +x /usr/local/bin/plantuml /usr/local/bin/ditaa \
 && sh /tmp/build/fetch.sh node /tmp/node.tar.xz \
 && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 --exclude CHANGELOG.md --exclude LICENSE --exclude README.md \
 && rm -f /tmp/pandoc.deb /tmp/vale.tar.gz /tmp/structurizr-cli.zip /tmp/node.tar.xz

# Python and Node diagram and API documentation tools, at the versions pinned beside this file.
# mermaid-cli 12 needs Node 22.13 or later and puppeteer 25. package.json pins the Mermaid it draws with in
# "overrides", as mermaid-cli asks for ^12.
# allowScripts in package.json denies every dependency install script (npm 11 runs none it has not been told about):
# canvas loads without its node-gyp rebuild, puppeteer's would download a Chrome the image does not use, and the
# rest delete leftover files, print a banner or send usage telemetry.
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/build/requirements.txt \
 && mkdir -p /opt/node /etc/py-doc \
 && cp /tmp/build/package.json /opt/node/package.json \
 && cd /opt/node && npm install --omit=dev --no-audit --no-fund \
 && cp /tmp/build/puppeteer.json /etc/py-doc/puppeteer.json \
 && cp /tmp/build/export-diagrams.js /opt/node/export-diagrams.js \
 && cp /tmp/build/asyncapi-docs.js /opt/node/asyncapi-docs.js \
 && node /opt/node/asyncapi-docs.js --compile \
 && rm -rf /tmp/build /root/.npm

# A cache every run shares, as a volume: font caches, TeX caches and Chromium profiles live here.
# The volume copies this folder's mode the first time it is used, so any user can write to it.
RUN mkdir -p /cache/home && chmod -R 1777 /cache
ENV HOME=/cache/home

WORKDIR /work
