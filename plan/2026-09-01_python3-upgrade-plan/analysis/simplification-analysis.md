# Codebase Simplification Analysis

**Date:** 2026-09-01
**Analysed:** `desk` @ `python3` branch (HEAD `ab50c63`), 29 Python files, **3,151 lines**
**Companion docs:** `python3-upgrade-analysis.md`, `golang-rewrite-analysis.md`

**No code was changed. Analysis only.**

---

## TL;DR

Realistic reduction potential is roughly **700 lines (~20–25%)**, while removing several
latent crashes. Ranked by value:

1. **Your PowerDNS idea is sound — and the HTTP API variant is even simpler than the CLI variant.** Removes ~150–200 lines of hand-built SQL, the whole serial-management block, an SQL-quoting hazard, and the same-host constraint (§1).
2. **~250 lines of provably dead code** can be deleted today with zero risk (§2).
3. **The command layer is half-unported** — six commands still call the removed couchdbkit API and crash if invoked. Each needs a port-or-delete decision; porting needs one ~10-line `view()` helper (§3).
4. Consolidations: duplicate attr-dict classes, five overlapping FQDN helpers, scattered debug prints (§4–6).

---

## 1. Remove the sqlite PowerDNS backend (your idea) — YES, do it

### 1.1 What the sqlite backend costs today

`desk/plugin/dns/powerdns.py` (344 lines, the largest file in the codebase) hand-builds
SQL strings against PowerDNS's internal schema:

- **Quoting/injection hazard.** Every value is `.format()`-interpolated into SQL
  (`powerdns.py:52,62,113,155-166,180-186,...`). A TXT record containing a quote breaks
  the statement — and SPF/DKIM/DMARC records contain quotes routinely. No parameterised
  queries anywhere.
- **Silent failure.** `_db()` (`powerdns.py:36-49`) catches *all* exceptions, logs, and
  returns the cursor anyway; callers never check the returned `error`. A failed INSERT
  is indistinguishable from success — the task is marked `done` in CouchDB regardless.
- **Hand-rolled SOA serial management.** `_calc_serial` / `get_soa_serial` / `update_soa`
  (~45 lines, `powerdns.py:66-108`) reimplement YYYYMMDDnn serial bumping.
- **Writing behind PowerDNS's back.** Direct DB writes bypass the pdns packet cache —
  which is exactly what the unresolved TODO at `powerdns.py:107-108`
  (`# TODO sudoers / pdns_control purge`) is about. That TODO is disabled, so stale
  answers after updates are possible today.
- **Same-host coupling.** The worker must run where the sqlite file lives
  (`settings.powerdns_db`), and any other backend is a hard crash:
  `raise Exception("can't get database connection")` (`powerdns.py:28`).

### 1.2 Two ways to remove it

**Option A — PowerDNS built-in HTTP API (recommended).**
Enable `webserver=yes` + `api-key=...` in `pdns.conf`. The code then talks JSON over
HTTP — which this worker *already does all day* via `httpx`; a `PowerdnsApi` class would
look like a sibling of `CouchDBClient`.

- Zone CRUD: `POST/DELETE /api/v1/servers/localhost/zones[/{zone}]`
- Records: `PATCH .../zones/{zone}` with RRsets, `changetype: REPLACE | DELETE`
- `update()` maps *better* than today: the current "del_records then recreate per rtype"
  dance (`powerdns.py:286-288`) is exactly RRset-REPLACE semantics, atomic per name/type.
- **Serials disappear entirely:** `SOA-EDIT-API=INCEPTION-INCREMENT` in pdns.conf makes
  PowerDNS bump serials itself — deletes the whole ~45-line serial block.
- MX/SRV special-casing shrinks: API content is `"10 mail.example.ch."` — priority is
  part of the content string, no separate `prio` column juggling
  (`powerdns.py:144-153` simplifies).
- No cache problem: pdns knows about changes it makes; the `pdns_control purge` TODO dies.
- No same-host requirement; no sudoers; the dns worker container no longer needs the
  DB file mounted.
- `dns-export-powerdns` reimplements via `GET .../zones/{zone}/export` (BIND zone format).

**Option B — `pdnsutil` CLI (your original suggestion).**
`pdnsutil create-zone / add-record / replace-rrset / delete-rrset / list-zone /
list-all-zones` via `subprocess`. Also fully backend-agnostic — pdns.conf decides.
Downsides vs. A: keeps the same-host requirement, revives the sudoers question the TODO
already flags, and `get_records`/export mean parsing human-oriented text output instead
of JSON. Choose B only if enabling the API webserver is unacceptable operationally.

**Either way** the backend choice (sqlite / MySQL / Postgres / LMDB) moves into
`pdns.conf`, where it belongs, and `SETTING_KEYS`, `powerdns_backend`, `powerdns_db`
config plumbing all go away.

### 1.3 Estimated effect

| | now | after (API) |
|---|---|---|
| `powerdns.py` | 344 lines | ~150–180 |
| SQL strings | 12 call sites | 0 |
| serial logic | ~45 lines | 0 (SOA-EDIT-API) |
| silent-failure `_db()` | yes | HTTP status checks — real errors |
| same-host constraint | yes | no |

**Caveats (assumptions to confirm):** requires PowerDNS ≥ 4.x with the API enabled
(standard for a decade, but I could not verify the deployed version); zones are NATIVE
(`powerdns.py:114`), which the API handles fine. `test_worker.py` exercises `Powerdns`
directly and would need updating — those tests are currently broken anyway (§3.4).

---

## 2. Dead code — delete today, zero risk (~250 lines)

| What | Where | Evidence |
|---|---|---|
| Whole file: imports only, nothing defined | `desk/plugin/dns/cmd.py` (8 lines) | No class/function/statement after imports; nothing imports this module |
| Whole file: aiohttp experiment | `desk/tmp/aiotest.py` (20 lines) | `aiohttp` is not even a dependency; superseded by the httpx implementation |
| `DocsProcessor` class | `desk/command.py:179-293` (~115 lines) | Zero subclasses/callers — its only users were the importers deleted on this branch. Also internally broken (`ResourceNotFound` undefined) |
| `ImportServiceCommand` | `desk/plugin/service/cmd.py:6-38` (~35 lines) | `run()` references `ImportServices` — **undefined** (importer.py deleted); command no longer registered in `worker.py` |
| `create_order_doc`, `auth_from_uri` | `desk/utils.py:203-220` | Only imported by the dead `dns/cmd.py` |
| `check_domain()` | `desk/plugin/dns/powerdns.py:51-57` | No callers |
| Unreachable lines after `return` | `desk/utils.py` `AttributeDict.copy()` | Dead statements below the return |
| Commented-out debug blocks | `utils.py:258-272` (ipdb blocks), ~10 `# print(...)` in `powerdns.py`, `__init__.py:110` | Noise |
| `MigrateCommand` + `desk/migrations/` | `command.py:152-177` + 71 lines | *Probable* dead: the only migration is `to0001` (the 2014-era `@ip_`→`$ip_` conversion) — if all docs are long since version ≥ 1, delete; it is also broken anyway (§3). **Confirm before deleting.** |

The stray `.pyc` files (`desk/tests/test_dns.pyc` etc.) are untracked local clutter —
`git ls-files` shows zero tracked — but note `test_dns.pyc` is the only remnant of a
deleted test file (see §3.4).

---

## 3. The half-ported command layer — port or delete

The python3 branch fully ported the **daemon** path (Worker/Foreman/changes feeds).
It did **not** port most **CLI commands**: they still call couchdbkit APIs
(`db.view(...)`, `Server(...)`, `db.dbname`, `ResourceNotFound`) that no longer exist.
Each would crash at runtime today:

| Command | Broken by | Decision needed |
|---|---|---|
| `invoices-create` | `Server` undefined (`invoice/cmd.py:58`); `db.view`/`db.dbname` (`invoice.py:31-36,141`) | **Port — this is the core billing path** |
| `service-query` | `Server` undefined (`service/query.py:14`) | Port (small) or delete if unused |
| `dns-rebuild-powerdns` | `db.view(...).one()` (`cmd_powerdns.py:87,112`) | Port — useful ops tool; trivial after §1 |
| `migrate` | `db.view` + bare `db` NameError (`command.py:170,174`) | Probably delete (§2) |
| `install-db`, `install-worker`, `run`, `invoices-qrbill`, `dns-export-powerdns` | — | Already ported and working |

### 3.1 The fix is one helper, not six rewrites

Add to `CouchDBClientMixin` (~10 lines):

```python
def view(self, name, **params):
    # translate couchdbkit-style view call to GET {db}/_design/{ddoc}/_view/{name}
    ...returns rows list
```

after which each broken command is a mechanical 2–5 line change
(`Server(...)`/`get_db` → `CouchDBClient.db(...)`, keep the loop bodies).

### 3.2 `ResourceNotFound` is doubly wrong now

`desk/plugin/base.py:100` and `command.py:232,240` do `except ResourceNotFound:` —
the name is **undefined** (couchdbkit import removed), *and* the model is wrong:
`httpx` does not raise on 404, it returns a response. The `try/except` can never work;
replace with a status-code check. (`base.py:96` already carries `# TODO:fix`.)

### 3.3 `VersionDoc.create_version` is broken and near-dead

`base.py:63` does `self.db.put(f'{old_doc}/{old_doc.rev}', ...)` — f-strings the whole
*dict* into the URL. Only callers are tests. Fix it or delete `VersionDoc`; decide based
on whether the pad/frontend still relies on this revision-archiving flow.

### 3.4 Tests are broken and one is missing

- `test_worker.py:4` / `test_utils.py` import `CouchdbUploader` from `desk.utils` —
  **does not exist** on this branch. The suite cannot even be imported.
- `test_dns.py` was deleted at some point; only its stale `.pyc` remains. As noted in
  the py3 analysis (§8), the diff→DNS-mutation logic is the most intricate code in the
  repo and has **zero coverage**.

Restoring the test suite is arguably a prerequisite for both §1 (PowerDNS backend swap)
and the optional json-diff swap.

---

## 4. Two attribute-dict implementations → one (~-100 lines)

`desk/utils.py` carries both:

- `ObjectDict` (3 lines) — used for settings.
- `AttributeDict` (~110 lines, copied from obspy) — carrying `defaults` / `readonly` /
  `_types` / `warn_on_non_default_key` machinery that **nothing in this codebase uses**.
  Bonus: its warning paths call `warnings.warn(...)` but `warnings` is **never
  imported** (`utils.py:57,120`) — a latent `NameError`.

Trim `AttributeDict` to the ~25 lines actually exercised (attr access, nested-dict
wrapping, MutableMapping protocol), or keep it and fold `ObjectDict` into it. Either
way: one class, no unused machinery, no missing import.

---

## 5. Five overlapping FQDN helpers → one pair

`dnsbase.py` defines `host_to_fqdn`, `cname_key_trans`, `a_key_trans`, `to_fqdn`,
`reverse_fqdn` — five near-duplicate "append/strip domain, handle `@`, handle trailing
dot" functions, plus the same logic inlined *again* inside `DnsValidator._validate`
(marked twice: `# TODO do in host name calc in one place`, `dnsbase.py:28,54`).

One canonical pair — `to_fqdn(name, domain)` / `from_fqdn(fqdn, domain)` — with the
`structure` table referencing it, removes the duplication and both TODOs. This is also
the code most likely to harbour the subtle `@`/trailing-dot edge cases, so consolidating
it shrinks the bug surface, not just the line count.

---

## 6. Smaller items

- **`_create_diff` duplication** (`base.py:127` `# TODO cleanup lot of duplication`)
  and `_create_records` (`powerdns.py:223` `# TODO merge with create logic`) — partly
  addressed by the optional DeepDiff shim (py3 analysis §8); the three near-identical
  update/append/remove blocks can share one extraction helper regardless.
- **Class-level caches**: `MergedDoc.cache` (wipe-all-at-50 dict, `base.py:20-26`) and
  `DocsProcessor.map_cache` (dies with §2). A `functools.lru_cache(maxsize=50)` on
  `get_template` is simpler and correct; or drop caching — the doc volumes are tiny.
- **`print()` → logging** in ~15 places (`qrbill.py:21`, `todoyu.py:85,123,143-144`,
  `query.py:91-94`, `cmd_powerdns.py:125,128`, invoice `cmd.py` progress dots).
- **`db_async()` per-call client leak** (`__init__.py:36`) — already noted in the py3
  analysis; one long-lived client per queue is simpler.
- **`Worker._process_tasks` loop shape** (`__init__.py:57-67`): `provider_lookup` is
  rebuilt per provides-entry and the dispatch `if` sits inside the outer loop — it works
  by accident of data (one service type), but the intended shape is: build the whole
  lookup first, then dispatch once. Review rather than blind-fix.
- `AttributeDict.toJSON` (`utils.py:129`) — no callers; goes with §4.

---

## 7. Suggested order

| Step | What | Effort | Lines | Risk |
|---|---|---|---|---|
| 1 | Delete §2 dead code (confirm `migrate` first) | trivial | ~-250 | none |
| 2 | Add `view()` helper; port `invoices-create` (+ `service-query`, `dns-rebuild`) ; fix `ResourceNotFound` sites | small | ~+15/-30 | low — these commands are broken today, can only improve |
| 3 | Restore tests (`CouchdbUploader` refs, resurrect `test_dns.py`) | medium | +tests | enables 4 |
| 4 | **PowerDNS → HTTP API** (§1, Option A) | medium | ~-170 | medium — needs pdns config change + rebuild-from-CouchDB as safety net (which step 2 just fixed) |
| 5 | Consolidations: attr-dicts (§4), FQDN helpers (§5), caches/prints (§6) | small each | ~-180 | low |

A pleasant property of this ordering: step 2's `dns-rebuild-powerdns` gives you the
perfect migration tool for step 4 — rebuild every zone through the new API from CouchDB
(the authoritative source), then diff `dns-export` output old vs. new before switching.

---

## Appendix — method & caveats

- Every file on the `python3` branch read in full or structurally
  (`desk/` = 3,151 lines total per `wc -l`); dead-code claims are grep-verified
  (no callers / undefined names), not guesses.
- "Broken" claims are static findings (undefined names, methods that don't exist on the
  httpx client). Commands were **not executed** against a live CouchDB/pdns.
- The deployed PowerDNS version and whether its API webserver can be enabled were not
  verified — confirm before committing to §1 Option A.
- Whether `migrate`, `service-query`, and `VersionDoc` are still needed is a product
  decision, not derivable from the code; the tables above flag them as decisions.
