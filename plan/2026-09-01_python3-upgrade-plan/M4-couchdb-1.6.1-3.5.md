# M4 — CouchDB 1.6.1 → 3.5

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

*Goal: the datastore runs a supported CouchDB (3.5.2, latest stable, official image) instead of a
custom 2014-era 1.6.1 image. The worker code path is already close: the python3 branch
talks plain HTTP via httpx and was already fixed for CouchDB 2.3 attachment-rev
semantics (commit d9726b9).*

**Breaking changes that matter here (1.6 → 3.x):**
- Data files are **not** upgradeable in place across 1.x → 3.x; migrate via one-shot
  HTTP **replication** from the old container to the new one.
- `httpd_global_handlers` is gone → the `_desk_pad` static-file serving in
  `docker-compose.yml` **cannot work** on 3.x. `vhosts` + design-doc `_rewrite` still
  exist in 3.x but are deprecated.
- No admin party; every db call needs auth (already the case here: admin/admin env).

**Steps:**
1. **DECISION — effectively answered by the user's `tmp/docker-compose_new.yml`
   (2026-09-01):** it adds an `openresty/openresty` service (`capi`) serving
   `desk_pad`, i.e. option (a), the nginx container. Confirm the detail with the user,
   don't re-open the question. Original wording: how should `desk_pad` be served once
   CouchDB can't do it — (a) tiny nginx container in the compose stack serving
   `/opt/app/desk_pad` (recommended, ~10 lines), (b) keep it unresolved until the
   deferred frontend round and accept a broken pad in dev? The `_rewrite`-based vhost for `desk_drawer` needs the same
   call (still works on 3.x, but deprecated — nginx can take that role too).
2. Grep-audit the worker's CouchDB usage against 3.x: `_changes` feeds
   (`desk/__init__.py`), views (`_design/…/_view`), doc PUT/GET, attachment upload with
   rev (`d9726b9` already handles 2.x+ semantics). Expect little to nothing — but write
   down what was checked.
3. Compose: replace `yvess/couchdb:1.6.1a` with the official `couchdb:3.5.2` image
   (or newer stable at execution time, ground rule 6)
   (`COUCHDB_USER`/`COUCHDB_PASSWORD` env; single-node setup — create `_users` db or set
   `single_node=true`). Port the `[httpd]`-era env-var config that still applies;
   drop what died with 1.x. Wire the step-1 decision in.
4. Migration runbook (write it into this file when done): start old + new side by side,
   replicate `desk_drawer` (+ any other dbs found via `_all_dbs`) old → new, verify doc
   counts match, verify design docs / views build.
5. Load the dev fixture set (`desk/docker/couchdb-testdata.yml` /
   `desk/tests/fixtures/couchdb-*.json`) into a fresh CouchDB 3 and run the worker
   against it — this doubles as the end-to-end test bed M5 needs.

**Verify:** suite green; `docker compose up` with couchdb:3 → worker connects, `_changes`
feed loop runs, `invoices-create` (M2) executes against it, doc counts old vs. new match
after replication; `curl http://admin:…@localhost:5984/desk_drawer` sane.
