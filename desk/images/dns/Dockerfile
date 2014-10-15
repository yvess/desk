FROM yvess/pydev
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && apt-get install -y \
        libldap2-dev \
        libsasl2-dev \
        pdns-backend-sqlite3 \
    && rm -rf /var/lib/apt/lists/*
ADD ./etc/service/pdns /etc/service/pdns
RUN virtualenv /var/py27
ADD ./requirements.txt /tmp/requirements.txt
RUN . /var/py27/bin/activate && pip install -r /tmp/requirements.txt

