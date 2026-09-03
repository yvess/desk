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
