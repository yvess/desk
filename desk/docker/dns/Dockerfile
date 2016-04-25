FROM yvess/desk-worker:0.1
MAINTAINER Yves Serrano <y@yas.ch>

RUN apk add --no-cache \
        pdns-backend-sqlite3&& \
    ln -s /usr/lib/pdns/pdns/libgsqlite3backend.so /usr/lib/pdns/libgsqlite3backend.so && \
    rm -rf /var/cache/apk/*
ADD ./etc/ /etc/
ADD entrypoint-worker.sh /entrypoint-worker.sh
ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
EXPOSE 53/udp 53/tcp
