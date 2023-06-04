FROM yvess/desk-worker:0.1.2d
MAINTAINER Yves Serrano <y@yas.ch>

RUN sed 's/3.4/3.6/g' -i /etc/apk/repositories && \
    apk update && \
    apk add --no-cache \
        pdns \
        pdns-backend-sqlite3 \
    && ln -s /usr/lib/pdns/pdns/libgsqlite3backend.so /usr/lib/pdns/libgsqlite3backend.so \
    && rm -rf /var/cache/apk/*
    # rm /etc/pdns.conf && \

ADD /etc/cont-init.d /etc/cont-init.d
ADD /etc/desk /etc/desk
ADD /etc/powerdns /etc/powerdns
ADD /etc/services.d /etc/services.d

ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
EXPOSE 53/udp 53/tcp
