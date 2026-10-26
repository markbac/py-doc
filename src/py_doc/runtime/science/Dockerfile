# The py-doc science image: the tool image, with the scientific Python libraries a few fences draw with.
# Built by `py-doc tools build --science`, or the first time a document or poster draws one of those fences.
# Its tag is a hash of this folder and of the tool image's, so a change to either rebuilds it.
ARG BASE
FROM ${BASE}

USER root
COPY requirements.txt /tmp/science/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/science/requirements.txt \
 && MPLCONFIGDIR=/tmp/mpl /opt/venv/bin/python -c "import matplotlib.pyplot" \
 && rm -rf /tmp/science /tmp/mpl
ENV MPLBACKEND=agg MPLCONFIGDIR=/cache/home/matplotlib
WORKDIR /work
