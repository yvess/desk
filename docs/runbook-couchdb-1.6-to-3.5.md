# Runbook — CouchDB 1.6.1 → 3.5.2

One half of [upgrading a Python 2 installation to the Python 3
version](upgrade-master-to-python3.md), split out because it stands on its own.

The data files **cannot be upgraded in place** across 1.x → 3.x, so the new
database is filled by replication from the old one — plan for the two servers to
run side by side. Verified by replicating a populated `yvess/couchdb:1.6.1a`
into a fresh `couchdb:3.5.2`; the failures quoted below are the ones that
actually came up, in the order they bite.

## 1. Prepare the old server — do this first

CouchDB 3.x **validates map functions when a design document is written**. The
`master` design document uses `for each (x in list)`, a SpiderMonkey-only form
that 1.6 accepted and 3.5 rejects. Replication copies design documents like any
other document, so it aborts on that one:

```
{"error":"doc_write_failed","reason":"compilation_error ... 'inspector_items' ... Unexpected identifier"}
```

The `python3` design document is valid in **both** engines, so install it on the
**old** server before replicating:

```bash
./dworker install-db -c <config pointing at the 1.6 server>
```

Confirm the views still build there (`GET .../_view/<name>?limit=1` → 200).

> Filtering design documents out of the replication instead does not work: a
> `selector` needs Mango, which CouchDB 1.6 predates.

## 2. Replicate to CouchDB 3.5.2

Start the new server, then, **on the new server**, disable the replicator's
session authentication — 3.x tries cookie auth first and 1.6's `_session` closes
the connection, even when credentials are supplied:

```bash
curl -X PUT -d '"couch_replicator_auth_noop"' \
  "$NEW/_node/_local/_config/replicator/auth_plugins"
```

Then replicate, giving the source credentials explicitly:

```bash
curl -X POST -H 'Content-Type: application/json' -d '{
  "source": {"url": "http://OLD:5984/desk_drawer",
             "auth": {"basic": {"username": "admin", "password": "PASSWORD"}}},
  "target": "desk_drawer"
}' "$NEW/_replicate"
```

Check `doc_write_failures` is `0` in the response, then verify. Save this as
`verify.sh` and run it with both credentialed base URLs:

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

```bash
OLD=http://admin:admin@old:5984 NEW=http://admin:admin@new:5984 bash verify.sh
```

The document counts must match, and every view must build — `42 views build,
0 failed` on an untouched database.

The last section lists the source's other databases. `_users` holds the browser
logins: replicate any real `org.couchdb.user:*` documents separately, and do
**not** copy `_users/_design/_auth`; 3.x ships its own.

## 3. Bring the documents to the current version

```bash
./dworker migrate
```

This stamps `version = 1` on every document and rewrites the two types that
changed shape: `@ip_` map variables become `$ip_`, and TXT entries move from
`txt` to `content`. It leaves document *state* alone, so it does not queue every
zone for rebuilding.

Then continue with the rest of the upgrade — PowerDNS, `worker.conf` and the
compose stack — in [upgrade-master-to-python3.md](upgrade-master-to-python3.md).
