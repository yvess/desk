FROM yvess/pydev
MAINTAINER Yves Serrano <y@yas.ch>

RUN apt-get update && apt-get install -y \
        libldap2-dev \
        libsasl2-dev \
        runit \
    && rm -rf /var/lib/apt/lists/*
ADD requirements.txt /tmp/requirements.txt
RUN . /var/py27/bin/activate && cat /tmp/requirements.txt |grep -v "^#"| xargs -n 1 pip install
RUN mkdir -p /etc/desk
ADD worker.conf /etc/desk/
ADD service /etc/service
ADD docker-entrypoint.sh /entrypoint.sh
ENV WORKER_TYPE foreman
ENTRYPOINT ["/entrypoint.sh"]
CMD ["worker"]
