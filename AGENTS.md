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

## Where things go

**This file is not user documentation.** `CLAUDE.md` is a symlink to
`AGENTS.md`; both are instructions for the agent. Never put material a human is
meant to copy or follow here — config files, setup snippets, runbook steps.
Those belong in `docs/`. This file may mention such a thing in a line or two and
point at the doc that holds it.

- `docs/` — what an operator or developer executes: upgrade runbooks, the
  files they copy, the commands they run.
- `plan/` — decisions, findings and rationale from the milestones. Not runbooks:
  when a milestone produces operator steps, write them into `docs/` and leave a
  pointer behind.

## Project

`desk` — service data manager. Python package under `desk/`, with plugins in
`desk/plugin/` (e.g. `invoice/`, `extcrm/`, `service/`, `base.py`). Data is
stored in CouchDB and reached over plain HTTP with `httpx` (`CouchDBClient` and
helpers like `get_doc`, `encode_json` in `desk/utils.py`); `couchdbkit` is gone.

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

Python 3.14 with a venv at the repo root; setup steps are in
`docs/dev-environment.md`. `desk/docker/worker/requirements3.txt` holds the
direct runtime dependencies, pinned transitively by `requirements3.lock`.

## Docker

`desk/taskfile.sh` replaces the old Makefiles -- one function per task,
dispatched by `"$@"`:

```bash
cd desk
./taskfile.sh build          # both images; they are independent, order is free
./taskfile.sh push           # multi-arch push of both
./taskfile.sh help           # list the tasks
```

Running the stack is plain `docker compose up -d` / `down` / `logs -f` from
`desk/` -- the taskfile only carries what needs more than one command.

On a dev host the Cappuccino checkouts are bind-mounted under `/opt/src` by
`desk/docker-compose.override.yml` (git-ignored, auto-loaded, no `-f`); the file
to copy is in `docs/upgrade-master-to-python3.md`. Production has no override
file -- the deploy copies a release build into `desk_pad/Frameworks` instead.

Services are supervised by s6-overlay v3 (`s6-rc.d`, see
`tmp/s6-overlay-setup.md`) and each is opt-in via `START_WORKER` / `START_PDNS`.

## Tests

`cd desk && python -m unittest discover` (or `./taskfile.sh test`) with the
venv on PATH (see `docs/dev-environment.md`). Tests are
unit-level and need no CouchDB or PowerDNS. Mock at the HTTP boundary
(`httpx.MockTransport`), not inside `desk`.
