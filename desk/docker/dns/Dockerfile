# The dns node is a worker that also runs PowerDNS, so it builds on the worker
# image instead of repeating its python install.
ARG WORKER_VERSION
FROM yvess/desk-worker:${WORKER_VERSION}
LABEL org.opencontainers.image.authors="Yves Serrano <y@yas.ch>"
LABEL org.opencontainers.image.source="https://github.com/yvess/desk"

# sqlite is the CLI, used by pdns-init to create the zone database
RUN apk add --no-cache \
        pdns \
        pdns-backend-sqlite3 \
        sqlite

COPY dns/etc /etc

ENV WORKER_TYPE=worker
ENV WORKER_SUBTYPE=dns
EXPOSE 53/udp 53/tcp
