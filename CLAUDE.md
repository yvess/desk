# CLAUDE.md

## Git / commits

**The user always makes the commits.** Do not run `git commit` (or `git push`).
Stage changes or leave them in the working tree and let the user review and
commit. The same applies to merges/rebases: resolve conflicts and `git add` the
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

## Tests

```bash
cd desk
python -m unittest discover          # run tests
./coverage.sh                        # tests + HTML coverage report
```
