#!/usr/bin/env bash
# Build/run tasks for desk. Run from anywhere: ./taskfile.sh <task> [args]
set -euo pipefail
cd "$(dirname "$0")"

WORKER_VERSION=0.4.0
DNS_VERSION=0.4.0
REGISTRY=yvess
PUSH_PLATFORMS=linux/amd64,linux/arm64
# buildx auto-creates a "docker" driver builder named after the active context.
# That driver builds against the local image store, which is what lets the dns
# image use the just-built worker image as its base; a docker-container builder
# (often the selected one) only ever sees the registry.
LOCAL_BUILDER="$(docker context show)"

# The build context is docker/, so the dns image can COPY from worker/.
build_worker() {
    docker buildx build --builder "${LOCAL_BUILDER}" --load \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t "${REGISTRY}/desk-worker:${WORKER_VERSION}" \
        -f docker/worker/Dockerfile docker
}

# needs desk-worker:${WORKER_VERSION} locally or in the registry
build_dns() {
    docker buildx build --builder "${LOCAL_BUILDER}" --load \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --build-arg "WORKER_VERSION=${WORKER_VERSION}" \
        -t "${REGISTRY}/desk-dns:${DNS_VERSION}" \
        -f docker/dns/Dockerfile docker
}

build() {
    build_worker
    build_dns
}

# desk-dns builds FROM desk-worker, so the worker push has to land first.
push() {
    docker buildx build --push --platform "${PUSH_PLATFORMS}" \
        -t "${REGISTRY}/desk-worker:${WORKER_VERSION}" \
        -f docker/worker/Dockerfile docker
    docker buildx build --push --platform "${PUSH_PLATFORMS}" \
        --build-arg "WORKER_VERSION=${WORKER_VERSION}" \
        -t "${REGISTRY}/desk-dns:${DNS_VERSION}" \
        -f docker/dns/Dockerfile docker
}

pull() {
    docker pull "${REGISTRY}/desk-worker:${WORKER_VERSION}"
    docker pull "${REGISTRY}/desk-dns:${DNS_VERSION}"
}

compose() {
    docker compose -f docker-compose.yml -f docker-extra.yml "$@"
}

up() {
    compose up -d "$@"
}

down() {
    compose down "$@"
}

logs() {
    compose logs -f "$@"
}

test() {
    python -m unittest discover
}

help() {
    echo "tasks: $(grep -oE '^[a-z_]+\(\)' "$0" | tr -d '()' | tr '\n' ' ')"
}

"${@:-help}"
