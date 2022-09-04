FROM alpine:3.16
MAINTAINER Yves Serrano <y@yas.ch>
RUN apk update && apk add --no-cache \
        curl \
        python3 \
        py3-pillow \
        py3-brotli \
        py3-pip \
        py3-cffi \
        py3-wheel \
        py3-lxml \
        py3-reportlab \
        py3-jinja2 \
        make \
        readline \
        openssl \
        pango \
        bind-tools \
        ttf-freefont \
        binutils \
        wget \
        upx \
        libxml2 \
        libxslt \
        jq
ARG S6_OVERLAY_VERSION="3.0.0.2-2"
ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME 20000
RUN curl -Ls https://github.com/just-containers/s6-overlay/releases/download/v$S6_OVERLAY_VERSION/s6-overlay-noarch-$S6_OVERLAY_VERSION.tar.xz | tar xJ -C / \
    && curl -Ls https://github.com/just-containers/s6-overlay/releases/download/v$S6_OVERLAY_VERSION/s6-overlay-x86_64-$S6_OVERLAY_VERSION.tar.xz | tar xJ -C /
ADD requirements3.txt /tmp/requirements3.txt
RUN apk add --no-cache \
        build-base \
        openssl-dev \
        readline-dev \
        musl-dev \
        git \
        pango-dev \
        python3-dev \
        libxml2-dev \
        libxslt-dev \
    && pip3 install -r /tmp/requirements3.txt && \
    apk del \
        build-base \
        openssl-dev \
        readline-dev \
        musl-dev \
        git \
        pango-dev \
        python3-dev \
        libxml2-dev \
        libxslt-dev \
    && rm -rf /var/cache/apk/* /tmp/* /var/tmp/* /root/.cache
ADD etc.tar.gz /
ENV WORKER_TYPE foreman
ENTRYPOINT ["/init"]
