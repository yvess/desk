FROM alpine:3.24
LABEL org.opencontainers.image.authors="Yves Serrano <y@yas.ch>"
LABEL org.opencontainers.image.source="https://github.com/yvess/desk"

# cairo/pango/fontconfig are the shared libraries CairoSVG and WeasyPrint dlopen
# at runtime; the rest are used by the s6 init scripts and by hand for debugging.
RUN apk add --no-cache \
        bind-tools \
        cairo \
        curl \
        fontconfig \
        jq \
        openssl \
        pango \
        py3-pip \
        python3 \
        ttf-freefont \
        wget

ARG S6_OVERLAY_VERSION=3.2.3.2
ENV S6_STAGE2_HOOK=/etc/s6-overlay/setup-user-services.sh
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2
# worker-init blocks until CouchDB answers, which has no useful upper bound;
# 0 means "wait as long as it takes" instead of failing stage2
ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0
ENV PATH="/opt/desk/bin:${PATH}:/command"

# The legacy-* bundles keep /etc/cont-init.d and /etc/services.d alive; this
# image uses s6-rc.d only, so they are excluded from the noarch tarball.
RUN wget -q -O - "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" | \
        xzcat | tar x \
            --exclude='./*/*/*/*/*/*/legacy-cont-init' \
            --exclude='./*/*/*/*/*/*/*/*/legacy-cont-init' \
            --exclude='./*/*/*/*/*/*/legacy-services' \
            --exclude='./*/*/*/*/*/*/*/*/legacy-services' \
            -C / \
    && wget -q -O - "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-`arch`.tar.xz" | \
        xzcat | tar x -C /

# Alpine's python is externally managed (PEP 668), so the deps live in a venv.
COPY worker/requirements3.txt worker/requirements3.lock /tmp/
RUN apk add --no-cache --virtual .build-deps \
        build-base \
        libffi-dev \
        python3-dev \
    && python3 -m venv /opt/desk \
    && /opt/desk/bin/pip install --no-cache-dir \
        -r /tmp/requirements3.txt -c /tmp/requirements3.lock \
    && apk del .build-deps \
    && rm -rf /tmp/requirements3.txt /tmp/requirements3.lock /root/.cache

COPY worker/etc /etc
# `top` pulls in both user bundles, and git cannot carry an empty directory
RUN mkdir -p /etc/s6-overlay/user-bundles.d/user2/contents.d \
    && echo bundle > /etc/s6-overlay/user-bundles.d/user2/type

ENV WORKER_TYPE=foreman
ENTRYPOINT ["/init"]
