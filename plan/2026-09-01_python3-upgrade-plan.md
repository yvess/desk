# Python 3 Full-Upgrade Plan — `desk`

**Date:** 2026-09-01 (rev 3: latest-stable versions everywhere; rev 2 added Docker-wide + CouchDB milestones)
**Branch:** all work happens on `python3` in `/Users/yserrano/src/desk`.
**Planned with:** Fable (this doc). **Executed with:** Opus — therefore every milestone
below is self-contained: it states scope, exact files, verification commands, and
flagged decisions. Do not improvise beyond a milestone's scope; KISS/YAGNI is the
tiebreaker (see `tmp/python-django-best-practices.md` §1.2).

**Milestones:** each milestone's full spec lives in its own file under
`plan/2026-09-01_python3-upgrade-plan/` (linked from the headings below). This file keeps the
shared intro, the deferred items, and the tracking table.

**Source analyses (read before executing a milestone that cites them):**
- `tmp/python3-upgrade-analysis.md` — dependency/version findings, verified on PyPI + py3.14 venvs
- `tmp/simplification-analysis.md` — dead code, half-ported commands, PowerDNS API design
- `tmp/s6-overlay-setup.md` — proven s6-overlay v3 setup from another project: s6-rc.d
  layout, env-var-gated optional services via `S6_STAGE2_HOOK`, v1/v2→v3 migration table.
  **The M3 s6 migration follows this document.**
- `tmp/python-django-best-practices.md` — only the cross-cutting parts apply (this is not Django):
  §1.2 KISS tiebreaker, §1.4 comments describe current code (never history), §1.5 every bug
  fix ships with a regression test in the same change, §7.4 test at real boundaries (fixtures
  from real docs, no mock-heavy tests), §8.7 no commented-out code.

**Ground rules for the executor (Opus):**
1. **Never `git commit` / `git push`** — the user commits. Stage or leave in working tree. (CLAUDE.md)
2. Each milestone must end **green**: `cd desk && python -m unittest discover` passes and
   `python3 -m compileall desk` is clean, before moving on.
3. Every behavior-affecting change gets a test in the same milestone ("improve testing on the go").
4. Prefer deleting code over porting it when nothing uses it. When unsure whether something
   is used, it is a **DECISION** for the user — flagged inline below, don't guess.
5. Python 3 idioms when resolving conflicts: `.values()` not `.itervalues()`, `print(...)`,
   f-strings, `get_doc`/`encode_json` (CLAUDE.md). Keep master's newer business logic.
6. **Latest stable everywhere.** Every pin in this plan (PyPI packages, base images,
   CouchDB, s6-overlay) is the latest stable as verified on 2026-09-01. At execution
   time, re-check each one and bump to whatever is latest-stable then — pins are floors,
   not ceilings. Exception: never move to an alpha/beta/RC.

**Version targets (latest stable, verified 2026-09-01):**
| Component | Now | Target |
|---|---|---|
| Alpine (both images) | 3.14 / 3.16 | **3.24** (ships Python 3.14.7 — same version the deps were verified on) |
| CouchDB | 1.6.1 (custom image) | **couchdb:3.5.2** (official image) |
| PowerDNS (alpine pkg) | 4.x-era | **5.0.7** (alpine 3.24 `pdns`) |
| s6-overlay | 3.0.0.2 | **3.2.3.2** |
| Python deps | pip-freeze from 2022 | 9-line set in M0 (latest PyPI, re-check at execution) |

**Current state (verified 2026-09-01):**
- `python3` branch: py2-only stack already gone (couchdbkit/restkit → httpx). qrbill invoicing is new here.
- `origin/master` has **10 commits not in `python3`** (local `master` is behind origin by these 10).
  Python side: only 4 files — `desk/plugin/invoice/invoice.py` (bulk), `invoice/cmd.py`,
  `extcrm/todoyu.py`, `extcrm/dummy.py`. Rest is `desk_pad/` frontend (deferred, see bottom).
- Test suite is broken at import (`CouchdbUploader` no longer exists): 6 errors, 0 real tests run.
- Working tree has uncommitted modifications to 4 `desk_pad/Resources/*.xib` files —
  **user must commit or stash these before M1's merge.**
- **Infrastructure (all EOL/legacy):**
  - `desk/docker/worker/Dockerfile` — `alpine:3.16` (EOL 2024), bare `pip3 install`
    (breaks under PEP 668), pyinstaller cruft (`binutils`/`upx`).
  - `desk/docker/dns/Dockerfile` — `alpine:3.14` (older still), `pdns` +
    `pdns-backend-sqlite3` + a `libgsqlite3backend.so` symlink hack; no Python — it runs
    the pyinstaller `dworker` binary shipped via the worker etc tarball.
  - Both images pull s6-overlay 3.0.0.2 (current: 3.2.x) and are assembled by
    `desk/docker/Makefile` via `etc.tar.gz` tarball tricks.
  - `desk/docker-compose.yml` — legacy compose **v1** format (top-level services,
    `links:`), runs CouchDB as `yvess/couchdb:1.6.1a` — **CouchDB 1.6.1 is from 2014**,
    unsupported for years. It also (ab)uses CouchDB to serve the `desk_pad` frontend via
    `httpd_global_handlers` + vhost `_rewrite` — machinery that **no longer exists in
    CouchDB 3.x** (see M4).

---

## M0 — Working dev environment + runnable test suite

→ [M0-working-dev-environment-runnable-test-suite.md](2026-09-01_python3-upgrade-plan/M0-working-dev-environment-runnable-test-suite.md)

---

## M1 — Merge `origin/master` into `python3` (the new invoice/extcrm logic)

→ [M1-merge-origin-master-into-python3-the-new-invoice-extcrm-logic.md](2026-09-01_python3-upgrade-plan/M1-merge-origin-master-into-python3-the-new-invoice-extcrm-logic.md)

---

## M2 — Delete dead code, port the half-ported command layer

→ [M2-delete-dead-code-port-the-half-ported-command-layer.md](2026-09-01_python3-upgrade-plan/M2-delete-dead-code-port-the-half-ported-command-layer.md)

---

## M3 — Docker: both images + compose, updated and simplified

→ [M3-docker-both-images-compose-updated-and-simplified.md](2026-09-01_python3-upgrade-plan/M3-docker-both-images-compose-updated-and-simplified.md)

---

## M4 — CouchDB 1.6.1 → 3.5

→ [M4-couchdb-1.6.1-3.5.md](2026-09-01_python3-upgrade-plan/M4-couchdb-1.6.1-3.5.md)

---

## M5 — PowerDNS upgrade: sqlite backend → PowerDNS HTTP API

→ [M5-powerdns-upgrade-sqlite-backend-powerdns-http-api.md](2026-09-01_python3-upgrade-plan/M5-powerdns-upgrade-sqlite-backend-powerdns-http-api.md)

---

## M6 — Consolidation pass (optional, only if time permits — YAGNI applies)

→ [M6-consolidation-pass-optional-only-if-time-permits-yagni-applies.md](2026-09-01_python3-upgrade-plan/M6-consolidation-pass-optional-only-if-time-permits-yagni-applies.md)

---

## Deferred — frontend (`desk_pad/`, Cappuccino)

Out of scope for this upgrade. Noted for later:
- master's `desk_pad` commits (invoiceRef in client UI 33dbb9c, xcode/cib updates,
  Jakefile deploy) arrive via the M1 merge — taken verbatim, untested here.
- The uncommitted local `*.xib` modifications predate this plan — user handles them.
- **New (from M4):** CouchDB 3.x can no longer serve the pad via `httpd_global_handlers`.
  Settled in M3: `capi` (stock nginx) serves the pad and rewrites `/api/...`, and it
  proxies `_session`/`_users` so the pad can still log in.
- **New (from M4's audit):** the pad's `_show`/`_update` routes, the worker's
  `_list`/`_update` calls and the design doc's `rewrites` are all deprecated in
  CouchDB 3.x and **removed in 4.x**. Not a problem for 3.5.2; the frontend round
  should decide their replacement.
- A dedicated frontend update round follows after the backend milestones ship.

---

## Milestone tracking

| # | Milestone | Status | Verified by |
|---|-----------|--------|-------------|
| M0 | Dev env + runnable tests | ☑ done 2026-09-01 | venv install, compileall, unittest green (22 tests) |
| M1 | Merge origin/master | ☑ done 2026-09-01 | test_invoice.py, suite green (55 tests) |
| M2 | Dead code + command ports | ☑ done 2026-09-02 | entry-point smoke, no dead refs, suite green (78 tests) |
| M3 | Docker: alpine 3.24 images, compose v2 | ☑ done 2026-09-02 | both images build, full stack up (incl. capi + couchdb 3.5.2), s6 gating, QR-bill PDF, dig on 1053/2053, suite green (96 tests) |
| M4 | CouchDB 1.6.1 → 3.5.2 | ☑ done 2026-09-02 (review follow-up same day) | usage audit against a live 3.5.2 (no code change needed), 1.6.1→3.5.2 replication 6/6 docs 0 failures + all 42 views build, fixtures→migrate→order→task→zone e2e, `invoices-create` clean, suite green (103 tests) |
| M5 | PowerDNS HTTP API | ☑ done 2026-09-02 | export diff sqlite vs API identical (16/16 lines), dig A/CNAME/MX/SOA with no pdns restart, TXT quoting case fixed, 0 SQL sites left, suite green (135 tests) |
| M6 | Consolidations (optional) | ☑ done 2026-09-02 | AttributeDict 107→44 lines (2 latent NameErrors gone), 5 FQDN helpers→1 pair (2 edge-case bugs fixed), `_process_tasks` dispatched once per service type, DnsValidator repaired + `dworker dns-check` verified live, suite green (162 tests) |

Update this table (and note decisions taken) as milestones complete, so any later
session can pick up from here.
