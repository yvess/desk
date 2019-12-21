FROM yvess/desk-worker:0.2.1
MAINTAINER Yves Serrano <y@yas.ch>

RUN apk add --no-cache \
        pdns \
        pdns-backend-sqlite3 && \
    rm -rf /var/cache/apk/*
    # rm /etc/pdns.conf && \
ADD etc.tar.gz /
ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
EXPOSE 53/udp 53/tcp
