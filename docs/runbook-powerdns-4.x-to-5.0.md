# Runbook — PowerDNS gsqlite3 schema, 4.x-era → 5.0

One half of [upgrading a Python 2 installation to the Python 3
version](upgrade-master-to-python3.md), split out because it stands on its own —
it applies to any host whose PowerDNS database predates 5.0, whatever else is
being upgraded.

Verified against `yvess/desk-dns:0.4.0` (pdns 5.0.7) with a database built from
the pre-upgrade 2014 schema.

The worker no longer writes PowerDNS's database, but PowerDNS still stores zones
in it, and 5.0 will not start on a 4.x-era schema:

```
PDNSException while filling the zone cache: ... no such column: domains.catalog
```

The database, `sqlite3` and the migration script all live inside the dns
container, so the migration runs from a shell in it. Start one with pdns
switched off (the service is opt-in through `START_PDNS`, so the crash-loop
described at the end does not get in the way), from `desk/`:

```bash
docker compose run --rm -e START_PDNS=NO dnsa sh    # then again for dnsb
```

Inside that shell, `hostname` is the container's (`ns1.localhost`), which is
what the database file is named after:

```bash
cp /var/services/powerdns/pdns_$(hostname).sqlite3{,.bak}
sqlite3 /var/services/powerdns/pdns_$(hostname).sqlite3 \
    < /etc/powerdns/powerdns-upgrade-4.x-to-5.0.sql
exit
```

`/var/services` is the `./var` bind mount, so the migrated database and its
`.bak` are on the host under `desk/var/powerdns/` afterwards.

What it changes, old schema → 5.0:

| table | change |
|---|---|
| `domains` | **+ `options`, + `catalog`** — `catalog` is the column in the error |
| `cryptokeys` | + `published` |
| `records` | `change_date` is no longer read; left in place, harmless |
| indexes | record and comment indexes renamed and made multi-column |

It also writes an **`SOA-EDIT-API = DEFAULT` row per zone** into
`domainmetadata`, and that part is easy to overlook. Zones created *through the
API* are given it automatically; zones that predate the API have no metadata at
all, so their `soa_edit_api` reads back as `''`. Since the worker no longer
maintains SOA serials itself, without that row **nothing would ever bump them** —
an update would change the records and leave the SOA frozen, and secondaries
would never notice. With it, the next worker update moves the serial normally.

Run it once. SQLite has no `ADD COLUMN IF NOT EXISTS`, so a second run reports
`duplicate column name: options` and carries on through the rest; that message is
how you can tell a database was already upgraded.

Migrating this way keeps the existing serials, which is what secondaries
transferring from the host depend on.

**If the zone data is expendable** there is a shorter path — CouchDB is
authoritative, so a fresh database plus a rebuild needs no schema migration:

```bash
rm /var/services/powerdns/pdns_$(hostname).sqlite3   # pdns-init recreates it
# then, once pdns is up again:
./dworker dns-rebuild-powerdns
```

That restarts every serial at today's date, so prefer the schema migration
wherever anything transfers zones from this host.

**Afterwards**, confirm the result with `./dworker dns-check`, which reads every
zone back over DNS and compares it with the CouchDB documents.

## Why this is not automatic

`pdns-init` creates the database when it is missing, but deliberately does not
alter one that already exists — silently rewriting a production zone database at
container boot is not something a start-up script should do. The cost is that a
container with an old database crash-loops on the `domains.catalog` error above
until this runbook is applied.

## Updating PowerDNS itself

PowerDNS comes from the alpine package, so a pdns update is an alpine bump of
the dns image alone -- `desk-dns` shares nothing with `desk-worker`:

```bash
# desk/docker/dns/Dockerfile: raise the alpine tag in the FROM line
cd desk
./taskfile.sh build_dns       # the worker image is not touched
```

Bump `DNS_VERSION` in `desk/taskfile.sh` and the `yvess/desk-dns` tag in
`docker-compose.yml` with it. If the packaged pdns crossed a schema version,
this runbook applies again on the first start.
