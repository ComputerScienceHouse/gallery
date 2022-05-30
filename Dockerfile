FROM docker.io/python:3.9.7-buster
MAINTAINER Computer Science House <rtp@csh.rit.edu>

ENV IMAGEIO_USERDIR /var/lib/gallery

RUN apt-get update && \
    apt-get install -y libldap-dev libsasl2-dev libmagic-dev ghostscript && \
    apt-get autoremove --yes && \
    apt-get clean autoclean && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/ && \
    mkdir -p /opt/gallery /var/lib/gallery

RUN pip install --upgrade pip

WORKDIR /opt/gallery
ADD . /opt/gallery

RUN pip install \
        --no-warn-script-location \
        --no-cache-dir \
        -r requirements.txt

RUN groupadd -r gallery && \
    useradd -l -r -u 1001 -d /var/lib/gallery -g gallery gallery && \
    chown -R gallery:gallery /opt/gallery /var/lib/gallery && \
    chmod -R og+rwx /var/lib/gallery

USER gallery

CMD ddtrace-run gunicorn "wsgi:app" \
    --workers 4 \
    --timeout 600 \
    --capture-output \
    --bind=0.0.0.0:8080 \
    --access-logfile=-
