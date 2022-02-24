FROM alpine:3.14
MAINTAINER Yves Serrano <y@yas.ch>
RUN apk update && apk add --no-cache \
        curl \
        python3 \
        python3-dev \
        py3-lxml \
        py3-pillow \
        py3-pip \
        py3-wheel \
        ipython \
        make \
        readline \
        openssl \
        pango \
        cairo \
        bind-tools \
        ttf-freefont \
        binutils \
        wget \
        jq
ARG S6_OVERLAY_VERSION="3.0.0.2-2"
RUN curl -Ls https://github.com/just-containers/s6-overlay/releases/download/v$S6_OVERLAY_VERSION/s6-overlay-noarch-$S6_OVERLAY_VERSION.tar.xz | tar xJ -C / \
    && curl -Ls https://github.com/just-containers/s6-overlay/releases/download/v$S6_OVERLAY_VERSION/s6-overlay-x86_64-$S6_OVERLAY_VERSION.tar.xz | tar xJ -C /
ADD requirements3.txt /tmp/requirements3.txt
RUN apk add --no-cache \
        build-base \
        readline-dev \
        git \
        pango-dev \
        cairo-dev \
    && pip3 install -r /tmp/requirements3.txt && \
    apk del \
        build-base \
        openssl-dev \
        readline-dev \
        libffi-dev \
        pango-dev \
        cairo-dev \
    && rm -rf /var/cache/apk/* /tmp/* /var/tmp/* /root/.cache
ADD etc.tar.gz /
ENV WORKER_TYPE foreman
ENTRYPOINT ["/init"]
