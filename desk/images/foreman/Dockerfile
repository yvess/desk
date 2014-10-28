FROM yvess/pydev
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && apt-get install -y \
        libldap2-dev \
        libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*
RUN virtualenv /var/py27
ADD ./requirements.txt /tmp/requirements.txt
RUN . /var/py27/bin/activate && cat /tmp/requirements.txt |grep -v "^#"| xargs -n 1 pip install
# ADD ./root/insecure_key /root/.ssh/id_rsa
# ADD ./root/insecure_key.pub /root/.ssh/id_rsa.pub
# RUN chmod 0600 /root/.ssh/id_rsa
ADD ./root/_profile /root/.profile
