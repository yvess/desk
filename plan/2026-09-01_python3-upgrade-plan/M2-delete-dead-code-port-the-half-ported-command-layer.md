# M2 — Delete dead code, port the half-ported command layer

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

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

**Done 2026-09-02.** Notes:
- **Deleted** (step 1, all grep-verified dead): `desk/plugin/dns/cmd.py`,
  `desk/tmp/aiotest.py`, `DocsProcessor` (`command.py`, ~115 lines),
  `ImportServiceCommand` (`service/cmd.py`, + its `worker.py` import),
  `create_order_doc` / `auth_from_uri` (`utils.py`), `check_domain()`
  (`powerdns.py`), the unreachable tail of `AttributeDict.copy()`, and every
  commented-out debug block (ipdb blocks in `utils.py`, ~10 `# print(...)` in
  `powerdns.py`, `# logging.basicConfig` + `# print` in `__init__.py`,
  `# print(client[...])` in `invoice/cmd.py`). Imports left unused by those
  deletions were dropped too (`os`/`time` in `command.py`, `datetime`/`uuid`
  and the already-unused `asynccontextmanager`/`re`/`urljoin` in `utils.py`,
  `copy`/`logging`/`json` in `base.py`, `os`/`copy` in `powerdns.py`,
  `ast`/`os`/`shutil`/`Todoyu`/`FilesForCouch` in `service/query.py`).
- The `#os.system("pdns_control purge ...")` line under `update_soa`'s
  `# TODO sudoers` became a plain TODO comment — the stale-packet-cache problem
  it names is real until M5 replaces the direct DB writes.
- **`view()` helper (step 2)** lives on `CouchDBClient`, **not** on
  `CouchDBClientMixin` as the plan said: on the mixin it would be inherited by
  `CouchDBClientAsync`, where `self.get()` returns a coroutine and the helper
  would be silently broken. Only sync CLI commands need it. The mixin gained a
  `db_name` attribute (set by `db()`/`db_design()`) so `view(name)` can default
  the design doc to the one named after the database — the only one this project
  installs. Keys/flags go through `encode_view_params` (couchdb wants JSON, not
  `client-1` / `True`), and the helper raises on a non-2xx instead of returning
  `None` rows. 7 tests in `test_utils.py`.
- **Ported (step 3)**, all off `Server(...)`/`db.view("<ddoc>/<view>")`:
  `invoices-create` (`CreateInvoicesCommand` is now a `SettingsCommandDb`;
  `Invoice.__init__` takes the `db` client instead of building a `Server`),
  `dns-rebuild-powerdns` (`.one()` → `rows[0]`; the lookup-map read goes through
  `get_doc`), `migrate`, and `service-query` (`QueryServices(settings, db)`).
  The now-redundant `_cmd()` helpers — which only existed to build couchdbkit's
  `"<ddoc>/<view>"` strings — are gone from all six classes.
- View rows are plain dicts, but `MergedDoc` reads `doc.template_id`, so both
  `Invoice.get_services` and `PowerdnsRebuildCommand._rebuild` now wrap the row
  doc in `AttributeDict` (the worker path got this for free via `get_doc`).
  Without it a templated service/domain doc crashes with `AttributeError`.
- `MigrateCommand.run()` no longer re-calls `self.set_settings(self.settings)`:
  `worker.py` already does that before `run()`, and the second call leaked a
  second httpx client. `InstallDbCommand`/`InstallWorkerCommand` still carry the
  same redundant line — left alone, they are outside this milestone.
- **DECISIONS TAKEN (user):** `service-query` → **ported** (not deleted).
  `migrate` + `desk/migrations/` → **ported** (kept; `to0001` still reachable).
  `VersionDoc` → **deleted** (M0 had already fixed its f-string bug, but nothing
  in the worker path calls it — `Foreman._update_order` does its own
  rev-archiving); `tests/test_base.py` went with it.
- `except ResourceNotFound:` (step 4) is gone: the two in `DocsProcessor` died
  with it, and `Updater.__init__` now checks `map_response.status_code == 200`
  (httpx returns the 404, it never raises) — the `# TODO:fix` there is resolved.
- New `desk/tests/test_commands.py` (15 tests) drives the four ported commands
  through a real `CouchDBClient` over `httpx.MockTransport` — view URLs, JSON
  params, template merging, `to0001`'s document rewrite, the rebuild call order,
  and the `service-query` CSV. Suite is 78 tests.
- Not touched, still owned by later milestones: the `print()` → logging sweep and
  `MergedDoc.cache` (M6), `dns-export-powerdns`/`dns-rebuild-powerdns` still
  taking a sqlite path argument (M5), `_basic_base_url`'s port-80 default (M0 note).
