#!/usr/bin/env bash
# Build/run tasks for desk. Run from anywhere: ./taskfile.sh <task> [args]
set -euo pipefail
cd "$(dirname "$0")"

WORKER_VERSION=0.5.0
DNS_VERSION=0.5.0
REGISTRY=yvess
PUSH_PLATFORMS=linux/amd64,linux/arm64
# buildx auto-creates a "docker" driver builder named after the active context.
# That driver builds against the local image store, which is where --load puts
# the images the compose stack then runs; a docker-container builder (often the
# selected one) only ever sees the registry.
LOCAL_BUILDER="$(docker context show)"
# the cdb service's published port, with the dev admin credentials from
# docker-compose.yml embedded -- used by the `fixtures` task
COUCHDB_ADMIN_URL=${COUCHDB_ADMIN_URL:-http://admin:admin@127.0.0.1:5984}

# One buildx invocation per image, spelled once. "$@" carries the flags that
# differ between a local build (--load) and a registry push (--push --platform).
# The build context is docker/, so the dns image can COPY worker/'s lock file
# and s6 services -- that is all the two images share.
_buildx_worker() {
    docker buildx build "$@" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t "${REGISTRY}/desk-worker:${WORKER_VERSION}" \
        -f docker/worker/Dockerfile docker
}

_buildx_dns() {
    docker buildx build "$@" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t "${REGISTRY}/desk-dns:${DNS_VERSION}" \
        -f docker/dns/Dockerfile docker
}

build_worker() {
    _buildx_worker --builder "${LOCAL_BUILDER}" --load
}

build_dns() {
    _buildx_dns --builder "${LOCAL_BUILDER}" --load
}

build() {
    build_worker
    build_dns
}

push() {
    _buildx_worker --push --platform "${PUSH_PLATFORMS}"
    _buildx_dns --push --platform "${PUSH_PLATFORMS}"
}

pull() {
    docker pull "${REGISTRY}/desk-worker:${WORKER_VERSION}"
    docker pull "${REGISTRY}/desk-dns:${DNS_VERSION}"
}

# Load the dev fixture set into the running stack's CouchDB. The fixtures are
# pre-migration documents (no `version` property, `@ip_` map variables), so
# `migrate` has to run after them to bring them to the current document version.
# Rerunnable: CouchDB rejects a PUT over an existing document without its
# current _rev, so each one is looked up first (empty on a fresh database).
fixtures() {
    for f in tests/fixtures/couchdb-*.json; do
        id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["_id"])' "$f")"
        rev="$(curl -fsS -I "${COUCHDB_ADMIN_URL}/desk_drawer/$id" 2>/dev/null \
            | awk -F'"' 'tolower($0) ~ /^etag:/ {print $2}')" || rev=""
        curl -fsS -o /dev/null -X PUT -H 'Content-Type: application/json' \
            --data-binary "@$f" "${COUCHDB_ADMIN_URL}/desk_drawer/$id${rev:+?rev=$rev}"
        echo "  loaded $id"
    done
    docker compose exec -T foreman ./dworker migrate
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
