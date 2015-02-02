FROM yvess/desk-worker
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && \
    apt-get install -y \
        pdns-backend-sqlite3 \
    && rm -rf /var/lib/apt/lists/*
ADD files /root/build
ADD entrypoint-worker.sh /entrypoint-worker.sh
ENV WORKER_TYPE worker
ENV WORKER_SUBTYPE dns
