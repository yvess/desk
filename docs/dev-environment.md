# Development environment

Setting up a checkout for running the tests and the worker outside Docker.

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

## Tests

```bash
cd desk
python -m unittest discover          # run tests (needs the venv on PATH)
./taskfile.sh test                   # the same thing
./coverage.sh                        # tests + HTML coverage report
```

Tests are unit-level and need no CouchDB or PowerDNS. Mock at the HTTP boundary
(`httpx.MockTransport`), not inside `desk`.
