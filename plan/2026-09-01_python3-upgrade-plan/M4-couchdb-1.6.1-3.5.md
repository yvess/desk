# M4 — CouchDB 1.6.1 → 3.5

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

*Goal: the datastore runs a supported CouchDB (3.5.2, latest stable, official image) instead of a
custom 2014-era 1.6.1 image. The worker code path is already close: the python3 branch
talks plain HTTP via httpx and was already fixed for CouchDB 2.3 attachment-rev
semantics (commit d9726b9).*

**Landed early, in M3 (2026-09-02)** — do not redo:
- Step 1 (`desk_pad` served by a container instead of CouchDB) and step 3 (the
  official `couchdb:3.5.2` image + single-node config): the user pulled both into
  M3, where `capi` became a stock `nginx` with a `map`+`rewrite` config and later
  gained the `_session`/`_users` routes. The deprecated `vhosts` + `_rewrite`
  entry is gone with them.
- The design-doc JavaScript port (`for each (x in list)` → indexed `for`, five
  views): 3.5 rejects the SpiderMonkey-only form with a `compilation_error`, so
  the stack could not come up without it. Covered by `DesignDocJavascriptTest`.

**What is left here:** steps 2, 4 and 5 — the usage audit, the replication
runbook and the fixture load.

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

---

**Done 2026-09-02.** Steps 2, 4 and 5 executed against real servers
(`couchdb:3.5.2` and the `yvess/couchdb:1.6.1a` image), not from documentation.

## Step 2 — CouchDB usage audit, 1.6 → 3.5.2

Every endpoint the worker and `capi` use was exercised against a live 3.5.2 with
the design doc installed and the dev fixtures loaded. **Nothing needed a code
change.** What was checked, and the result:

| Call site | Endpoint | 3.5.2 |
|---|---|---|
| `utils.CouchDBClient.view` | `GET {db}/_design/{ddoc}/_view/{name}` (+`include_docs`, JSON `key`/`keys`/`startkey`/`endkey`) | works |
| `Worker._setup_worker` | `GET .../_list/list_docs/worker` | works (**deprecated**, see below) |
| `Foreman._update_order` | `PUT .../_update/set-state/{id}`, `.../_update/set-active-rev/{id}` | works (**deprecated**) |
| `capi` `/api/showjson/*` | `GET .../_show/showjson/{id}` | works (**deprecated**) |
| `Worker._create_queue` | `GET {db}/_changes?feed=continuous&heartbeat=30000&since=now&filter={ddoc}/{name}&include_docs=true` | works |
| `capi` feed routes | `GET {db}/_changes?feed=eventsource&filter=...` | works |
| `Foreman._create_tasks` | `GET /_uuids` (server level, via the client's `../_uuids`) | works |
| `Foreman._update_order` | `PUT {db}/{id}/{rev}?rev={rev}` — the active-doc snapshot, an attachment named after the rev | works, reads back byte-identical |
| `utils.response_add_rev` | `ETag` on `HEAD`/`PUT` | present, unweakened |
| `InstallDbCommand` | `PUT {db}/_design/{ddoc}` with `rewrites` (35 entries), 42 views, 5 filters, 3 lists, 4 updates, 1 show | accepted |

**The one real risk is `_list` / `_show` / `_update`.** They are deprecated in
3.x and **removed in CouchDB 4.x**. Three call sites depend on them
(`_setup_worker`, `_update_order`, and `capi`'s `showjson`/`add-editor` routes),
plus the design doc's `rewrites` (also deprecated, and already unused now that
`capi` does the rewriting). This does not block M4 — it is the thing that will
block a future 4.x move, and `rewrites` could be dropped from the design doc
today. Not done here: out of M4's scope, and the frontend round should decide it
together with the `_show`/`_update` routes it still calls.

## Step 4 — migration runbook (1.6.1 → 3.5.2)

Verified by replicating from a populated `yvess/couchdb:1.6.1a` into a fresh
`couchdb:3.5.2`. Three things bite, in this order:

1. **Install the current design doc on the OLD server first.**
   Replication copies `_design/desk_drawer` like any other document, and 3.5.2
   *validates map functions on write*: the pre-M3 design doc fails with
   `{"error":"doc_write_failed","reason":"compilation_error ... 'inspector_items'
   ... Unexpected identifier"}` (`for each`) and **the whole replication aborts**.
   The ported design doc is valid in both engines — verified: it installs on
   1.6.1 and all four rewritten views still build there. So:
   `./dworker install-db -c <config pointing at the 1.6 server>`.
   Filtering design docs out of the replication instead does *not* work: a
   `selector` needs Mango on the source (`changes_req_failed,400`), which 1.6
   predates.
2. **Turn off the replicator's session auth on the NEW server.** 3.x tries cookie
   auth first and 1.6's `_session` closes the connection, giving
   `{"error":"replication_auth_error","reason":"{session_request_failed,...}"}` —
   including when `auth.basic` is supplied. Fix:
   `curl -X PUT -d '"couch_replicator_auth_noop"' \
     "$NEW/_node/_local/_config/replicator/auth_plugins"`
3. **Then replicate**, giving the source credentials explicitly:
   ```
   curl -X POST -H 'Content-Type: application/json' -d '{
     "source": {"url": "http://OLD:5984/desk_drawer",
                "auth": {"basic": {"username": "admin", "password": "admin"}}},
     "target": "desk_drawer"
   }' "$NEW/_replicate"
   ```
   Result on the test corpus: `docs_read 6, docs_written 6,
   doc_write_failures 0`. Attachments — including the rev-named active-doc
   snapshots — come across and read back byte-identical.

4. **Verify.** Run this with `OLD`/`NEW` set to the two credentialed base URLs
   (`OLD=http://admin:admin@old:5984 NEW=http://admin:admin@new:5984 bash verify.sh`):
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   OLD=${OLD:?}
   NEW=${NEW:?}

   echo "doc counts (must match):"
   for db in "$OLD" "$NEW"; do
       curl -fsS "$db/desk_drawer" | python3 -c \
           'import json,sys; d=json.load(sys.stdin); print(" ", d["doc_count"], "docs,", d["doc_del_count"], "deleted")'
   done

   echo "views:"
   views=$(curl -fsS "$NEW/desk_drawer/_design/desk_drawer" | python3 -c \
       'import json,sys; print(" ".join(sorted(json.load(sys.stdin)["views"])))')
   failed=0
   for v in $views; do
       code=$(curl -s -o /dev/null -w '%{http_code}' \
           "$NEW/desk_drawer/_design/desk_drawer/_view/$v?limit=1")
       [ "$code" = 200 ] || { echo "  FAILED $v -> $code"; failed=$((failed + 1)); }
   done
   echo "  $(set -- $views; echo $#) views build, $failed failed"

   echo "other databases on the source (migrate real users separately):"
   curl -fsS "$OLD/_all_dbs" | python3 -c \
       'import json,sys; print("  ", json.load(sys.stdin))'
   curl -fsS "$OLD/_users/_all_docs" | python3 -c \
       'import json,sys; rows=json.load(sys.stdin)["rows"]; u=[r["id"] for r in rows if r["id"].startswith("org.couchdb.user:")]; print("  ", len(u), "user docs:", u)'
   ```
   On the test corpus it prints `6 docs, 0 deleted` twice, `42 views build,
   0 failed`, and `0 user docs`. Real `org.couchdb.user:*` documents have to be
   replicated separately — and do **not** copy `_users/_design/_auth`, 3.x ships
   its own.

## Step 5 — fixtures + end-to-end on 3.5.2

`desk/docker/couchdb-testdata.yml` (the fig-era loader) was deleted in M3, so
loading is now `./taskfile.sh fixtures`: it PUTs `desk/tests/fixtures/couchdb-*.json`
and then runs `dworker migrate`. The fixtures are **pre-migration** documents (no
`version` property, `@ip_web1` map variables), which is what forced the two bug
fixes below.

End-to-end, verified on 3.5.2 with the real images: load fixtures → `migrate` →
create an order → the foreman picks it up off the continuous `_changes` feed,
reads `new_by_editor`, pulls a uuid and creates a task → the dns worker picks the
task off its own `_changes` feed and writes the zone → the foreman sees
`tasks_done`, runs `_update/set-state`, PUTs the rev-named attachment, runs
`_update/set-active-rev` and closes the order. Final state: order `done`,
task `done_checked`, `dns-test2` `active` with `active_rev` and a matching
attachment, and the zone in pdns:

```
blog2.test|A|172.17.1.10      <- $ip_web1 resolved through map-ips
test|NS|ns1.localhost
test|SOA|ns1.localhost dsnmaster@test 2026090200 3600 3600 3600 3600
```

and, after a `s6-svc -r /run/service/pdns` (see the zone-cache note below),
`dig @127.0.0.1 test SOA` and `dig @127.0.0.1 blog2.test A` answer from it.

**DECISION (user, 2026-09-02): the dns nodes keep M3's `ns1.localhost` /
`ns2.localhost`, and the fixtures move to match.** The fixtures named `dnsa.test`
while compose registered the workers as `ns1.localhost`, so a task's `provider`
matched no worker and every order stalled at `new_created_tasks`. `.localhost`
resolves to the loopback address on the developer's own machine with no hosts-file
entry, so the dev stack works out of the box — that beats the RFC 2606 `.test`
tidiness here. Changed: only the fixture template's `nameservers` and
`soa_primary` → `ns1.localhost`. `docker-compose.yml` is untouched, and the `test`
zone's `dnsa`/`dnsb` A records stay as they are — with an out-of-zone nameserver
they are ordinary host records, not glue.

### Verify line — the two commands the milestone names

- **`invoices-create` (M2) against the fixture-loaded 3.5.2.** Runs clean:
  with the fixture set as shipped it queries `client_is_billable`, finds no
  billable client and prints `total 0`. Marking the fixture client
  `is_billable: 1` in the database makes the view return it, the command reads
  the document and reaches the invoice guard, which declines with
  `NOT creating invoice missing extcrm_id`. So the CouchDB side of the command
  — view with `include_docs`, document read — is good on 3.5.2. Producing an
  actual PDF needs a client with `extcrm_id` plus `service`/`service_definition`
  documents and invoice templates, none of which the fixture set has; the QR-bill
  rendering path itself was verified end-to-end in M3.
  Note `invoices-create` is only registered when `WORKER_TYPE=foreman` is in the
  environment (`dworker:11`), not from `[worker] is_foreman` in the config.
- **The worker against the fixture set.** Re-run after the `to0001` change:
  order → task → zone completes, order `done`, `dns-test` `active` with a
  rev-named attachment, and the zone carries `test|NS|ns1.localhost`,
  `test|SOA|ns1.localhost ...`, `blog2.test|A|172.17.1.10`.
- **ETags are strong.** `HEAD` on a document and on the design doc both return a
  bare `"<rev>"` with no `W/` prefix, which is what `utils.response_add_rev`
  relies on.

## Bugs found by running it (fixed here, with regression tests)

1. **dns workers registered `provides.domain[0].name` as the literal
   `-HOSTNAME-`**, so they matched no task and every dns task sat in state `new`.
   `install-worker` runs in `worker-init`, but the `-HOSTNAME-`/`-DNS_PRIMARY-`/
   `-PDNS_DATA-` substitution lived in `pdns-init`, which s6 starts *after* it.
   **Pre-existing, not an M3 regression** — the old `cont-init.d` scripts had the
   same order (`05-worker-check` before `10-pdns-check`). Fixed by moving all of
   `/etc/desk/worker.conf`'s templating into `worker-init`, next to the
   `COUCHDB_*` substitutions it already did; `pdns-init` keeps `/etc/powerdns/*`.
   Covered by `tests/test_container_init.py`, which asserts every placeholder in
   either `worker.conf` is substituted, and substituted *before* the
   `dworker install-worker` line.
2. **`dworker migrate` was a no-op on legacy documents.** It walks the `version`
   view, whose `else { emit(0, doc.type); }` branch was commented out — and
   `FileDesignDocsLoader` strips every line containing `//`, so the branch never
   reached CouchDB at all. Legacy documents have no `version` property, so
   exactly the documents needing migration were invisible. Uncommented. Covered
   by two tests in `DesignDocJavascriptTest`: no commented-out `emit(` anywhere
   in `_design/`, and `version/map.js` emits in both branches.

## Review follow-up 2026-09-02

Actions from `tmp/reviews/2026-09-02_m4-couchdb-code-review.md`.

**DECISION (user, 2026-09-02): `migrate` stamps the version but must not reset
document state.** With the `version` view fixed, `dworker migrate` reaches every
version-less document — and `to0001` forced `state = 'new'` on every `domain`,
which would have turned a migration into a rebuild of every zone in the database.
The stamp stays (the whole database goes to version 1); the `state` reset is
removed. Verified live: a domain document with `state: active` comes out of
`migrate` as `version: 1, state: active`, with the `@ip_` → `$ip_` conversion
still applied. Covered by
`MigrateCommandTestCase.test_the_migration_leaves_the_document_state_alone`.

**Also fixed:** `tests/fixtures/couchdb-design.json` deleted (2014 dump, invalid
JSON, referenced nowhere) and the `fixtures` task's special case for it dropped;
the task is now rerunnable (it looks up the current `_rev` first, so a second run
no longer dies with 409 — verified by running it twice); `COUCHDB_URL` renamed
`COUCHDB_ADMIN_URL` since it carries the dev admin credentials;
`test_container_init.py` matches `s#…#` and `s/…/` alike, so a future
`/`-delimited sed is not reported missing; the `version`-view test now asserts on
the design doc `FileDesignDocsLoader` builds rather than the raw file, which is
where the `//` stripping actually happens.

**Left as-is, with reasons:** the `read()` helper in `test_container_init.py`
(three call sites walking two file sets, not two — it clears the AGENTS.md bar);
the `PDNS_DATA` default spelled in both init scripts (AGENTS.md prefers explicit
repetition over a shared source); and the test docstrings that name the failure
mode they guard — that is what a regression test is for, and §1.4 is not in
CLAUDE.md's binding set. The `_list`/`_show`/`_update`/`rewrites` 4.x removal is
recorded in step 2 and in the plan's Deferred section, not acted on here.

## Noted, not fixed

- ~~**PowerDNS 5.0 caches the zone list at startup**~~ — **resolved in M5.**
  It only bit because the worker wrote PowerDNS's database behind its back; a
  zone created through the API is served immediately, with the cache interval
  left at its 300s default. No setting needed.
- `desk/tests/fixtures/couchdb-design.json` is a 2014 dump of the old design doc,
  is not valid JSON (literal newlines inside strings), and is referenced nowhere.
  Candidate for deletion.
- `_list`/`_show`/`_update`/`rewrites` removal in 4.x — see step 2.

**Verified:** suite green, 103 tests; `compileall` clean; replication 6/6 docs
with 0 write failures and all 42 views building on the target; the full
order → task → zone chain on 3.5.2. Both runbook failure modes reproduced
verbatim against a live 1.6.1: `replication_auth_error` without
`couch_replicator_auth_noop`, and `doc_write_failed / compilation_error` with the
pre-M3 design doc still on the source.
