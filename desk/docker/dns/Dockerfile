FROM yvess/desk-worker
MAINTAINER Yves Serrano <y@yas.ch>

RUN apk add --update \
        pdns-backend-sqlite3@testing && \
    ln -s /usr/lib/pdns/pdns/libgsqlite3backend.so /usr/lib/pdns/libgsqlite3backend.so && \
    rm -rf /var/cache/apk/*
ADD files /root/build
ADD entrypoint-worker.sh /entrypoint-worker.sh
ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
EXPOSE 53/udp 53/tcp
