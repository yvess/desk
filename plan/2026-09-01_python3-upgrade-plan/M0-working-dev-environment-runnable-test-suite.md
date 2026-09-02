# M0 — Working dev environment + runnable test suite

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

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

**Done 2026-09-01.** Notes for later milestones:
- All nine pins re-checked against PyPI at execution time; every one was still
  latest-stable, so the plan's versions were kept verbatim. `requirements-build.txt`
  pins `pyinstaller==6.22.2`.
- Venv lives at repo root `.venv` (Python 3.14.7), added to `.gitignore` together
  with `__pycache__`; dev setup + test invocation documented in `CLAUDE.md`.
- `setup.py` read the version via `__import__('desk').__version__`, which made
  `pip install -e .` fail inside pip's isolated build env (no `httpx` there).
  It now regex-reads `__version__` out of `desk/__init__.py`.
- `desk/tests/test_worker.py` was **deleted**, not ported: every one of its helpers
  went through the removed `CouchdbUploader` / couchdbkit `Server` API and it needed a
  live CouchDB *and* live PowerDNS. Its scenarios (new domain, update/append/delete
  record, two domains) are the spec for the e2e bed M4.5 builds and the
  `test_dns.py` M5.1 restores — recover it from git history (`git show 6c93880:desk/tests/test_worker.py`).
- New tests: `test_utils.py` (21 cases: `AttributeDict`, `ObjectDict`, `parse_date`,
  `calc_esr_checksum`, json helpers, `get_rows`/`get_doc`/`get_key`, and the
  `CouchDBClient`/`CouchDBClientAsync` rev handling — the last is the regression test
  for the `super()._request` fix, mocking only the HTTP boundary via `httpx.MockTransport`);
  `test_imports.py` walks and imports every `desk.*` module, guarding the exact failure
  class that PyPDF2 caused.
- Left alone deliberately (owned by later milestones): `AttributeDict.copy()` and
  `_cast_type` reference `copy` / `warnings` without importing them — latent
  `NameError`s, M6 item 1. `desk/__init__.py` calls `logging.basicConfig(level=DEBUG)`
  at import time, which makes the test run noisy — M6 item 3.
- `CouchDBClientMixin._basic_base_url` defaults to port **80** when the URI carries no
  port, including for `https://` URIs. Harmless today (every caller passes `:5984`),
  worth fixing whenever that area is next touched.
