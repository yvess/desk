FROM yvess/aldev
MAINTAINER Yves Serrano <y@yas.ch>

RUN echo "@testing http://dl-4.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk add --update \
        openldap-dev \
        libffi-dev \
        cairo \
        pango-dev \
        bind-tools \
        runit@testing  && \
    curl -SL 'https://bootstrap.pypa.io/get-pip.py' | python2.7  && \
    pip install virtualenv && virtualenv /var/py27 && \
    rm -rf /var/cache/apk/*

ADD requirements.txt /tmp/requirements.txt
RUN . /var/py27/bin/activate && cat /tmp/requirements.txt |grep -v "^#"| xargs -n 1 pip install
ADD files /root/build
ADD docker-entrypoint.sh /entrypoint.sh
ENV WORKER_TYPE foreman
VOLUME /var/py27
ENTRYPOINT ["/entrypoint.sh"]
CMD ["worker"]
