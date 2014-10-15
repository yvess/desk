FROM yvess/pydev
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && apt-get install -y \
        libldap2-dev \
        libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*
RUN virtualenv /var/py27
ADD ./requirements.txt /tmp/requirements.txt
RUN . /var/py27/bin/activate && pip install -r /tmp/requirements.txt
ADD ./insecure_key /root/.ssh/id_rsa
ADD ./insecure_key.pub /root/.ssh/id_rsa.pub
ADD ./root/_profile /root/.profile
