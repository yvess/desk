# CLAUDE.md

## Git / commits

**The user always makes the commits.** Do not run `git commit` (or `git push`).
**Do not stage changes on your own** — leave them in the working tree and let
the user review, stage, and commit; run `git add` only when explicitly asked.
The same applies to merges/rebases: resolve conflicts and `git add` the
files if asked, but the user finalizes (`git commit` / `git rebase --continue`).

## Project

`desk` — service data manager. Python package under `desk/`, with plugins in
`desk/plugin/` (e.g. `invoice/`, `extcrm/`, `service/`, `base.py`). Data is
stored in CouchDB; the codebase is mid-migration from `couchdbkit` to plain
`requests` (see helpers like `get_doc`, `encode_json`).

Active work is on the `python3` branch: a Python 2 → Python 3 port. When
resolving conflicts against `master`, prefer the Python 3 idioms
(`.values()` not `.itervalues()`, `print(...)`, f-strings, `get_doc`/`encode_json`)
but keep any newer logic that only exists on `master`.

## Python 3 upgrade — plan & analyses (2026-09)

The full upgrade is planned in **`plan/2026-09-01_python3-upgrade-plan.md`** —
milestones M0–M6 (dev env/tests → merge origin/master → dead-code/command ports →
Docker images+compose → CouchDB 1.6→3.x → PowerDNS HTTP API → optional
consolidation). Work milestone by milestone; each ends with the test suite green.
Supporting analyses:
`tmp/python3-upgrade-analysis.md` (dependencies, verified),
`tmp/simplification-analysis.md` (dead code, PowerDNS API design),
`tmp/python-django-best-practices.md` (cross-cutting parts only: KISS tiebreaker,
regression test with every bug fix, no commented-out code).
Frontend (`desk_pad/`, Cappuccino) is explicitly deferred to a later round.
Update the tracking table at the bottom of the plan as milestones complete.

## Dev environment

Python 3.14, venv at the repo root (git-ignored):

```bash
python3 -m venv .venv
.venv/bin/pip install -r desk/docker/worker/requirements3.txt
.venv/bin/pip install -e .
.venv/bin/pip install coverage       # only for ./coverage.sh
```

`desk/docker/worker/requirements3.txt` holds the 9 direct runtime dependencies.
`requirements-build.txt` (pyinstaller) is build-only and is not installed into
the runtime images.

## Tests

```bash
cd desk
python -m unittest discover          # run tests (needs the venv on PATH)
./coverage.sh                        # tests + HTML coverage report
```

Tests are unit-level and need no CouchDB or PowerDNS. Mock at the HTTP boundary
(`httpx.MockTransport`), not inside `desk`.
