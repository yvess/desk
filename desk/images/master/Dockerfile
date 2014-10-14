FROM yvess/pydev
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && apt-get install -y \
        libldap2-dev \
        libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*
RUN virtualenv /var/env
RUN . /var/env/bin/activate && pip install -r /tmp/requirements.txt
