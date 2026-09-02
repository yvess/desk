# M5 — PowerDNS upgrade: sqlite backend → PowerDNS HTTP API

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

*Goal: `powerdns.py` stops hand-writing SQL against pdns internals and talks the
built-in JSON API. Removes injection hazard, silent-failure `_db()`, hand-rolled SOA
serials, same-host constraint. Reference: `simplification-analysis.md` §1, Option A.*

Pre-conditions: dns image on pdns 5.0.7 (done in M3); `pdns.conf`
(`desk/docker/dns/etc/powerdns/`) gets `webserver=yes`, `api-key=…`, and
`SOA-EDIT-API=INCEPTION-INCREMENT`; settings gain `powerdns_api_url` +
`powerdns_api_key` (replacing `powerdns_backend`/`powerdns_db`). **Confirm with user**
that the production pdns hosts can enable the API webserver before coding.

1. **Tests first:** restore `desk/tests/test_dns.py` (only a stale `.pyc` remains).
   Pin current diff→mutation behavior of `Updater._create_diff` (`base.py`) with fixtures
   captured from real CouchDB domain docs — this logic drives live zone mutations and is
   currently unguarded. Do this against the *old* code before swapping the backend.
2. New `PowerdnsApi` class (sibling of `CouchDBClient`, httpx-based):
   zone CRUD via `POST/DELETE /api/v1/servers/localhost/zones[/{zone}]`; record changes via
   `PATCH …/zones/{zone}` with RRsets `changetype: REPLACE|DELETE` (maps 1:1 onto the current
   del-then-recreate-per-rtype dance); export via `GET …/zones/{zone}/export`.
   MX/SRV prio becomes part of the content string — the `prio` juggling shrinks.
   Serial code (`_calc_serial`/`get_soa_serial`/`update_soa`) is deleted, pdns bumps serials.
   HTTP errors must **raise** — no `_db()`-style swallow.
3. Test `PowerdnsApi` methods against recorded/expected request-response pairs (mock only
   the HTTP boundary); keep the diff-fixture tests from step 1 passing unchanged.
4. Migration/cutover (uses M2's `dns-rebuild-powerdns`, on the M4 test bed): rebuild every
   zone through the API from CouchDB (the authoritative source), then diff
   `dns-export-powerdns` output old-backend vs. new-API before switching the worker over.
5. Remove `powerdns_backend`/`powerdns_db` plumbing; in the dns image drop the
   sqlite-DB-file mount requirement, the `pdns.local.gsqlite3.conf` direct-access bits
   the worker needed, and (if step M3.2 kept it) re-evaluate the symlink hack — pdns
   itself still needs *a* backend, which stays a pdns.conf concern, not the worker's.

**Expected size:** `powerdns.py` 344 → ~150–180 lines.
**Verify:** test suite green; zone rebuild + export diff shows zero record-level differences;
`dig` spot-checks (A/CNAME/MX/TXT-with-quotes — the injection case the old code mishandled)
against the compose dnsa/dnsb containers.

---

**Done 2026-09-02.** Verified against a live PowerDNS **5.0.7** API and the M4
CouchDB 3.5.2 test bed, not from documentation.

**DECISIONS taken (user, 2026-09-02):**
- **Option A, the HTTP API.** The production pdns hosts can run the webserver.
- **The API key comes from the environment**, templated into both files the way
  `COUCHDB_ADMIN`/`COUCHDB_ADMINPASS` already are: `PDNS_API_KEY` →
  `-PDNS_API_KEY-` in `docker/dns/etc/desk/worker.conf` (by `worker-init`) and in
  `docker/dns/etc/powerdns/pdns.d/pdns.local.conf` (by `pdns-init`).
  `docker-compose.yml` carries the dev value.
- **The `_create_diff` gap is fixed, after the swap** — see the last section.

**Correction to the pre-conditions:** `SOA-EDIT-API=INCEPTION-INCREMENT` is *not*
a `pdns.conf` setting — pdns 5.0 rejects it as an unknown setting and refuses to
start. It is per-zone metadata, and the API sets `soa_edit_api` to `DEFAULT` on
every zone it creates, which already produces the YYYYMMDDnn serial the old code
built by hand. Nothing to configure: `pdns.conf` needs only `webserver=yes`,
`api=yes`, `webserver-address=127.0.0.1`, `webserver-allow-from=127.0.0.1/32`
(the worker runs in the same container as its pdns) and the API key.

**1. Tests first** — `desk/tests/test_dns.py` (new). `Updater._create_diff` had
nothing guarding it; seven tests now pin it against the real fixture documents:
value change (`lookup: key`), key change (`lookup: value`), append, the removal
case where json_diff's positional list comparison also reports the shifted tail,
and emptying a type. Written and passing against the *old* backend first.

**2. `Powerdns` on the API** — `desk/plugin/dns/powerdns.py`, rewritten.
- **Named `Powerdns`, not `PowerdnsApi`** (deviation): the backend class is
  resolved by name at runtime from the worker document
  (`desk/__init__.py:94` builds `backend.title()`), so `provides.domain[].backend
  = "powerdns"` requires the class to be `Powerdns`. A separate `PowerdnsApi`
  client class would have been a pass-through layer in front of it; the httpx
  client lives in `Powerdns` and takes an injectable `transport`, which is what
  makes the boundary tests possible.
- Zone CRUD is `POST`/`DELETE /zones[/{zone}]`; record changes are one `PATCH`
  with RRsets. `update()` rebuilds every record type the diff touched — the same
  end state as the old delete-all-then-recreate-per-type dance, atomic per name
  and type, with an explicit `DELETE` for names the document no longer covers.
- `_calc_serial` / `get_soa_serial` / `update_soa` are **gone** (~45 lines); the
  API bumps the serial on every write. Verified: create → `2026090201`, next
  patch → `2026090202`.
- **Every call raises on an error status.** `_db()`'s catch-everything is gone.
- MX/SRV priority is part of the content string, so the `prio` juggling is gone.
- `SOA_FORMAT` had to change: the documents spell the hostmaster
  `dsnmaster@test`, which the API rejects with 422. It is a domain name in the
  SOA, so `soa_mailbox()` turns `a@b` into `a.b.` and the primary gets its root
  dot. The sqlite backend wrote the raw value through and PowerDNS served an
  escaped `dsnmaster\@test.`
- `create()` **syncs** rather than insisting the zone is absent: PowerDNS answers
  a second POST of the same zone with 409, so a task retried after a partial
  failure could otherwise never succeed. It is also what
  `dns-rebuild-powerdns` needs, so the two share one code path.
- `DnsBase` lost the four per-row abstract methods (`add_record`,
  `update_record`, `del_record`, `del_records`) — RRsets are not rows, and
  `Powerdns` is the only implementation.

**3. Boundary tests** — 23 more in `test_dns.py`, all through
`httpx.MockTransport`: what one `create` POSTs (absolute names, apex MX, resolved
`$ip_` map variables, absolute CNAME targets, the SOA mailbox), what `update`
PATCHes, the sync-instead-of-409 path, that an error status raises, and that
`get_records` still produces the shape `dns-export-powerdns` writes.

**4. Cutover check** — both backends rebuilt from the same CouchDB and exported:

```
$ diff export_sqlite.txt export_api.txt   # 16 lines each
$   # identical -- zero record-level differences
```

**5. Plumbing removed** — `powerdns_backend` / `powerdns_db` / the dead
`powerdns_name` / `powerdns_primary` / `powerdns_user` settings, and the `db`
positional argument on both `dns-export-powerdns` and `dns-rebuild-powerdns`
(they read `[powerdns] api_url` / `api_key` from the config now). `DNS_PRIMARY`
left `docker-compose.yml` with them — nothing read it; the SOA primary comes from
the domain's template document. `pdns.local.gsqlite3.conf` **stays**: pdns still
stores zones in sqlite, which is a pdns.conf concern, not the worker's.

**Also changed, and why:** an HTTP error raised inside `_do_task` escaped through
the `_changes` queue coroutine and stopped the worker processing anything
further — the direct consequence of "errors must raise". `desk/__init__.py:103`
now catches `httpx.HTTPError` there, logs it and reports the task failed, so
`_run_tasks` marks the task `error` and the queue keeps running.

**Size:** 327 → 289 lines, but the old file had no docstrings; counting code
only it is **274 → 199**, and **14 SQL string sites → 0**. Short of the plan's
150–180 estimate: `get_records`/`_export_value` reproduce the old export format
exactly (so step 4 could diff), and the record-content builders are explicit.

**The `_create_diff` gap (fixed after the swap, as decided):** `_create_diff`
only read json_diff's `_update` section. A record type absent from the active
document and present in the new one is reported at the *top* level, so it fell
through — the zone was never touched and the task was still marked `done`.
Adding a domain's first TXT record, i.e. an SPF or DKIM entry, was exactly this
case. `desk/plugin/base.py` now also reads the top-level `_append`/`_remove`.
Verified live: a domain with no TXT, changed to carry
`v=spf1 include:_spf.example.ch -all`, now answers that record on `dig`, with its
A records untouched.

**Verified:** suite green, **135 tests**; `compileall` clean.
Against the live stack (CouchDB 3.5.2 + `yvess/desk-dns` with the API on):
order → task → zone through the API; `dig` answers A, CNAME, MX (with priority)
and SOA **without a pdns restart** — which also closes M4's open zone-cache note,
since PowerDNS invalidates its own caches for changes it makes itself;
the export diff above; and the injection case the old code mishandled —
a TXT record containing `O'Brien` is served correctly by the API backend, while
the sqlite backend silently stored **zero** TXT rows for the same document and
still reported the task done.

**Left for later:** `desk/tests/test_dns.py` covers the diff and the backend, not
`DnsValidator` (`dnsbase.py`), which still uses the removed
`dns.resolver.Resolver.query` name and is exercised by nothing.
