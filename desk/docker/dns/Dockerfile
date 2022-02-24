FROM alpine:3.14
MAINTAINER Yves Serrano <y@yas.ch>
RUN apk add --no-cache \
        curl \
        wget \
        pdns \
        pdns-backend-sqlite3 && \
    rm -rf /var/cache/apk/*
    # rm /etc/pdns.conf && \
ARG S6_OVERLAY_VERSION="3.0.0.2-2"
RUN curl -Ls https://github.com/just-containers/s6-overlay/releases/download/v$S6_OVERLAY_VERSION/s6-overlay-noarch-$S6_OVERLAY_VERSION.tar.xz | tar xJ -C / \
    && curl -Ls https://github.com/just-containers/s6-overlay/releases/download/v$S6_OVERLAY_VERSION/s6-overlay-x86_64-$S6_OVERLAY_VERSION.tar.xz | tar xJ -C /
ADD etc.tar.gz /
ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
EXPOSE 53/udp 53/tcp
ENTRYPOINT ["/init"]
