# M7 — Standalone dns image, decoupled from the worker image

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

**Planned 2026-09-03** (Fable, with the user). Follows M6; does not touch the M4/M5 runbooks.

## Why

`desk-dns` is built `FROM yvess/desk-worker:${WORKER_VERSION}`. That made sense
when both nodes ran the same code from the same venv, but it couples the two
images the wrong way round: **a PowerDNS update is an alpine bump, and an alpine
bump of the dns image means rebuilding the worker image first** — with its
cairo/pango/fontconfig stack, the C build step for the invoice packages, and
the multi-arch push of both. That has bitten before (master history: pdns
4.0.3 → 4.0.7 "because 4.0.3 has some bugs", 348f1bc), and it will again every
time alpine moves pdns.

The dns node needs almost none of that. Verified on 2026-09-03 by importing
`dworker` with `WORKER_TYPE=worker` and diffing `sys.modules`:

| loaded on a dns node | never loaded on a dns node |
|---|---|
| `desk`, `desk.command`, `desk.utils`, `desk.migrations.*` | `desk.plugin.invoice.*` |
| `desk.plugin.base`, `desk.plugin.dns.*`, `desk.plugin.service.*` | `desk.plugin.extcrm.*` (see the catch below) |
| third-party: **httpx, dnspython, json-diff** (+ httpx's own deps) | CairoSVG, WeasyPrint, pypdf, qrbill, Jinja2, PyMySQL |

Six of the nine pinned requirements are foreman-only, and those six are exactly
what pulls in the shared libraries, the fonts and the build toolchain.

**The one catch: `service-query`.** It is registered for every role, and
`QueryServices.__init__` (`plugin/service/query.py:9`) calls
`get_crm_module`, which imports `plugin/extcrm`, whose `__init__` imports
`todoyu`, which imports `pymysql`. So today a dns node that runs
`dworker service-query` needs PyMySQL. Nothing else on the dns path does.

## Target

Two images that share nothing but the lock file and the s6 layout:

| image | base | python deps | services |
|---|---|---|---|
| `desk-worker` (foreman) | alpine 3.24 | all nine, as today | `worker` |
| `desk-dns` | alpine 3.24 | httpx, dnspython, json-diff | `worker` + `pdns` |

The dns image keeps running the worker (it registers itself, applies
migrations, and serves `dns-check` / `dns-rebuild-powerdns`), so it still needs
python and the `worker`/`worker-init` s6 services. It just stops needing the
invoice stack. Code still comes from the `..:/opt/app` mount in both images —
installing the package into the image is a separate step (see *Follow-up*).

## Steps

Each ends green (`cd desk && python -m unittest discover`).

1. **Gate `service-query` on the foreman.** In `desk/dworker`, move
   `('service-query', QueryServiceCommand)` and its import under `if is_foreman:`,
   next to the two invoice commands. It is a reporting command with no reason to
   run on a nameserver. Regression test: with `WORKER_TYPE=worker` the parser
   rejects `service-query`; with `foreman` it accepts it.

2. **Make `plugin/extcrm` lazy about pymysql.** `plugin/extcrm/__init__.py`
   imports `Todoyu` eagerly, so even the `Dummy` backend drags `pymysql` in.
   Import `todoyu` only inside `get_crm_module` when `worker_extcrm` names it
   (a plain `from desk.plugin.extcrm.todoyu import Todoyu` in that branch; it
   is the only backend), and keep `Dummy` importable without pymysql.
   `test_utils` covers the Dummy branch; add one for the todoyu branch with
   the MySQL connection patched out. The "pymysql is not in `sys.modules`"
   assertion cannot live in `test_utils`: `test_imports.py` imports every
   module in the package, todoyu included, so in-process `sys.modules` is
   already polluted. It goes into the subprocess test of step 3 instead.

3. **Pin the split with a test** (`tests/test_dworker_roles.py` or next to the
   existing entry-point smoke test): run `dworker --help` in a subprocess with
   `WORKER_TYPE=worker` and assert that none of `desk.plugin.invoice`,
   `desk.plugin.extcrm`, `weasyprint`, `cairosvg`, `jinja2`, `pymysql` appear in
   `sys.modules` (print them from a `-c` wrapper). This is the guard that stops
   the dns image from silently regrowing — a new foreman-only import on the
   shared path fails here, not in production.

4. **Two requirement files, one lock.** Add `docker/dns/requirements3.txt`
   with the three dns packages; `docker/worker/requirements3.txt` stays as it
   is. Both images `pip install -r <their file> -c worker/requirements3.lock`,
   so the versions cannot diverge. (`extras_require` in `setup.py` is the
   nicer mechanism, but it only pays off once the package itself is installed
   into the image — see *Follow-up*. Until then a three-line file is the KISS
   answer.) Update `docs/dev-environment.md`: the host venv installs the worker
   file, which is the superset.

5. **Standalone `docker/dns/Dockerfile`.** `FROM alpine:3.24`; `apk add`
   `pdns pdns-backend-sqlite3 sqlite python3 py3-pip bind-tools curl jq
   openssl`; the s6-overlay install block; the venv at `/opt/desk` from the dns
   requirement file — **no `.build-deps` stage**, none of the three packages
   compile anything; `COPY worker/etc /etc` **and** `COPY dns/etc /etc` (the dns
   node still needs the `worker`/`worker-init` services and the shared stage2
   hook); the same `ENV` block as the worker image with `WORKER_TYPE=worker`,
   `WORKER_SUBTYPE=dns`, `EXPOSE 53`. Drop the `ARG WORKER_VERSION`.

   The s6 install block and the `ENV` lines are then spelled out in both
   Dockerfiles. **That is intended** — the whole point is that neither image
   depends on the other, and the repo's rule is explicit repetition over
   config that has to be read across files. A shared "base" image would just
   recreate the coupling one level down. (Duplication is a judgement call:
   *DECISION* flagged below.)

6. **`taskfile.sh`.** `build_dns` loses the `--build-arg WORKER_VERSION` and
   the "needs desk-worker locally" comment; `build` still runs both, but they
   no longer have to run in order; `push` likewise. Bump `DNS_VERSION` (and
   `WORKER_VERSION` for the requirement-file move) — both to `0.5.0`, and the
   three image tags in `docker-compose.yml` with them.

7. **Docs.** `AGENTS.md` Docker section: drop "dns builds FROM worker".
   `docs/upgrade-master-to-python3.md` §5: image tags. The PowerDNS runbook is
   unaffected (it already runs inside the dns container).

## Verification

- `./taskfile.sh build` from a clean cache: the dns image builds **without**
  the worker image present locally (`docker rmi yvess/desk-worker:0.5.0` first).
- `docker image ls`: record both sizes before/after in the tracking table. The
  dns image should lose the cairo/pango/font layers (expect well under half of
  today's size).
- Full stack up: `dig @127.0.0.1 -p 1053 <zone> SOA`, `docker compose exec
  dnsa dworker dns-check` green, `docker compose exec dnsa dworker service-query`
  is rejected by argparse, `docker compose exec foreman dworker service-query`
  still works, `invoices-create` still works on the foreman.
- The pdns-update path this milestone exists for: bump nothing but the alpine
  tag in `docker/dns/Dockerfile`, rebuild **only** `build_dns`, stack still
  serves the zones. That is the acceptance test.
- Suite green, including the new role test from step 3.

## DECISIONS (user, taken 2026-09-03)

- **Dockerfile duplication** (step 5): **accepted.** The s6-overlay block and
  the `ENV` lines are spelled out in both Dockerfiles; no `desk-base` image.
- **`service-query` on dns nodes** (step 1): **foreman-only.** PyMySQL stays out
  of the dns requirement file.

## Explicitly NOT in scope (decided 2026-09-03)

- **A PyInstaller/Nuitka `dworker` binary.** Rejected: musl builds are fragile,
  the multi-arch push would need a per-arch build stage with a full toolchain,
  and the container loses `python3` for debugging. The three dns packages are
  pure Python; a venv is already the lean form.
- **A foreman that builds a binary and a script that deploys it to the dns
  nodes.** Rejected: the foreman image would carry the build toolchain
  permanently, a fresh dns container would have no worker until the script ran
  (an ordering `worker-init` cannot express), and the artifact would drift from
  the image tag. The build-time split above gives the same lean dns image
  deterministically.
- **Config-driven plugin enabling/disabling.** Rejected as speculative
  generality: image size is decided at build time by what is installed, and the
  existing `WORKER_TYPE` role gate already decides what is registered. There is
  no deployment shape where one image serves several roles.

## Follow-up (own milestone, not blocked on this one)

**Install the package into the images** instead of bind-mounting the repo:
`pip install .[dns]` / `.[foreman]` (that is when `extras_require` replaces the
requirement files), a `console_scripts` entry point for `dworker`, `_design/`
as package data resolved next to the package instead of relative to the
working directory (`command.py:111`), and then `PYTHONPATH`, `working_dir` and
the `..:/opt/app` volume disappear from production compose. Dev keeps live
editing through `docker-compose.override.yml`, the mechanism already used for
the Cappuccino checkouts.

## Executed 2026-09-03 (Opus)

All seven steps as written, both decisions as recommended. What the run showed:

- **Sizes: `desk-dns` 238MB → 129MB**, `desk-worker` unchanged at 225MB. The dns
  image lost cairo/pango/fontconfig/ttf-freefont, the six foreman-only packages
  and their transitive C extensions.
- **Independence is proven by construction**: `./taskfile.sh build_dns` produced
  `desk-dns:0.5.0` while no `desk-worker:0.5.0` existed in the local store at
  all. No `.build-deps` stage was needed — all three dns packages ship wheels or
  are pure python (json-diff builds its own wheel from an sdist, no compiler).
- **`ENTRYPOINT ["/init"]` had to be added** to the dns Dockerfile: it used to
  inherit it from the worker image, and nothing in the plan mentioned it. Same
  for `wget`, which the s6-overlay install block uses.
- **`get_crm_module` imports `Todoyu` only in the `worker_extcrm` branch**
  and `Dummy` only in the other, both inside the function, so
  `plugin/extcrm/__init__.py` is down to the `Dummy` import and a dns node
  never loads the extcrm package at all. (A first cut imported the backend
  module by name; the review reverted that to the spec's fixed import — one
  backend exists, and the by-name lookup changed how a capitalised config
  value resolved.)
- **The guard test lives in `tests/test_dworker_roles.py`** (4 tests). It runs
  the real entry point through `runpy` in a subprocess and dumps `sys.modules`
  over stderr behind a `MODULES` marker from an `atexit` hook. Verified it bites: restoring the eager
  `from .todoyu import Todoyu` fails it. An in-process assertion was not an
  option — `test_imports.py` imports every module in the package, todoyu
  included, so `sys.modules` is already polluted by the time it runs.

Verification against a live stack (run under a separate compose project on
shifted host ports, because another checkout's stack held 5984/81):

- `dig` on both nodes answers SOA/NS/A for `test` after
  `dns-rebuild-powerdns`, i.e. httpx + the pdns HTTP API work from the lean image.
- `dworker dns-check` → `2/2 zones match`, exit 0, on `dnsa` **and** `dnsb`.
- `dworker service-query web` on `dnsa`: argparse `invalid choice`, exit 2.
  On `foreman`: exit 0. `invoices-create` on the foreman still loads WeasyPrint
  and runs clean.

**Not an M7 regression, worth knowing:** a zone created through the API is
REFUSED for non-apex names until pdns refreshes its zone cache
(`zone-cache-refresh-interval`, default 300s); `s6-svc -r /run/service/pdns`
clears it immediately. M4 already noted this. `dns-check` surfaces it as an
uncaught `dns.resolver.NoNameservers` traceback rather than a reported failure —
`dnsbase._answers` (`plugin/dns/dnsbase.py:39`) does not catch it. Pre-existing,
left alone.
