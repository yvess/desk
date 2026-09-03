# M1 — Merge `origin/master` into `python3` (the new invoice/extcrm logic)

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

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

**Done 2026-09-01.** Notes:
- All 10 master commits merged. Conflicts: `desk/plugin/invoice/invoice.py` (one hunk)
  plus 11 `desk_pad/` files, the latter resolved with `git checkout --theirs` per the
  frontend-deferred rule — not hand-edited.
- The invoice.py conflict was master's **refactor** of `add_addons`: the inline
  start/end-date block moved into the new `set_item_period()` helper and the
  `start_date > end_date` guards became a `total != 0.0` filter. Master's side taken
  whole; the python3 branch's duplicate loop dropped.
- py3 idioms re-applied to master's incoming code (ground rule 5): `basestring` → `str`,
  `.iterkeys()`/`.iteritems()` → `.keys()`/`.items()`, no `__future__` imports.
  `git diff origin/master -- desk/plugin/invoice/invoice.py` is now exactly those
  idioms plus the revert below.
- **DECISION TAKEN (user): 75d431b "temp double price for domains" was REVERTED.**
  Both `price *= 2` blocks removed (service price in `get_services`, addon price in
  `add_addons`). Domain services and their addons bill the service-definition price
  again. Nothing else from that commit remains.
- `desk/tests/test_invoice.py` added: 19 tests over the four merged behaviours
  (`set_item_period` clipping/activity, `package_price`/`price_overwritten` incl. the
  empty-price-string case that used to hit `float('')`, empty service/addon removal,
  `invoice_ref`), plus billed-amount checks. Fixtures are plain dicts shaped like
  `service_by_client` view rows; the CouchDB view is the only stub. Each of the four
  behaviours was **mutation-checked** — breaking it in `invoice.py` fails the suite.
- `Invoice.__init__` still calls the undefined `Server(...)` and `db.view(...)`; that
  pre-dates the merge and is M2 step 3's job (`invoices-create`). It is why the tests
  build the `Invoice` object without running `__init__`.
