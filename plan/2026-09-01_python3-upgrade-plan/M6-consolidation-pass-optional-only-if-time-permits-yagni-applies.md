# M6 — Consolidation pass (optional, only if time permits — YAGNI applies)

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

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

**Done 2026-09-02.**

**DECISIONS taken (user, 2026-09-02):**
- **`AttributeDict`: trim the dead machinery only.** `ObjectDict` stays separate
  — folding it in is a deduplication, and a separate call.
- **FQDN helpers: consolidate, with an edge-case test table first.**
- **`DnsValidator`: repair it as an opt-in live check**, rather than delete it —
  see below for what it turned out to be.
- **`_process_tasks`: fix it, with a regression test.**
- Not done, by decision: `MergedDoc.cache` stays as it is.

**1. One attr-dict** — `AttributeDict` **107 → 44 lines**. Deleted `defaults`,
`readonly`, `_types`, `warn_on_non_default_key`, `do_not_warn_on`, `toJSON`,
`_pretty_str`, `_cast_type`, `copy`, `__getstate__`/`__setstate__` — none of it
used anywhere. That removes **two** latent `NameError`s, not one: `warnings` was
never imported (known), and neither was `copy`, so `AttributeDict.copy()` raised
`NameError` for any caller — there were none. Pinned first by two new tests, for
the behaviours the deletion could have broken: surviving a `deepcopy` (which
`MergedDoc` does to every document) and wrapping nested mappings on `update`.

**2. Five FQDN helpers → one pair.** `host_to_fqdn`, `cname_key_trans`,
`a_key_trans` and `to_fqdn` each handled a different subset of the `@` and
trailing-dot cases, so which one a record type happened to name in `structure`
decided whether those cases came out right:

| input | host_to_fqdn | cname_key_trans | a_key_trans | to_fqdn |
|---|---|---|---|---|
| `www` | `www.test` | `www.test` | `www.test` | `www.test` |
| `@` | `test` | **`@.test`** | `test` | **`@.test`** |
| `www.` | `www` | `www` | **`www..test`** | `www` |
| `mail.other.ch.` | `mail.other.ch` | `mail.other.ch` | **`mail.other.ch..test`** | `mail.other.ch` |

Now `to_fqdn(name, domain=None)` / `from_fqdn(name, domain)` (the latter is
`reverse_fqdn`, renamed and with its arguments in the same order as its
counterpart), driven by a table-driven test over every edge case. **Two real
bugs go with the duplication:** an A record whose host is already absolute
(`www.` or an out-of-zone name) produced `www..test`, and a CNAME alias of `@`
produced `@.test`. Both verified fixed at the RRset the backend builds. The two
standing `# TODO do in host name calc in one place` markers in `DnsValidator`
are resolved — that code calls `to_fqdn` now.

**3a. Diagnostic prints → logging** — 7 sites: the two todoyu duplicate-record
warnings, its key-error dump, the two qrbill notices, and the "not creating
invoice, missing extcrm_id" warning. The other **11 `print()` calls are left
alone on purpose**: they are a command's reported output (`service-query`'s
report, `migrate`'s progress, `dns-rebuild-powerdns`'s progress, the invoice
progress dots and totals) or a CLI error raised before logging is configured,
and two test files assert on them through captured stdout.

**3b. `db_async()` "per-call client leak" — not a leak.** One call site,
`__init__.py:135`, inside `async with`, so the client is closed. Nothing to do;
the analysis item is stale.

**3c. `_process_tasks` fixed.** `provider_lookup` was filled *inside* the loop
over `self.provides`, with the dispatch `if` inside it as well and no reset, so
once a provider matched, every further service type dispatched the same task
again. Measured before the fix: `_run_tasks` called **1x / 2x / 3x** for one,
two and three service types. It was correct only because `provides` has exactly
one key (`domain`) today. The lookup is now built once and each task dispatched
once; three tests cover one type, three types, and a provider this worker does
not have.

## `DnsValidator` — repaired, not deleted

It looked like abandoned code. It is not: on `master` it was the **assertion
mechanism of the end-to-end integration suite** — run a real Foreman against a
real CouchDB, then query the actually-running PowerDNS (`lookup` mapping
`dnsa.test`/`dnsb.test` to `127.0.0.1`) to confirm the zone really said what the
document said. `do_check()` checked A/AAAA/MX/CNAME/TXT; `check_one_record` was
paired with `assertRaises(NXDOMAIN)` to prove a renamed record was gone. It was
never called by the worker itself, on master either. **python3 lost those tests
in M0** (`8833a20`), which is what left the class unreachable. It is also the
only reason `dnspython` is a runtime dependency.

Four defects were in the way, not the two that were visible from reading it:
1. `resolver.query` — deprecated in dnspython 2.x (still present in 2.8.0, so it
   would have warned rather than crashed).
2. `is_fqdn` unbound whenever a query returned no answers.
3. `hasattr(self.doc, record_type.lower())` — documents are plain dicts as often
   as `AttributeDict`s, and `hasattr` is False for a dict *key*, so record types
   were silently skipped.
4. **TXT could never have worked**: it asked the apex and compared the record's
   *name*, using `answer_attr='address'`, which TXT rdata does not have — an
   `AttributeError` on any domain with a TXT record. It now asks each record's
   own name and compares the content, reading `.strings`.

A missing record is now an answer of nothing rather than an exception, so a zone
that never got written reports invalid instead of blowing up.

**`dworker dns-check [domain] [-n NAME=ADDRESS ...]`** makes it reachable: it
reads the domain documents from CouchDB, asks every nameserver they name, and
prints `ok`/`FAIL` per zone plus a total. `-n` overrides a nameserver's address
for hosts that cannot resolve the name themselves. Nine unit tests drive it
through a stub resolver, so the suite still needs no CouchDB or PowerDNS.

**Verified live** against a CouchDB 3.5.2 + dns stack, from inside the foreman
container (nameservers resolve through the compose alias):

```
$ ./dworker dns-check
ok   test
ok   test2
2/2 zones match

# change www's address in CouchDB only, leaving the zone alone:
FAIL test
ok   test2
1/2 zones match
```

This is the codified form of the `dig` checks M3-M5 were verified with by hand.

**Explicitly NOT done** (unchanged from the scope above, plus one): DeepDiff,
rewriting `_create_diff`, and `MergedDoc.cache`.

**Verified:** suite green, **145 → 162 tests**; `compileall` clean.
