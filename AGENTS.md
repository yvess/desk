# CLAUDE.md

## Git / commits

**The user always makes the commits.** Do not run `git commit` (or `git push`).
**Do not stage changes on your own** — leave them in the working tree and let
the user review, stage, and commit; run `git add` only when explicitly asked.
The same applies to merges/rebases: resolve conflicts and `git add` the
files if asked, but the user finalizes (`git commit` / `git rebase --continue`).

## Style

**Keep it simple.** KISS is the tiebreaker. No abstraction for a need that
does not exist yet, and no helper introduced only to shorten a file.

**Duplicated code: ask before touching it.** Repeated logic in Python is not a
violation. When you think a duplication should be factored out or removed,
ask the user first and leave it as it is until they decide; in reviews, report
it as a judgement call, never as a hard finding.

**YAML keeps explicit repetition.** Config is read top to bottom, so spell it
out: no YAML anchors or `x-` merge blocks in `docker-compose.yml` (services
stay spelled out in full, even when `dnsa`/`dnsb` are near-identical), and the
same for any other YAML file.

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

`desk/docker/worker/requirements3.txt` holds the 9 direct runtime dependencies,
pinned transitively by `requirements3.lock`. Both images install them into a
venv at `/opt/desk` (alpine's python is PEP 668 externally-managed).

## Docker

`desk/taskfile.sh` replaces the old Makefiles -- one function per task,
dispatched by `"$@"`:

```bash
cd desk
./taskfile.sh build          # build_worker then build_dns (dns builds FROM worker)
./taskfile.sh up             # docker compose -f docker-compose.yml -f docker-extra.yml up -d
./taskfile.sh push           # multi-arch push, worker first
./taskfile.sh help           # list the tasks
```

Copy `docker-extra.yml.dist` to `docker-extra.yml` for the host-specific
Cappuccino paths. Services are supervised by s6-overlay v3 (`s6-rc.d`, see
`tmp/s6-overlay-setup.md`) and each is opt-in via `START_WORKER` / `START_PDNS`.

## Tests

```bash
cd desk
python -m unittest discover          # run tests (needs the venv on PATH)
./taskfile.sh test                   # the same thing
./coverage.sh                        # tests + HTML coverage report
```

Tests are unit-level and need no CouchDB or PowerDNS. Mock at the HTTP boundary
(`httpx.MockTransport`), not inside `desk`.
