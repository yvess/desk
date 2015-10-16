FROM alpine:3.2
MAINTAINER Yves Serrano <y@yas.ch>

ADD requirements.txt /tmp/requirements.txt
RUN sed -i -e "s#dl-4\.#nl\.#" /etc/apk/repositories && \
    echo "@testing http://nl.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk add --update \
        python py-pip make readline openssl wget python-dev \
        libxml2 libxslt openldap libffi pango \
        git gcc g++ \
        openssl-dev readline-dev \
        libxml2-dev libxslt-dev openldap-dev libffi-dev pango-dev \
        cairo \
        pango-dev \
        bind-tools \
        ttf-freefont \
        runit@testing && \
    cat /tmp/requirements.txt |grep -v "^#"| xargs -n 1 pip install && \
    apk del gcc g++ openssl-dev readline-dev libxml2-dev libxslt-dev openldap-dev libffi-dev pango-dev && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*
ADD ./files /root/build/
ADD docker-entrypoint.sh /entrypoint.sh
ENV WORKER_TYPE foreman
ENTRYPOINT ["/entrypoint.sh"]
CMD ["worker"]
