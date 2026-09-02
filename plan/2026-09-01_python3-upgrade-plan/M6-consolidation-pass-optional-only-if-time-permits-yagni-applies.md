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
