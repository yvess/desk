FROM desk/worker
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && apt-get install -y \
        libldap2-dev \
        libsasl2-dev \
        pdns-backend-sqlite3 \
    && rm -rf /var/lib/apt/lists/*
ADD service/pdns /etc/service/pdns
ADD entrypoint-worker.sh /entrypoint-worker.sh
