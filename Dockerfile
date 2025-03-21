FROM docker.io/python:3.13-bookworm
MAINTAINER Computer Science House <rtp@csh.rit.edu>

ENV IMAGEIO_USERDIR /var/lib/gallery

RUN apt-get update && \
    apt-get install -y libldap-dev libsasl2-dev libmagic-dev ghostscript libldap-common && \
    apt-get autoremove --yes && \
    apt-get clean autoclean && \
    sed -i \
      's/rights="none" pattern="PDF"/rights="read | write" pattern="PDF"/' \
      /etc/ImageMagick-6/policy.xml && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/ && \
    mkdir -p /opt/gallery /var/lib/gallery && \
    wget 'https://github.com/imageio/imageio-binaries/raw/504db2368125044a9da3bcfe031e1d9166fb7647/ffmpeg/ffmpeg-linux64-v3.3.1' && \
    mv ffmpeg-linux64-v3.3.1 /var/lib/gallery/ffmpeg && \
    chmod a+x /var/lib/gallery/ffmpeg

ENV FFMPEG_BINARY /var/lib/gallery/ffmpeg

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
