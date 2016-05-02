FROM yvess/desk-worker:0.1
MAINTAINER Yves Serrano <y@yas.ch>

RUN echo -e "@edgetesting http://dl-cdn.alpinelinux.org/alpine/edge/testing\n@edgemain http://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories && \
    apk add --no-cache \
        boost-serialization@edgemain \
        boost-program_options@edgemain \
        pdns@edgetesting \
        pdns-backend-sqlite3@edgetesting && \
    ln -s /usr/lib/pdns/pdns/libgsqlite3backend.so /usr/lib/pdns/libgsqlite3backend.so && \
    rm -rf /var/cache/apk/*
ADD ./etc/ /etc/
ADD entrypoint-worker.sh /entrypoint-worker.sh
ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
EXPOSE 53/udp 53/tcp

