FROM alpine:3.3
MAINTAINER Yves Serrano <y@yas.ch>

# s6 overlay
RUN apk add --no-cache wget && \
  wget -q https://github.com/just-containers/s6-overlay/releases/download/v1.17.2.0/s6-overlay-amd64.tar.gz --no-check-certificate -O /tmp/s6-overlay.tar.gz && \
  tar xvfz /tmp/s6-overlay.tar.gz -C / && \
  rm -f /tmp/s6-overlay.tar.gz && \
  apk del wget

ADD requirements.txt /tmp/requirements.txt
RUN sed -i -e "s#dl-4\.#nl\.#" /etc/apk/repositories && \
    apk add --no-cache \
        python \
        py-pip \
        make \
        readline \
        openssl \
        wget \
        python-dev \
        libxml2 \
        libxslt \
        openldap \
        libffi \
        pango \
        git \
        gcc \
        g++ \
        openssl-dev \
        readline-dev \
        libxml2-dev \
        libxslt-dev \
        openldap-dev \
        libffi-dev \
        pango-dev \
        cairo \
        pango-dev \
        bind-tools \
        ttf-freefont \
        && \
    cat /tmp/requirements.txt |grep -v "^#"| xargs -n 1 pip install && \
    apk del \
        gcc \
        g++ \
        openssl-dev \
        readline-dev \
        libxml2-dev \
        libxslt-dev \
        openldap-dev \
        libffi-dev \
        pango-dev \
        && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*
ADD ./etc/ /etc/
ENV WORKER_TYPE foreman
ENTRYPOINT ["/init"]
