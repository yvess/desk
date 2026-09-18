# Python 3 Upgrade — Dependency Analysis

**Date:** 2026-09-01
**Analysed:** `desk-master` @ `master` (py2 baseline) vs `desk` @ `python3` branch (2026-06-15)
**Verification:** all versions checked against live PyPI; blockers test-installed into real Python 3.14 venvs; running container `tdesk-foreman-1` (Python 2.7.12) inspected for actual installed versions.

**No code was changed. Analysis only.**

---

## TL;DR

The hard blocker is already solved. The `python3` branch dropped the entire Python-2-only CouchDB stack and replaced it with `httpx` + `asyncio`.

What remains is maintenance, not migration:

1. `desk/docker/worker/requirements3.txt` no longer installs on any modern Python (verified failing).
2. It is a raw `pip freeze` — 53 lines of which only 9 are direct dependencies.
3. `PyPDF2` is dead upstream — the only genuine code change required.
4. `alpine:3.16` base image is EOL and its bare `pip3 install` will now fail under PEP 668.

Estimated real work: one requirements file, two lines of Python, one Dockerfile.

---

## 1. Baseline: `desk-master` @ `master` (Python 2.7)

`docker/worker/requirements.txt` — 34 pins. Checked every one against PyPI.

### Hard blockers — no Python 3 version exists

| Package | Pinned | Finding |
|---|---|---|
| **couchdbkit** | git master / 0.6.5 | Python-2 only. Last PyPI release 2013-08-30; repo last pushed 2018-07-20. `pip install` on py3 fails: `ModuleNotFoundError: No module named 'imp'`. Imported in **14 files**. |
| **restkit** | 4.2.2 | Py2-only, last release 2013-08-30. Same `imp` failure. Used at `desk/__init__.py:12`. |
| **http-parser** | 0.8.3 | Build fails on py3 (`imp`). Transitive dep of restkit; not imported directly. |
| **socketpool** | 0.5.2 | 0.5.3 *does* install on py3, but exists only to back restkit. `desk/__init__.py:13`. |

These are really one blocker: the `couchdbkit` + `restkit` + `socketpool` + `gevent` connection-pool stack wired together in `desk/__init__.py:32-34`.

No py3 fork exists — checked `couchdbkit-ng`, `couchdbkit3`, `restkit3`: none are on PyPI. Viable replacements would have been `couchdb3` (3.0.4, py3.11+) or `pycouchdb` (1.17.1), but neither provides `Consumer`/`ChangesStream`, so the changes-feed loop would need rewriting.

**→ Superseded. The `python3` branch already did exactly this rewrite by hand. See §2.**

### Delete outright

- `wsgiref==0.1.2` — stdlib since py3. The PyPI package is a 2006 py2 file; install fails with `SyntaxError: Missing parentheses in call to 'print'`. Not imported. Not even present in the running container.
- `argparse==1.2.1` — stdlib. Also absent from the container.
- `pycrypto==2.6.1` — abandoned 2014, known CVEs, not imported. (Note: it *installs* on py3.14 but is broken at import — `NameError: xrange` in `Crypto/Cipher/ARC4.py` — and silently poisons any venv that also has `pypdf`.)
- `Cython` — build-time only.
- `tinycss`, `html5lib`, `CairoSVG`, `cairocffi`, `Pyphen`, `cffi`, `pycparser`, `cssselect` — WeasyPrint/lxml transitive deps, none imported directly. Modern WeasyPrint uses `tinycss2`, not `tinycss`.

### Available on py3, large version jumps

| Package | Pinned | Latest | Note |
|---|---|---|---|
| WeasyPrint | 0.24 | 69.0 | Major API rework |
| Jinja2 | 2.7.3 | 3.1.6 | |
| dnspython | 1.12.0 | 2.8.0 | API rework in 2.x |
| PyMySQL | 0.6.2 | 1.2.0 | |
| gevent | 1.1.1 | 26.8.0 | Moot — removed on `python3` branch |
| lxml | 3.4.0 | 6.1.2 | Moot — removed |
| python-ldap | 2.4.18 | 3.4.7 | Moot — removed |
| paramiko | 1.15.1 | 5.0.0 | Not imported anywhere even on master |

### Unmaintained but working — verified importable on py3.14

- `ezodf` 0.2.5 → 0.3.2 (last release 2015) — installs and imports fine. Moot: the ODS importers were deleted on the `python3` branch.
- `json-diff` 1.3.3 → 1.5.0 (last release 2019) — `Comparator` present and working. Still used at `desk/plugin/base.py:8`.

---

## 2. Current state: `desk` @ `python3` branch

Branch `python3`, HEAD `ab50c63` (2026-06-15), merge `7f3e9e7` from origin/master the same day. Diff vs `origin/master`: **36 files, +705 / -966**.

### What it already accomplished

- `couchdbkit` → hand-rolled `CouchDBClient(httpx.Client)` / `CouchDBClientAsync(httpx.AsyncClient)` in `desk/utils.py:150-200`
- `restkit` + `socketpool` + `gevent` → `httpx` + `asyncio`
- `ezodf` ODS importers deleted (`desk/plugin/dns/importer.py`, `desk/plugin/service/importer.py`)
- `lxml`, `python-ldap`, `paramiko`, `pycrypto`, `ipython`, `ipdb`, `coverage` all dropped
- Added Swiss QR-bill invoicing: `qrbill`, `PyPDF2`, `cairosvg` (`desk/plugin/invoice/qrbill.py`)

**No Python-2-only package remains.** Full third-party import set on the branch:

```
cairosvg, dns.resolver, httpx, jinja2, json_diff, pymysql,
PyPDF2, qrbill, weasyprint
```

### Verification performed

- `python3.14 -m compileall desk` → **exit 0**, all 29 files, zero syntax errors (25 of 29 already carry `from __future__ import ...`).
- Smoke-imported against a modern dep set: `desk.utils`, `desk`, `desk.plugin.base`, `desk.plugin.dns.cmd`, `desk.command`, `desk.plugin.invoice.invoice` all **import cleanly**. Only `desk.plugin.invoice.qrbill` fails, on `PyPDF2`.

---

## 3. Findings against `requirements3.txt`

### 3.1 It does not install on modern Python — verified

`pip install -r requirements3.txt` on Python 3.14 fails:

```
error: subprocess-exited-with-error
KeyError: '__version__'
ERROR: Failed to build 'Pillow' when getting requirements to build wheel
```

Two independent causes:

- **`httpx==0.23.0`** imports `cgi`, removed in Python 3.13 → `ModuleNotFoundError: No module named 'cgi'`
- **`Pillow==9.1.1`** cannot build against current Python

It works only on the pinned `alpine:3.16` (Python 3.10), which is **EOL since May 2024**.

### 3.2 It is a raw `pip freeze` — 53 lines, 9 of them real

Transitive noise that pip resolves on its own:
`anyio`, `certifi`, `charset-normalizer`, `cssselect2`, `defusedxml`, `fonttools`, `h11`, `httpcore`, `idna`, `iso3166`, `MarkupSafe`, `Pillow`, `pycparser`, `pydyf`, `pyphen`, `python-stdnum`, `qrcode`, `rfc3986`, `sniffio`, `svgwrite`, `tinycss2`, `urllib3`, `webencodings`, `Brotli`, `cairocffi`, `xcffib`, `zopfli`

Pure packaging cruft, unused at runtime:
`altgraph`, `appdirs`, `contextlib2`, `more-itertools`, `olefile`, `ordered-set`, `packaging`, `pep517`, `pyparsing`, `retrying`, `six`, `tomli`, `requests`

Build tooling in the wrong file:
`pyinstaller==5.3`, `pyinstaller-hooks-contrib` — used only by `desk/Makefile:54` (`pyinstaller -F -n dworker worker.py`, spec at `desk/dworker.spec`) to build the standalone `dworker` binary. Not needed by the Docker image; it also drags `binutils` and `upx` into the Dockerfile.

### 3.3 Version drift on the packages that matter

| Package | Pinned | Latest | Last release |
|---|---|---|---|
| httpx | 0.23.0 | 0.28.1 | 2026-08-31 |
| WeasyPrint | 56.1 | 69.0 | 2026-06-02 |
| **PyPDF2** | **2.10.4** | **3.0.1 (dead)** | **2022-12-31** |
| qrbill | 0.8.1 | 1.2.0 | 2025-11-05 |
| dnspython | 2.2.1 | 2.8.0 | 2025-09-07 |
| CairoSVG | 2.5.2 | 2.9.0 | 2026-03-14 |
| PyMySQL | 1.0.2 | 1.2.0 | 2026-05-19 |
| Jinja2 | 3.1.2 | 3.1.6 | 2025-03-05 |
| Pillow | 9.1.1 | 12.3.0 | 2026-07-01 |
| json-diff | 1.5.0 | 1.5.0 | 2019-08-25 (already current; upstream dormant) |

---

## 4. Proposed `requirements3.txt`

Nine direct dependencies. **Verified: installs cleanly on Python 3.14**, resolving to 32 packages total.

```
CairoSVG==2.9.0
dnspython==2.8.0
httpx==0.28.1
Jinja2==3.1.6
json-diff==1.5.0
PyMySQL==1.2.0
pypdf==6.16.2
qrbill==1.2.0
WeasyPrint==69.0
```

`pyinstaller` should move to a separate `requirements-build.txt` for the `dworker` Makefile target.

### qrbill 0.8.1 → 1.2.0 is safe

Checked the 1.2.0 signature against the call site at `desk/plugin/invoice/qrbill.py:31-50`. All keywords used — `language`, `account`, `reference_number`, `amount`, `currency`, `due_date`, `additional_information`, `font_factor`, `creditor` — still exist, and `as_svg(file_out, full_page=False)` is unchanged. **No code change needed.**

---

## 5. Code changes required

### 5.1 `desk/plugin/invoice/qrbill.py:9,61` — PyPDF2 → pypdf (required)

`PdfFileMerger` was removed in PyPDF2 3.0. Verified `pypdf.PdfWriter` keeps `append` / `write` / `close` with compatible signatures, so it is a drop-in:

```python
# line 9
from pypdf import PdfWriter        # was: from PyPDF2 import PdfFileMerger
# line 61
merger = PdfWriter()               # was: merger = PdfFileMerger()
```

Lines 62-65 (`.append()`, `.write()`, `.close()`) need no change.

### 5.2 `desk/utils.py:195` — latent bug, pre-existing

```python
class CouchDBClientAsync(httpx.AsyncClient, CouchDBClientMixin):
    async def request(self, *args, **kwargs):
        response = await super()._request(*args, **kwargs)   # <-- _request does not exist
```

`_request` exists in **neither httpx 0.23 nor 0.28** — confirmed by grepping the 0.23.0 sdist (`httpx/_client.py` defines only `request` at lines 761 and 1481). This has never worked.

It does not fire today only because `CouchDBClientAsync` is used exclusively via `.stream()` at `desk/__init__.py:127`, which bypasses `request()`. Any future call to `.request()` or `.rev()` on the async client raises `AttributeError`. Should be `super().request(...)`.

Minor, same area: `self.db_async()` (`desk/__init__.py:36`) constructs a fresh `AsyncClient` per call and never closes it.

---

## 6. Dockerfile — `desk/docker/worker/Dockerfile`

Current base `alpine:3.16` is EOL. Latest Alpine is 3.24; 3.22 is a conservative target.

**Verified on `alpine:3.22`:**
```
Python 3.12.14
PEP668 EXTERNALLY-MANAGED: True
```

So the existing bare `pip3 install -r /tmp/requirements3.txt` (line 30) will now fail with `error: externally-managed-environment`. Needs either a venv or `--break-system-packages`.

Also droppable once `pyinstaller` leaves the runtime requirements: `binutils`, `upx`. And with pip resolving them, the `py3-cairosvg` / `py3-jinja2` / `py3-pillow` / `py3-brotli` / `py3-cffi` apk pins are redundant (though keeping distro binaries can speed builds — judgement call).

Runtime system libs that must stay for WeasyPrint/CairoSVG: `pango`, `ttf-freefont`, `openssl`.

---

## 7. Suggested order of work

1. Replace `requirements3.txt` with the 9-line direct-dependency set (§4); split `pyinstaller` into `requirements-build.txt`.
2. Patch `desk/plugin/invoice/qrbill.py` for `pypdf` (§5.1).
3. Fix `desk/utils.py:195` `_request` → `request` (§5.2).
4. Bump Dockerfile to `alpine:3.22`, add venv or `--break-system-packages`, trim `binutils`/`upx` (§6).
5. Rebuild and exercise the invoice path end-to-end — WeasyPrint 56 → 69 is the largest untested jump, and PDF rendering is the thing most likely to shift visually.

All work belongs in `/Users/yserrano/src/desk` on branch `python3` — **not** the `desk-master` checkout.

Explicitly **not** in scope: replacing `json-diff`. It works on Python 3 as-is. See §8 for the optional later-stage plan.

---

## 8. OPTIONAL (later stage) — replacing `json-diff`

> **Status: OPTIONAL. Not part of the Python 3 upgrade.**
> `json-diff==1.5.0` works correctly on Python 3 — verified below. Nothing here is
> required to complete the upgrade. Defer to a later stage.

### 8.1 Why it is optional

`json-diff` was functionally tested on Python 3.14 against DNS-shaped documents.
All three code paths produce exactly the structure `desk/plugin/base.py` expects:

- `_update` → per-index `_update` with changed fields ✅
- `_append` → new records keyed by index ✅
- `_remove` → removed records keyed by index ✅
- `exclude` list (`_rev`, `state`, `_attachments`, …) filters correctly ✅

It is also already at its latest version — 1.5.0 is both the pin and what PyPI serves.
"Last release 2019" here means finished, not broken.

**The only genuine long-term risk** is `json-diff` breaking on some future Python.
It is ~500 lines of pure Python, so vendoring it into `desk/vendor/` is an afternoon's
work and a far smaller job than a migration.

### 8.2 Why it is not a trivial swap

`Updater._create_diff` (`desk/plugin/base.py:113-180`) is ~70 lines that walk
json-diff's output four levels deep
(`diff['_update'][name]['_update'][i]['_update']`), and use the list index `i`
to look back into `self.service.doc[name][i]`.

The result drives **live DNS record mutations** at
`desk/plugin/dns/powerdns.py:268-292` (`diff['remove']` / `['update']` / `['append']`).
A subtle index-semantics mismatch does not raise — it silently corrupts zones.

**There is currently no test coverage.** `desk/tests/` contains a stale
`test_dns.pyc` with no corresponding `.py`; the source was deleted at some point.

### 8.3 Recommended library, if/when it happens: DeepDiff

Surveyed on maintenance and establishment:

| Package | Latest | Last release | Releases | Stars | Verdict |
|---|---|---|---|---|---|
| **`deepdiff`** | **9.1.0** | **2026-05-15** | **91** | **2524** | ✅ **Recommended** |
| `dictdiffer` | 0.10.0 | 2026-07-16 | 17 | 849 | Maintained, smaller scope |
| `jsondiff` | 2.2.1 | 2024-08-29 | 14 | 748 | Maintained, symbol-based output |
| `jsonpatch` | 1.33 | 2023-06-26 | 42 | 498 | RFC 6902; no exclude support |
| `json-diff` (current) | 1.5.0 | 2019-08-25 | 29 | — | Works; dormant upstream |

**DeepDiff** wins on both axes — by far the most established (2524★, 91 releases) and
actively maintained (released 2026-05-15, repo pushed 2026-08-04, requires Python 3.10+).
Decisively for this use case, its `view='tree'` mode returns structured objects with
`.path(output_format='list')`, `.t1` and `.t2` — so the index positions the existing
logic depends on are available directly, with **no string-path parsing**.

### 8.4 Migration strategy: a shim, not a rewrite

Do **not** rewrite `_create_diff`. Emit the same shape from DeepDiff and leave all
~70 lines of downstream logic untouched. Prototype (verified, see 8.5):

```python
from deepdiff import DeepDiff

EXCLUDE = ['_attachments', 'prev_rev', 'active_rev', 'prev_active_rev', '_rev',
           'state', 'client_id', 'template_id', 'template_type']


def compare_dicts(old_doc, new_doc, exclude=EXCLUDE):
    """Drop-in for json_diff.Comparator(...).compare_dicts()."""
    old = {k: v for k, v in old_doc.items() if k not in exclude}
    new = {k: v for k, v in new_doc.items() if k not in exclude}

    dd = DeepDiff(old, new, view='tree', verbose_level=2, ignore_order=False)
    out = {}

    def slot(name, kind):
        return out.setdefault('_update', {}).setdefault(name, {}).setdefault(kind, {})

    def put_field(name, idx, field, val):
        slot(name, '_update').setdefault(str(idx), {}).setdefault('_update', {})[field] = val

    for kind in ('values_changed', 'type_changes', 'dictionary_item_added'):
        for item in dd.get(kind, []):
            p = item.path(output_format='list')
            if len(p) == 3:                      # ['a', 0, 'value']
                put_field(p[0], p[1], p[2], item.t2)
            elif len(p) == 1:                    # scalar top-level key
                out.setdefault('_update', {})[p[0]] = item.t2

    for item in dd.get('iterable_item_added', []):
        p = item.path(output_format='list')
        if len(p) == 2:
            slot(p[0], '_append')[str(p[1])] = item.t2

    for item in dd.get('iterable_item_removed', []):
        p = item.path(output_format='list')
        if len(p) == 2:
            slot(p[0], '_remove')[str(p[1])] = item.t1

    return out
```

Notes:
- `ignore_order=False` is **essential** — DNS record diffing is positional.
- `verbose_level=2` is required for `dictionary_item_added` to carry values.
- `OptionsClassDiff.include` and `.ignore_append` are always empty in the current
  code, so only `exclude` needs reproducing.

### 8.5 Verification performed

The shim was run head-to-head against `json_diff` on Python 3.14 across 8 cases.
**All 8 produced byte-identical output:**

| Case | Result |
|---|---|
| update, single field changed | PASS |
| update, both key and value changed | PASS |
| append (list grows) | PASS |
| remove (list shrinks) | PASS |
| multi-key (`a` + `mx` both changed) | PASS |
| no change | PASS |
| append + update combined | PASS |
| only excluded keys changed (`_rev`, `state`) | PASS |

**Not verified:** these are synthetic cases, not real fixtures from the CouchDB
database. Nesting deeper than `key → index → field` was not exercised, and neither
were type changes or `null` handling on real documents.

### 8.6 Suggested sequencing, if pursued

1. **First, restore `desk/tests/test_dns.py`** and pin current diff behaviour with
   fixtures captured from real documents. This is worth doing on its own merits —
   the most intricate logic in the codebase is currently unguarded.
2. Add the shim as `desk/plugin/diff.py`, keeping `json-diff` installed.
3. Run both implementations in parallel and log any divergence against live data.
4. Only once divergence is zero over a full billing/DNS cycle, drop `json-diff`.

---

## Appendix — method

- Every package queried against `https://pypi.org/pypi/<name>/json` for latest version, `requires_python`, py3 classifiers, and last upload date.
- Blockers test-installed into throwaway Python 3.14 venvs to distinguish "no py3 release" from "installs but broken".
- httpx 0.23.0 sdist downloaded and `_client.py` grepped to confirm `_request` absence.
- `alpine:3.22` container run to confirm Python version and PEP 668 marker.
- Running `tdesk-foreman-1` container inspected via `pip freeze` to confirm the real py2 baseline (46 packages, Python 2.7.12) — this is how `argparse` and `wsgiref` were confirmed to be no-op lines.
