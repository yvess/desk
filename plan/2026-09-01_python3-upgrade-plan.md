# Python 3 Full-Upgrade Plan — `desk`

**Date:** 2026-09-01 (rev 3: latest-stable versions everywhere; rev 2 added Docker-wide + CouchDB milestones)
**Branch:** all work happens on `python3` in `/Users/yserrano/src/desk`.
**Planned with:** Fable (this doc). **Executed with:** Opus — therefore every milestone
below is self-contained: it states scope, exact files, verification commands, and
flagged decisions. Do not improvise beyond a milestone's scope; KISS/YAGNI is the
tiebreaker (see `tmp/python-django-best-practices.md` §1.2).

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

*Goal: a fresh Python 3 venv where the package installs, imports, and the test harness runs.
Everything later depends on this.*

1. Replace `desk/docker/worker/requirements3.txt` with the 9-line direct-dependency set from
   `python3-upgrade-analysis.md` §4 (CairoSVG 2.9.0, dnspython 2.8.0, httpx 0.28.1, Jinja2 3.1.6,
   json-diff 1.5.0, PyMySQL 1.2.0, **pypdf** 6.16.2, qrbill 1.2.0, WeasyPrint 69.0 — verified
   installing cleanly on py3.14). These were the latest stable on PyPI on 2026-09-01 —
   per ground rule 6, re-check each against PyPI at execution time and pin whatever is
   latest-stable then. Move `pyinstaller` to a new
   `desk/docker/worker/requirements-build.txt` (used only by `desk/Makefile` `dworker` target).
2. `desk/plugin/invoice/qrbill.py`: PyPDF2 → pypdf (§5.1 — line 9
   `from pypdf import PdfWriter`, line 61 `merger = PdfWriter()`; `.append/.write/.close` unchanged).
   qrbill 0.8.1 → 1.2.0 needs **no code change** (call-site verified, §4).
3. `desk/utils.py:195`: fix `super()._request(...)` → `super().request(...)` (latent bug, §5.2).
4. Fix the test harness:
   - Delete stale `.pyc`/`__pycache__` clutter in `desk/tests/`.
   - `test_worker.py` / `test_utils.py` import the removed `CouchdbUploader` — rewrite or delete
     those test cases so the suite **imports and runs**. Keep any test still testing real code
     (`AttributeDict`, `Powerdns`, …); delete tests of deleted features.
   - Make discovery work from repo root or `desk/` consistently (a `python -m unittest discover`
     invocation documented in CLAUDE.md must pass).

**Verify:** fresh venv → `pip install -r desk/docker/worker/requirements3.txt` succeeds;
`pip install -e .`; `python3 -m compileall desk` exit 0; smoke-import `desk`, `desk.utils`,
`desk.plugin.invoice.qrbill` (this one failed before, on PyPDF2); `python -m unittest discover` green.

---

## M1 — Merge `origin/master` into `python3` (the new invoice/extcrm logic)

*Goal: all business changes from master live on python3. This comes early so later work
never touches stale invoice code.*

Pre-condition: user has committed/stashed the dirty `desk_pad/*.xib` files.

1. `git fetch && git merge origin/master`. Conflicts expected mainly in
   `desk/plugin/invoice/invoice.py`. Resolution rule: **master's business logic wins**
   (addon/included-items start/end dates fb49e67, price-change safeguard 7541c38,
   invoice_ref d01a881, drop empty services/addons d39ba8f), expressed in py3 idioms;
   keep python3-branch plumbing (`get_doc`, requests/httpx style).
   `desk_pad/` conflicts: take master's side verbatim — frontend is deferred, don't hand-edit it.
2. **DECISION (flag to user, do not resolve silently):** commit 75d431b
   *"temp double price for domains, revert it later"* — ask whether to keep or revert now.
3. Tests (same milestone, per best-practices §1.5): add
   `desk/tests/test_invoice.py` with fixture-based regression tests for the merged logic —
   at minimum: addon/included-item start/end-date handling, the price-change safeguard,
   empty services/addons removal, invoice_ref presence. Use dict fixtures shaped like real
   CouchDB docs (see `desk/tests/fixtures/`), no live DB needed —
   `extcrm/dummy.py` exists exactly for this.

**Verify:** merge completed with user doing the final commit; `compileall` clean;
full suite green including new `test_invoice.py`; `git diff origin/master -- desk/plugin` shows
only intentional py3-idiom differences.

---

## M2 — Delete dead code, port the half-ported command layer

*Goal: every CLI command either works on py3 or is gone. ~250 lines deleted.
Reference: `simplification-analysis.md` §2–§3.*

1. Delete outright (grep-verified dead, §2): `desk/plugin/dns/cmd.py`, `desk/tmp/aiotest.py`,
   `DocsProcessor` (`command.py:179-293`), `ImportServiceCommand` (`service/cmd.py`),
   `create_order_doc` + `auth_from_uri` (`utils.py`), `check_domain()` (`powerdns.py`),
   unreachable lines in `AttributeDict.copy()`, commented-out ipdb/print blocks.
2. Add a ~10-line `view(name, **params)` helper to `CouchDBClientMixin` in `desk/utils.py`
   (GET `{db}/_design/{ddoc}/_view/{name}`, returns rows) — with a unit test.
3. Port using it (mechanical, §3.1): `invoices-create` (`invoice/cmd.py` + `invoice.py` —
   **core billing path, highest priority**), `dns-rebuild-powerdns` (`cmd_powerdns.py` —
   needed as the migration/safety tool for both M4 and M5).
4. Replace every `except ResourceNotFound:` (undefined name + wrong model for httpx) with
   status-code checks (`base.py:100`, `command.py`) — §3.2.
5. **DECISIONS (ask user):** `service-query` — port (small) or delete? `migrate` command +
   `desk/migrations/` — delete if all docs are version ≥ 1? `VersionDoc.create_version`
   (broken f-string, only tests call it) — fix or delete?

**Verify:** suite green; `desk/bin` entry points `--help` run without traceback;
`invoices-create` exercised against a dev CouchDB (or, if none available, a test that
mocks only the HTTP boundary with recorded responses); grep confirms no
`ResourceNotFound`, `db.view`, `Server(` references remain.

---

## M3 — Docker: both images + compose, updated and simplified

*Goal: every image builds on a supported base; the compose stack runs with the modern
`docker compose` plugin. Reference: upgrade-analysis §6 for the worker image.*

### 3.1 Worker image (`desk/docker/worker/Dockerfile`)
1. `alpine:3.16` → `alpine:3.24` (latest stable; Python 3.14.7 — the exact Python the
   requirements were verified on). PEP 668 means bare `pip3 install` fails —
   use a venv (KISS: `python3 -m venv /opt/desk`, put it on `PATH`).
   (The analysis verified PEP 668 behavior on 3.22; 3.24 behaves the same.)
2. Drop `binutils`, `upx` (pyinstaller left runtime reqs in M0); drop redundant
   `py3-*` apk pins that pip now resolves (`py3-pillow`, `py3-brotli`, `py3-cffi`,
   `py3-cairosvg`, `py3-jinja2`); keep `pango`, `ttf-freefont`, `openssl`
   (WeasyPrint/CairoSVG runtime libs).
3. s6-overlay `3.0.0.2-2` → `3.2.3.2` (latest stable, 2026-07-16), **both images**, as a
   real migration, not just a version bump: the images run v3 binaries but still use the
   legacy `etc/services.d/` + `etc/cont-init.d/` layout (worker: `services.d`,
   `cont-init.d/05-worker-check`; dns adds `services.d/pdns` with a `down` file and
   `cont-init.d/10-pdns-check`). Follow **`tmp/s6-overlay-setup.md`** exactly:
   - Per service: `s6-rc.d/<name>/` with `run` (shebang `#!/command/with-contenv sh`),
     `type` = `longrun`, `touch dependencies.d/base`.
   - The `START_WORKER` / `START_PDNS` env gating (today: `down` files removed by
     cont-init scripts) moves into an `S6_STAGE2_HOOK` script that `touch`es
     `user/contents.d/<name>` — same pattern as the doc's `START_NUXT`/`START_CRON`.
   - Other `cont-init.d` logic becomes `oneshot` services or stage2-hook lines.
   - Dockerfiles: two-tarball download (`noarch` + `` `arch` ``) **excluding the
     `legacy-cont-init`/`legacy-services` bundles** (doc §1), `ENV PATH="${PATH}:/command"`,
     `ENV S6_STAGE2_HOOK=…`, `S6_BEHAVIOUR_IF_STAGE2_FAILS=2`; keep the raised
     `S6_CMD_WAIT_FOR_SERVICES_MAXTIME` (wait-for-couchdb needs it).
   - The dns image's "wait for couchdb" behavior must survive the conversion — verify it.
   This layout swap is also what lets M3.3 replace the `etc.tar.gz` trick with plain
   `COPY etc/s6-overlay /etc/s6-overlay` (doc §1).
4. Delete the old py2 `requirements.txt` if nothing references it.

### 3.2 DNS image (`desk/docker/dns/Dockerfile`)
1. `alpine:3.14` → `alpine:3.24`, which ships **pdns 5.0.7** (M5's HTTP API is in every
   4.x/5.x). Read the PowerDNS 4.x → 5.0 upgrade notes for `pdns.conf` changes, and note
   the gsqlite3 **schema migrations** between pdns versions — the KISS escape hatch is to
   not migrate the sqlite file at all but re-create zones from CouchDB (the authoritative
   source) via `dns-rebuild-powerdns` (M2). Keep `pdns-backend-sqlite3` — pdns itself
   keeps sqlite as its storage; only the *worker's direct DB access* dies in M5.
2. Re-check the `libgsqlite3backend.so` symlink hack (`Dockerfile:10`) against the new
   alpine pdns package layout — delete it if the package now installs the link correctly.
3. `desk/docker/dns/requirements.txt` — check what uses it (image installs no Python);
   delete if orphaned.

### 3.3 Compose + build tooling (`desk/docker-compose.yml`, `docker-extra.yml`, Makefiles → `taskfile.sh`)
1. Rewrite compose files to the modern spec: `services:` top level, drop `links:`
   (default network + service DNS names replace them; note `worker.sample.conf` uses
   `cdb_1` as hostname — becomes `cdb`), keep the volume/port mappings.
   CouchDB image/config changes happen in **M4**, not here — keep `yvess/couchdb:1.6.1a`
   running in this milestone so M3 stays a pure infra-refresh with unchanged behavior.
2. **Replace both Makefiles with a `taskfile.sh`** (user convention; sample:
   https://github.com/taywa/docker-nuxt/blob/master/taskfile.sh — a plain bash script:
   `set -euo pipefail`, version variable at top, one function per task, `"$@"` dispatch
   at the bottom, `docker buildx` with `` `arch` `` detection, `--load` for local build
   and a `push` function with `--push --platform linux/arm64,linux/amd64`).
   - From `desk/docker/Makefile` carry over as functions: `build_worker`, `build_dns`,
     `build`, `push` — with the `etc.tar.gz` ADD trick replaced by plain `COPY` of the
     s6 tree (doc §1; the dns image's two-source overlay becomes two `COPY` lines).
     Bump image version tags (variables at the top of taskfile.sh, like `NUXT_VERSION`).
   - From `desk/Makefile` carry over only what's alive: `up` (as `docker compose up -d`,
     modern CLI) and — only if the M3.3 pyinstaller DECISION keeps it — `bundle`.
     Everything else is dead 2014-era tooling and is **deleted**: `freeze` (writes to
     `images/dns`/`images/master`, paths that no longer exist), `images` (same),
     `play`/`play-dns`/`play-testdata`/`enter-ansible` (hardcoded `/mnt/sda1` +
     `yvess/ansible-master`, boot2docker era), `stop_worker`/`start_worker` (s6 v2
     paths `/var/run/s6/services`, wrong after step 3's s6-rc migration — the
     replacement is `s6-rc -d/-u change worker` documented in `tmp/s6-overlay-setup.md` §6).
   - One `taskfile.sh` at repo root (or `desk/` — wherever the user runs it from today;
     ask if unclear) is enough; don't create one per directory (KISS).
   - Delete both Makefiles once their live targets are in taskfile.sh.
3. **DECISION (ask user):** is the pyinstaller `dworker` binary still the deployment
   mechanism for the dns hosts, or can the dns image install Python + the package like
   the worker image (simpler: one install path, no pyinstaller at all)? If pyinstaller
   goes, `requirements-build.txt`, `dworker.spec`, and the `bundle` task go with it.

**Verify:** `./taskfile.sh build` succeeds for both images;
`docker compose up` brings up cdb + dnsa/dnsb + foreman with no errors in logs;
`s6-rc -a list` inside each container shows the expected services, and toggling
`START_WORKER`/`START_PDNS` to NO actually keeps them off (the env-gating contract);
inside worker container render one QR-bill invoice PDF end-to-end and eyeball it —
WeasyPrint 56 → 69 is the biggest visual-risk jump in the whole upgrade;
`dig @localhost -p 1053` answers from dnsa.

---

## M4 — CouchDB 1.6.1 → 3.5

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
1. **DECISION (ask user, blocks step 3):** how should `desk_pad` be served once CouchDB
   can't do it — (a) tiny nginx container in the compose stack serving `/opt/app/desk_pad`
   (recommended, ~10 lines), (b) keep it unresolved until the deferred frontend round and
   accept a broken pad in dev? The `_rewrite`-based vhost for `desk_drawer` needs the same
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

## M5 — PowerDNS upgrade: sqlite backend → PowerDNS HTTP API

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

## M6 — Consolidation pass (optional, only if time permits — YAGNI applies)

Reference: `simplification-analysis.md` §4–§6. Each item independent, smallest first:
1. One attr-dict: trim `AttributeDict` to the ~25 used lines or fold `ObjectDict` in;
   fixes the missing-`warnings`-import latent NameError.
2. FQDN helpers: five near-duplicates in `dnsbase.py` → one `to_fqdn`/`from_fqdn` pair
   (+ table of edge-case tests: `@`, trailing dot). Resolves two standing TODOs.
3. `print()` → `logging` (~15 sites); `db_async()` per-call client leak (`__init__.py:36`);
   `MergedDoc.cache` → `functools.lru_cache` or drop.

**Explicitly NOT in scope** (documented decisions, don't do):
- Replacing `json-diff` with DeepDiff — works fine on py3; shim design parked in
  upgrade-analysis §8 if it ever breaks.
- Rewriting `_create_diff` — guarded by tests since M5.1; leave it.

---

## Deferred — frontend (`desk_pad/`, Cappuccino)

Out of scope for this upgrade. Noted for later:
- master's `desk_pad` commits (invoiceRef in client UI 33dbb9c, xcode/cib updates,
  Jakefile deploy) arrive via the M1 merge — taken verbatim, untested here.
- The uncommitted local `*.xib` modifications predate this plan — user handles them.
- **New (from M4):** CouchDB 3.x can no longer serve the pad via `httpd_global_handlers`;
  whatever M4 step 1 decides (nginx or defer) the frontend round inherits the final
  serving story.
- A dedicated frontend update round follows after the backend milestones ship.

---

## Milestone tracking

| # | Milestone | Status | Verified by |
|---|-----------|--------|-------------|
| M0 | Dev env + runnable tests | ☐ | venv install, compileall, unittest green |
| M1 | Merge origin/master | ☐ | test_invoice.py, suite green |
| M2 | Dead code + command ports | ☐ | entry-point smoke, no dead refs |
| M3 | Docker: alpine 3.24 images, compose v2 | ☐ | both images build, compose up, PDF render, dig |
| M4 | CouchDB 1.6.1 → 3.5.2 | ☐ | replication doc counts, worker e2e on couchdb:3.5 |
| M5 | PowerDNS HTTP API | ☐ | zone export diff, dig checks |
| M6 | Consolidations (optional) | ☐ | suite green |

Update this table (and note decisions taken) as milestones complete, so any later
session can pick up from here.
