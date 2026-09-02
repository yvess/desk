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
# the cdb service's published port, used by the `fixtures` task
COUCHDB_URL=${COUCHDB_URL:-http://admin:admin@127.0.0.1:5984}

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

# Load the dev fixture set into the running stack's CouchDB. The fixtures are
# pre-migration documents (no `version` property, `@ip_` map variables), so
# `migrate` has to run after them to bring them to the current document version.
# couchdb-design.json is skipped: it is a 2014 dump of the old design doc and is
# not even valid JSON (literal newlines inside strings). install-db owns that doc.
fixtures() {
    for f in tests/fixtures/couchdb-*.json; do
        [ "$f" = "tests/fixtures/couchdb-design.json" ] && continue
        id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["_id"])' "$f")"
        curl -fsS -o /dev/null -X PUT -H 'Content-Type: application/json' \
            --data-binary "@$f" "${COUCHDB_URL}/desk_drawer/$id"
        echo "  loaded $id"
    done
    compose exec -T foreman ./dworker migrate
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
