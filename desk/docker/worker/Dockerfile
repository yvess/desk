FROM alpine:3.10
MAINTAINER Yves Serrano <y@yas.ch>
ARG S6_OVERLAY_VERSION=v1.22.1.0

RUN apk update && apk add \
        curl \
        python3 \
        python3-dev \
        py3-lxml \
        py3-pillow \
        ipython \
        make \
        readline \
        openssl \
        pango \
        cairo \
        bind-tools \
        ttf-freefont \
        jq && \
    pip3 install --upgrade pip
RUN curl -Ls https://github.com/just-containers/s6-overlay/releases/download/$S6_OVERLAY_VERSION/s6-overlay-amd64.tar.gz | tar xz -C /
ADD requirements3.txt /tmp/requirements3.txt
RUN apk add \
        build-base \
        readline-dev \
        git \
        pango-dev \
        cairo-dev \
       && \
    pip3 install -r /tmp/requirements3.txt && \
    apk del \
        build-base \
        openssl-dev \
        readline-dev \
        libffi-dev \
        pango-dev \
        cairo-dev
    #     && \
    # rm -rf /var/cache/apk/* /tmp/* /var/tmp/*
ADD etc.tar.gz /
ENV WORKER_TYPE foreman
ENTRYPOINT ["/init"]
