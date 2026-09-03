# Upgrading a Python 2 installation to the Python 3 version

This is the operator's path from an installation running the `master` branch
(Python 2, CouchDB 1.6.1, PowerDNS 4.x-era, `fig`/`docker-compose` v1) to the
`python3` branch.

It is a **migration, not an in-place upgrade**: the CouchDB data files cannot be
upgraded across 1.x → 3.x, so the new database is filled by replication from the
old one. Plan for the two servers to run side by side for the duration.

Every step below was executed against real servers while the port was done,
including the failure modes quoted in it.

---

## What changes

| | master | python3 |
|---|---|---|
| Python | 2.7, `couchdbkit` + `restkit` | **3.14**, `httpx` (9 direct deps) |
| CouchDB | 1.6.1 (custom `yvess/couchdb` image) | **3.5.2**, official image |
| PowerDNS | 4.x-era, worker writes its **sqlite file directly** | **5.0.7**, worker uses the **HTTP API** |
| `desk_pad` | served by CouchDB (`httpd_global_handlers` + vhost `_rewrite`) | served by **`capi`**, an nginx container |
| Compose | v1 format, `links:` | v2 format, service DNS, healthchecks |
| Build | two `Makefile`s, `etc.tar.gz` | `desk/taskfile.sh` |
| Images | alpine 3.14/3.16, s6-overlay 3.0 | alpine 3.24, s6-overlay 3.2.3.2 |

Two of these change things you have configured by hand: the **`[powerdns]`
section of `worker.conf`** and the **way the frontend is served**. Both are
covered below.

---

## Before you start

- A maintenance window. DNS keeps answering from the existing PowerDNS
  throughout, but the worker is stopped for the CouchDB migration.
- Disk space for a second CouchDB alongside the first.
- Back up: the CouchDB data directory, every
  `/var/services/powerdns/pdns_*.sqlite3`, and every `/etc/desk/worker.conf`.

---

## 1. Migrate CouchDB 1.6.1 → 3.5.2

The data files cannot be upgraded in place, so the new database is filled by
replication from the old one, and the documents are then brought to the current
version with `./dworker migrate`. Three things bite in a fixed order — the design
document has to be installed on the *old* server first, the new server's
replicator needs its session auth disabled, and the source credentials have to be
given explicitly.

**→ [Runbook: CouchDB 1.6.1 → 3.5.2](runbook-couchdb-1.6-to-3.5.md)**, with the
verify script.

## 2. Upgrade the PowerDNS databases

PowerDNS 5.0 will not start on a 4.x-era gsqlite3 schema, and nothing migrates it
for you. The shipped SQL adds the missing columns and — the part that is easy to
miss — gives pre-API zones the `SOA-EDIT-API` metadata row without which their
serials would never move again.

**→ [Runbook: PowerDNS gsqlite3 4.x-era → 5.0](runbook-powerdns-4.x-to-5.0.md)**

## 3. Update `worker.conf`

The `[powerdns]` section changes completely. On every DNS host:

```ini
# master
[powerdns]
backend = sqlite
db      = /var/services/powerdns/pdns_ns1.example.ch.sqlite3
name    = ns1.example.ch
primary = ns1.example.ch

# python3 -- the worker talks to the API instead
[powerdns]
api_url = http://127.0.0.1:8081
api_key = <the api-key from pdns.conf>
```

`name` and `primary` are gone: the SOA primary comes from the domain's template
document, and the worker's own name comes from `[worker] dns = powerdns:<host>`,
which is unchanged.

`[couchdb] uri` must carry credentials — CouchDB 3.x has no admin party. The
other sections (`[worker]`, `[todoyu]`, `[invoice]`, `[service_*]`) are unchanged.

Enable the API in `pdns.conf` on each DNS host:

```
webserver=yes
webserver-address=127.0.0.1
webserver-allow-from=127.0.0.1/32
api=yes
api-key=<a secret>
```

Bind it to the loopback interface: the worker runs on the same host as the
PowerDNS it drives.

> Do **not** set `SOA-EDIT-API` in `pdns.conf`. It is per-zone metadata, not a
> setting, and pdns 5.0 refuses to start on an unknown setting.

## 4. Serve the frontend from `capi`

CouchDB 3.x dropped `httpd_global_handlers`, so it can no longer serve
`desk_pad`, and the design document's `_rewrite` routes are deprecated. A small
nginx container (`capi`) takes both jobs: it serves `desk_pad` and rewrites
`/api/...` onto the design document. Its config is
`desk/docker/capi/conf.d/`, wired up in `docker-compose.yml`.

If you serve the pad from your own nginx instead, copy those three files — the
routes were verified one by one against the old OpenResty config. `_session` and
`_users` must be proxied through as well, or the browser cannot log in against
`require_valid_user`.

## 5. Rewrite `docker-compose.yml`

The shipped `desk/docker-compose.yml` is the reference; this is what changed and
why, so you can port a customised file rather than diff it blind.

**Format.** The file is Compose v2: a top-level `services:` key, environment as a
mapping instead of a `- KEY=value` list. The `fig`-era v1 format the old file
used is no longer read at all.

**`links:` are gone.** Compose's default network resolves service names, so
`links: [cdb]` becomes nothing, and where ordering matters it becomes
`depends_on:`. `foreman` waits for `cdb` to be *healthy*, not merely started:

```yaml
    depends_on:
      cdb:
        condition: service_healthy
```

**`cdb` — the largest change.**

| | master | python3 |
|---|---|---|
| image | `yvess/couchdb:1.6.1a` | `couchdb:3.5.2` |
| admin | `COUCHDB_ADMIN` / `COUCHDB_ADMINPASS` | `COUCHDB_USER` / `COUCHDB_PASSWORD` |
| config | `COUCHDB_LOCAL_HTTPD`, `..._HTTPD_GLOBAL_HANDLERS`, `..._VHOSTS` | a mounted `docker/cdb/local.d/desk.ini` |
| data | under the shared `./var` mount | `./var/couchdb:/opt/couchdb/data` |
| health | — | a healthcheck everything else waits on |

The three `COUCHDB_LOCAL_*` variables have no equivalent: they configured
`httpd_global_handlers` and the `_rewrite` vhost, machinery CouchDB 3.x removed.
That job moves to `capi` (step 4).

Two things that cost real debugging time if you get them wrong:

```yaml
    volumes:
      # NOT :ro -- the image's entrypoint chowns everything under /opt/couchdb
      # under `set -e`, and a read-only mount makes it exit 1 with no log output
      - ./docker/cdb/local.d/desk.ini:/opt/couchdb/etc/local.d/desk.ini
    healthcheck:
      # has to authenticate: require_valid_user makes even /_up return 401
      test: ["CMD-SHELL", "curl -fsS -u \"$$COUCHDB_USER:$$COUCHDB_PASSWORD\" http://localhost:5984/_up"]
      interval: 3s
      timeout: 3s
      retries: 20
```

**`capi` is a new service** — nginx, serving `desk_pad` and rewriting `/api/...`.
See step 4.

**`dnsa` / `dnsb` / `foreman`.**

- Images are pinned: `yvess/desk-dns:0.4.0`, `yvess/desk-worker:0.4.0`.
- New environment: `COUCHDB_HOST` / `COUCHDB_PORT` (they replace the link name),
  `PYTHONPATH: /opt/app` and `working_dir: /opt/app/desk` (the images no longer
  ship a bundled binary, so the package is imported from the mount), and
  **`PDNS_API_KEY`** on the two DNS nodes, which the init scripts template into
  both `pdns.d/pdns.local.conf` and `worker.conf`.
- Hostnames became `ns1.localhost` / `ns2.localhost`, with a matching network
  alias so the name a domain document uses as its nameserver resolves inside the
  stack:

```yaml
    networks:
      default:
        aliases:
          - ns1.localhost
```

  Whatever you use here has to match the `nameservers` in your domain templates,
  or a task's provider matches no worker and orders stall at
  `new_created_tasks`.

- **Publish DNS on both protocols.** The old `"1053:53"` publishes **TCP only** —
  compose defaults the protocol to tcp, so UDP was never reachable from the host,
  which is most DNS traffic. Spell both out:

```yaml
    ports:
      - "1053:53/udp"
      - "1053:53/tcp"
```

**The Cappuccino checkout mounts** are gone from the committed compose file.
They attached to `cdb` before; on a dev host they now attach to `capi` (which is
what serves the pad) through `desk/docker-compose.override.yml` — git-ignored,
and picked up automatically without any `-f` flag. Create it with your own
checkout paths:

```yaml
# Dev-only host paths. desk_pad/Frameworks holds symlinks into /opt/src/..., so
# the Cappuccino checkouts have to be mounted at exactly those paths for capi to
# serve them.
services:
  capi:
    volumes:
      - /{your path}/cappuccino:/opt/src/cappuccino
      - /{your path}/GrowlCappuccino:/opt/src/GrowlCappuccino
      - /{your path}/CouchResource:/opt/src/CouchResource
```

**A production host does not get that file at all**; see the deploy step below.

**Before starting**, check the rendered result:

```bash
docker compose config
```

## 6. Deploy and start

```bash
cd desk
./taskfile.sh build      # or ./taskfile.sh pull
docker compose up -d
```

The Makefiles are gone; `./taskfile.sh help` lists the tasks, and starting or
stopping the stack is plain `docker compose` now that there is a single compose
file.

**The Cappuccino frameworks on a production host.** `desk_pad/Frameworks` is
committed as symlinks into `/opt/src/...`, which only resolve on a dev machine
that has the `cappuccino`, `GrowlCappuccino` and `CouchResource` checkouts
bind-mounted there. A deploy does not mount checkouts: it copies a Cappuccino
**release build** over `desk_pad/Frameworks`, so the directory holds real files
before `capi` starts.

That means a production host needs **no `docker-compose.override.yml`** and
nothing under `/opt/src`. Check it after deploying — a leftover symlink is the
failure mode here, because nginx serves a 404 for every framework and the pad
loads to a blank page:

```bash
find desk_pad/Frameworks -maxdepth 2 -type l   # must print nothing
docker compose config | grep /opt/src          # must print nothing
```

Services are opt-in per container through `START_WORKER` / `START_PDNS`, and the
API key reaches both `pdns.d/pdns.local.conf` and `worker.conf` through the `PDNS_API_KEY`
environment variable.

## 7. Verify

```bash
./dworker dns-check          # asks every nameserver whether the zones match CouchDB
dig @<ns> <zone> SOA         # serial should move after the next change
```

`dns-check` reports `ok`/`FAIL` per zone and a total. It is the check that covers
the whole path — document → worker → PowerDNS → what a resolver actually gets.

---

## Command-line changes

| master | python3 |
|---|---|
| `dworker dns-export-powerdns <db> <dest>` | `dworker dns-export-powerdns <dest>` |
| `dworker dns-rebuild-powerdns <db> [target]` | `dworker dns-rebuild-powerdns [target]` |
| — | `dworker dns-check [domain] [-n NAME=ADDRESS]` |

Both PowerDNS commands lost the sqlite-path argument; they read `[powerdns]
api_url` / `api_key` from the config file instead.

`invoices-create` and `invoices-qrbill` are only registered when
`WORKER_TYPE=foreman` is set in the environment — that has not changed, but it
surprises people running the commands by hand.

## Known gaps

- **The frontend (`desk_pad`) was deliberately not part of this round.** It is
  served and can log in, but the Cappuccino application itself was not revisited.
- `_list`, `_show`, `_update` and design-document `rewrites` are deprecated in
  CouchDB 3.x and **removed in 4.x**. Three places still use them. Not a problem
  for 3.5.2; it is what a future 4.x move has to deal with first.
