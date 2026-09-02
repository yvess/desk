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

# One buildx invocation per image, spelled once. "$@" carries the flags that
# differ between a local build (--load) and a registry push (--push --platform).
# The build context is docker/, so the dns image can COPY from worker/.
_buildx_worker() {
    docker buildx build "$@" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t "${REGISTRY}/desk-worker:${WORKER_VERSION}" \
        -f docker/worker/Dockerfile docker
}

_buildx_dns() {
    docker buildx build "$@" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --build-arg "WORKER_VERSION=${WORKER_VERSION}" \
        -t "${REGISTRY}/desk-dns:${DNS_VERSION}" \
        -f docker/dns/Dockerfile docker
}

build_worker() {
    _buildx_worker --builder "${LOCAL_BUILDER}" --load
}

# needs desk-worker:${WORKER_VERSION} locally or in the registry
build_dns() {
    _buildx_dns --builder "${LOCAL_BUILDER}" --load
}

build() {
    build_worker
    build_dns
}

# desk-dns builds FROM desk-worker, so the worker push has to land first.
push() {
    _buildx_worker --push --platform "${PUSH_PLATFORMS}"
    _buildx_dns --push --platform "${PUSH_PLATFORMS}"
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

# shadows the `test` builtin for the rest of this file -- AGENTS.md documents
# `./taskfile.sh test`, so the name stays; use [ ... ] instead of bare `test`.
test() {
    python -m unittest discover
}

# tasks are the top-level functions; helpers are prefixed with _ and hidden
help() {
    echo "tasks: $(grep -oE '^[a-z][a-z_]*\(\)' "$0" | tr -d '()' | tr '\n' ' ')"
}

"${@:-help}"
