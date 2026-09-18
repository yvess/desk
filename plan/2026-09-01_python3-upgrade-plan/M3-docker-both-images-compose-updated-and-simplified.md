# M3 — Docker: both images + compose, updated and simplified

*Part of [2026-09-01_python3-upgrade-plan.md](../2026-09-01_python3-upgrade-plan.md) — read its intro (ground rules, version targets) before executing.*

*Goal: every image builds on a supported base; the compose stack runs with the modern
`docker compose` plugin. Reference: upgrade-analysis §6 for the worker image.*

## 3.1 Worker image (`desk/docker/worker/Dockerfile`)
1. `alpine:3.16` → `alpine:3.24` (latest stable; Python 3.14.7 — the exact Python the
   requirements were verified on). PEP 668 means bare `pip3 install` fails —
   use a venv (KISS: `python3 -m venv /opt/desk`, put it on `PATH`).
   (The analysis verified PEP 668 behavior on 3.22; 3.24 behaves the same.)
2. Drop `binutils`, `upx` (pyinstaller left runtime reqs in M0); drop redundant
   `py3-*` apk pins that pip now resolves (`py3-pillow`, `py3-brotli`, `py3-cffi`,
   `py3-cairosvg`, `py3-jinja2`); keep `pango`, `ttf-freefont`, `openssl`
   (WeasyPrint/CairoSVG runtime libs).
3. s6-overlay `3.0.0.2-2` → `3.2.3.2` (latest stable, 2026-07-16), **both images**, as a
   real migration, not just a version bump: the images run v3 binaries but still use the
   legacy `etc/services.d/` + `etc/cont-init.d/` layout (worker: `services.d`,
   `cont-init.d/05-worker-check`; dns adds `services.d/pdns` with a `down` file and
   `cont-init.d/10-pdns-check`). Follow **`tmp/s6-overlay-setup.md`** exactly:
   - Per service: `s6-rc.d/<name>/` with `run` (shebang `#!/command/with-contenv sh`),
     `type` = `longrun`, `touch dependencies.d/base`.
   - The `START_WORKER` / `START_PDNS` env gating (today: `down` files removed by
     cont-init scripts) moves into an `S6_STAGE2_HOOK` script that `touch`es
     `user/contents.d/<name>` — same pattern as the doc's `START_NUXT`/`START_CRON`.
   - Other `cont-init.d` logic becomes `oneshot` services or stage2-hook lines.
   - Dockerfiles: two-tarball download (`noarch` + `` `arch` ``) **excluding the
     `legacy-cont-init`/`legacy-services` bundles** (doc §1), `ENV PATH="${PATH}:/command"`,
     `ENV S6_STAGE2_HOOK=…`, `S6_BEHAVIOUR_IF_STAGE2_FAILS=2`; keep the raised
     `S6_CMD_WAIT_FOR_SERVICES_MAXTIME` (wait-for-couchdb needs it).
   - The dns image's "wait for couchdb" behavior must survive the conversion — verify it.
   This layout swap is also what lets M3.3 replace the `etc.tar.gz` trick with plain
   `COPY etc/s6-overlay /etc/s6-overlay` (doc §1).
4. Delete the old py2 `requirements.txt` if nothing references it.

## 3.2 DNS image (`desk/docker/dns/Dockerfile`)
1. `alpine:3.14` → `alpine:3.24`, which ships **pdns 5.0.7** (M5's HTTP API is in every
   4.x/5.x). Read the PowerDNS 4.x → 5.0 upgrade notes for `pdns.conf` changes, and note
   the gsqlite3 **schema migrations** between pdns versions — the KISS escape hatch is to
   not migrate the sqlite file at all but re-create zones from CouchDB (the authoritative
   source) via `dns-rebuild-powerdns` (M2). Keep `pdns-backend-sqlite3` — pdns itself
   keeps sqlite as its storage; only the *worker's direct DB access* dies in M5.
2. Re-check the `libgsqlite3backend.so` symlink hack (`Dockerfile:10`) against the new
   alpine pdns package layout — delete it if the package now installs the link correctly.
3. `desk/docker/dns/requirements.txt` — check what uses it (image installs no Python);
   delete if orphaned.

## 3.3 Compose + build tooling (`desk/docker-compose.yml`, `docker-extra.yml`, Makefiles → `taskfile.sh`)

**Starting point (added by the user 2026-09-01): `tmp/docker-compose_new.yml` and
`tmp/etc/`** — a partially-upgraded compose file plus sample CouchDB and nginx configs.
Use them as the base for this milestone rather than rewriting from the old one. What
they already bring: modern `services:` top level, official `couchdb:2.3` image with
the `/opt/couchdb/{data,etc/local.d}` volume layout, `tmp/etc/couchdb/local.d/*.ini`
(single-node `[cluster] n = 1`, `require_valid_user`, admin hash), and — significant
for **M4 step 1** — a `capi` service serving `desk_pad` and the Cappuccino frameworks
from nginx, i.e. it already takes option (a) of that decision.

Still to do on the compose file here: drop `links:`, pin the CouchDB image per M4 (it
targets 3.5.2, not 2.3), replace the host-absolute `/opt/src/...` and `~/src/desk`
volume paths with relative ones, and re-check the `COUCHDB_LOCAL_VHOSTS` `_rewrite`
entry (deprecated on 3.x — `capi` can take that role too).

**DECIDED 2026-09-01 (user): `capi` runs stock `nginx`, not OpenResty — and needs no
scripting module at all.** The user asked whether njs (nginx's own JS engine) could
replace the Lua. It could — `ngx_http_js_module` is packaged as `nginx-mod-http-js`
in alpine 3.24 (nginx 1.30.4) — but it is unnecessary here: every function in the
`rewrite_by_lua_block` (`list_docs`, `list_items`, `show`, `update`, `couchdb`,
`changes_stream`) was a pure URI/query-string rewrite with no I/O, state, or logic.
A plain `map` + `rewrite` config reproduces all 18 routes.

That config is written and **verified route-by-route** against `nginx:1.27-alpine`
with a stub upstream echoing the proxied URI — all 18 routes byte-identical to the
Lua output. It was drafted in `tmp/etc/nginx/conf.d/` and **now lives in
`desk/docker/capi/conf.d/`** (tracked): `desk.conf` (maps + locations),
`desk_proxy.inc` (shared proxy headers), `desk_changes.inc` (the SSE `_changes`
rewrite). The OpenResty original was kept beside the draft as
`desk.conf.openresty` as a behavioral reference, and deleted with the rest of
`tmp/etc/nginx/` once M3 landed (see the review follow-up below).
Notes carried into M3:
- Rewrite replacements that build their own query string **must end in `?`**,
  otherwise nginx re-appends the client's original args (this silently produced
  `include_docs=true&limit=10&limit=10` and `since=now&since=now` in the first draft).
- Unknown collection names now `return 404` (via a `map` defaulting to `""`) where the
  Lua passed them through to CouchDB unrewritten. Tighter, and matches what the
  frontend actually calls; confirm that is wanted.
- `proxy_read_timeout 60` is inherited from the OpenResty config and applies to the
  SSE `_changes` feeds too, so they drop and the browser's `EventSource` reconnects
  every 60s. Pre-existing behavior, kept for parity — worth raising for the feed
  locations while M3 is open.
- `_show`/`_update` are not method-gated (the Lua gated them to GET/PUT). A wrong
  method now rewrites and lets CouchDB reject it instead of passing the raw
  `/api/...` path through; both end in an error, so this is cosmetic.

**Escape hatch if the config stops being readable (user, 2026-09-01):** do not
defend the pure-config version past the point where it is clear — fall back to a
JS engine in nginx. Verified on `alpine:3.24`, in order of cost:

1. **njs, default engine** — `apk add nginx-mod-http-js` (njs **0.9.9**, nginx
   1.30.4). Stock image plus one package, no build. The Lua ports near 1:1:
   `ngx.req.set_uri` → `r.internalRedirect`, `ngx.req.get_uri_args` → `r.args`.
   This is the first fallback.
2. **njs with the QuickJS engine** (`js_engine qjs`, njs ≥ 0.8.6) — gives full
   modern JS instead of the njs subset, but **alpine's package is not built for
   it**: `js_engine qjs` is rejected with `invalid value "qjs"`, and the module
   links no quickjs library. Alpine ships `quickjs`/`quickjs-ng` (+`-dev`)
   separately, so this means compiling the module yourself — a custom image,
   which is what dropping OpenResty was meant to avoid. Only worth it if the
   rewrite logic ever needs real language features; a URI rewriter does not.

**Tripwire — switch to njs when any of these becomes true.** Today's config sits
well inside them (3 maps, 9 locations, 2 `if`s, both the documented-safe
`return` / `rewrite ... break` forms):
- a route needs logic beyond "match a path, look up a name, rewrite" — anything
  touching a request or response *body*, or branching on an upstream reply;
- a location needs more than one `if`, or a nested one;
- a `map` stops being a flat lookup and wants string manipulation;
- location count passes ~12, where the order-dependence stops being obvious from
  reading the file top to bottom.

1. Rewrite compose files to the modern spec: `services:` top level, drop `links:`
   (default network + service DNS names replace them; note `worker.sample.conf` uses
   `cdb_1` as hostname — becomes `cdb`), keep the volume/port mappings.
   CouchDB image/config changes happen in **M4**, not here — keep `yvess/couchdb:1.6.1a`
   running in this milestone so M3 stays a pure infra-refresh with unchanged behavior.
2. **Replace both Makefiles with a `taskfile.sh`** (user convention; sample:
   https://github.com/taywa/docker-nuxt/blob/master/taskfile.sh — a plain bash script:
   `set -euo pipefail`, version variable at top, one function per task, `"$@"` dispatch
   at the bottom, `docker buildx` with `` `arch` `` detection, `--load` for local build
   and a `push` function with `--push --platform linux/arm64,linux/amd64`).
   - From `desk/docker/Makefile` carry over as functions: `build_worker`, `build_dns`,
     `build`, `push` — with the `etc.tar.gz` ADD trick replaced by plain `COPY` of the
     s6 tree (doc §1; the dns image's two-source overlay becomes two `COPY` lines).
     Bump image version tags (variables at the top of taskfile.sh, like `NUXT_VERSION`).
   - From `desk/Makefile` carry over only what's alive: `up` (as `docker compose up -d`,
     modern CLI) and — only if the M3.3 pyinstaller DECISION keeps it — `bundle`.
     Everything else is dead 2014-era tooling and is **deleted**: `freeze` (writes to
     `images/dns`/`images/master`, paths that no longer exist), `images` (same),
     `play`/`play-dns`/`play-testdata`/`enter-ansible` (hardcoded `/mnt/sda1` +
     `yvess/ansible-master`, boot2docker era), `stop_worker`/`start_worker` (s6 v2
     paths `/var/run/s6/services`, wrong after step 3's s6-rc migration — the
     replacement is `s6-rc -d/-u change worker` documented in `tmp/s6-overlay-setup.md` §6).
   - One `taskfile.sh` at repo root (or `desk/` — wherever the user runs it from today;
     ask if unclear) is enough; don't create one per directory (KISS).
   - Delete both Makefiles once their live targets are in taskfile.sh.
3. **DECISION (ask user):** is the pyinstaller `dworker` binary still the deployment
   mechanism for the dns hosts, or can the dns image install Python + the package like
   the worker image (simpler: one install path, no pyinstaller at all)? If pyinstaller
   goes, `requirements-build.txt`, `dworker.spec`, and the `bundle` task go with it.

**Verify:** `./taskfile.sh build` succeeds for both images;
`docker compose up` brings up cdb + dnsa/dnsb + foreman with no errors in logs;
`s6-rc -a list` inside each container shows the expected services, and toggling
`START_WORKER`/`START_PDNS` to NO actually keeps them off (the env-gating contract);
inside worker container render one QR-bill invoice PDF end-to-end and eyeball it —
WeasyPrint 56 → 69 is the biggest visual-risk jump in the whole upgrade;
`dig @localhost -p 1053` answers from dnsa.

---

**Done 2026-09-02.** Verified versions at execution time: alpine **3.24** (latest,
no 3.25), s6-overlay **v3.2.3.2**, couchdb **3.5.2**, nginx **1.30-alpine**,
pdns **5.0.7** (alpine 3.24). Notes:

**DECISIONS taken (user, 2026-09-02):**
- **pyinstaller is gone.** The dns image installs Python like the worker one, so
  `dworker.spec`, `docker/worker/requirements-build.txt` and the `bundle` target
  were deleted, along with the `desk/dist:/opt/app/desk` mount.
- **capi + CouchDB 3.5.2 land here, not in M4.** M4 shrinks to the data
  migration and replication verification.

**3.1 Worker image** — `alpine:3.24`, deps in a venv at `/opt/desk` (PEP 668),
`ENV PATH="/opt/desk/bin:${PATH}:/command"`. Dropped `binutils`, `upx`, `make`,
`readline` and the `py3-*` pins; `cairo` and `fontconfig` were **added** — pip's
CairoSVG/WeasyPrint need them at runtime and the deleted `py3-cairosvg` used to
pull them in. Build deps (`build-base`, `libffi-dev`, `python3-dev`) go in a
`.build-deps` virtual package and are removed in the same layer.

**3.2 DNS image** — `FROM yvess/desk-worker:${WORKER_VERSION}` plus `pdns`,
`pdns-backend-sqlite3`, `sqlite`. This replaces the plan's "two COPY lines": with
Python in the dns image, inheriting the worker image removes a duplicated
apk+pip block and the two images share layers. `build_dns` therefore needs the
worker tag (locally or in the registry); `build`/`push` run worker first.
- The `libgsqlite3backend.so` symlink hack is **deleted**. Its real cause was
  `module-dir=/usr/lib/pdns` in `pdns.conf` overriding the package's own
  `/usr/lib/pdns/pdns`; dropping the `module-dir` line fixes it properly.
- **pdns 5.0 config changes:** `master=yes` → `primary=yes` (5.0 removed the old
  name, and it is a *fatal* unknown-setting error, not a warning). `config-dir`
  and `daemon` were dropped from `pdns.conf` — the run script passes both.
  `pdns_comments.conf` (a 2014 autogenerated template, never read) was deleted.
- **gsqlite3 schema:** the 2014 `powerdns-setup.sql` is rejected by 5.0
  (`no such column: domains.catalog`). Replaced verbatim with the
  `rel/auth-5.0.x` schema; the alpine package ships none. The worker's direct
  SQL only touches columns that survived, so no code change was needed.
- `pdns-init` now `chown -R pdns:pdns "${PDNS_DATA}"` — `pdns_server` drops to
  `setuid=pdns` and could not write the root-owned database or its journal.

**3.1/3.2 s6-overlay v1/v2 → v3** — `cont-init.d`/`services.d` are gone,
`legacy-*` bundles excluded from the tarball. `05-worker-check` → `worker-init`
oneshot, `10-pdns-check` → `pdns-init` oneshot (ordering that the old `sleep 1`
papered over is now `pdns-init/dependencies.d/worker-init`), `worker`/`pdns`
longruns depend on their init. Longruns `exec` their process — the worker's
manual `trap`/`wait`/`sleep 2` dance is unnecessary under s6 supervision.
- **The user bundle lives in `user-bundles.d/`, not `s6-rc.d/user/`** — 3.2.x
  warns the latter is deprecated. `top` references both `user` and `user2`, so
  the Dockerfile creates the empty `user2` bundle (git cannot carry an empty
  directory).
- One `setup-user-services.sh` hook serves both images: `enable_service <name>
  <START_ value>` skips services the image does not ship, so the dns tree needs
  no hook of its own.
- `S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0` (was 20000). worker-init blocks until
  CouchDB answers, which has no useful upper bound; 20s made stage2 fail.
- "wait for couchdb" survives, and is now backed by a `depends_on:
  service_healthy` in compose.

**3.3 Compose** — `services:` top level, no `links:`, relative paths only.
`EXTRA_HOSTS`/`$$DNSA_PORT_53_TCP_ADDR` is replaced by compose network aliases
(`ns1.localhost` → dnsa, `ns2.localhost` → dnsb). Host-specific Cappuccino
mounts moved from `cdb` to `capi` in `docker-extra.yml.dist`.
- `cdb` = official `couchdb:3.5.2`, `COUCHDB_USER`/`COUCHDB_PASSWORD` for the
  admin, `docker/cdb/local.d/desk.ini` for `single_node`, `[cluster] n=1 q=1`
  and `require_valid_user`. That file must **not** be mounted `:ro`: the image's
  entrypoint chowns everything under `/opt/couchdb` under `set -e` and exits 1
  on a read-only mount, with no log output at all.
- The `cdb` healthcheck has to authenticate — `require_valid_user = true` makes
  even `/_up` return 401.
- `capi` = stock `nginx:1.30-alpine` with the verified `map` + `rewrite` config
  from `tmp/etc/nginx/conf.d/`, now at `docker/capi/conf.d/`. `nginx` resolves
  its upstream once at startup, which is the other reason everything waits for
  cdb to be healthy.
- `taskfile.sh` at `desk/` (where compose is run from): `build_worker`,
  `build_dns`, `build`, `push`, `pull`, `compose`, `up`, `down`, `logs`, `test`,
  `help`. Local builds pass `--builder "$(docker context show)"` — buildx's
  docker-driver builder is the one that can see the local image store, which
  `build_dns` needs; a docker-container builder only sees the registry.
  **Later change (ff4d52e, M4/M5 docs pass):** `compose`, `up`, `down` and
  `logs` were dropped again — each only wrapped one `docker compose` command, so
  the stack is run with plain `docker compose up -d` / `down` / `logs -f` from
  `desk/` and the taskfile keeps what needs more than one command.
- Deleted: `desk/Makefile`, `desk/docker/Makefile`, `dworker.spec`,
  `docker/worker/requirements-build.txt`, the two py2 `requirements.txt`
  (worker + dns), `docker/couchdb-testdata.yml` and `docker/_test_desk/` (fig,
  2014). `desk/var` was a broken symlink to `/var/projects/tdesk` (boot2docker
  era) and is now a real directory.

**Bugs found by running the stack (fixed here, with tests):**
1. `install-db` never created the database — it PUT the design doc straight into
   a non-existent `desk_drawer` and swallowed the 404. It now creates the db and
   `raise_for_status()`es both writes. It also ran only when the db was missing,
   so the design doc was never refreshed; worker-init now always calls it.
2. `InstallDbCommand.run()` / `InstallWorkerCommand.run()` called
   `self.set_settings(self.settings)` again, rebuilding `self.db` and making the
   commands impossible to point at a test client. `dworker` already calls it.
3. **CouchDB 3.x rejects the design doc** — five views used SpiderMonkey's
   `for each (x in list)`, which 1.6 accepted and 3.5 fails with
   `compilation_error`. Ported to indexed `for` loops. This is M4 work that had
   to land here because the stack cannot come up without it.

**Verified:** `./taskfile.sh build` builds both images; the full stack comes up
(cdb healthy, capi, dnsa, dnsb, foreman) with the design doc installed and three
worker docs registered; `s6-rc -a list` shows the expected services in both
images and `START_WORKER=NO`/`START_PDNS=NO` keeps both longruns out of the boot
set; `dig @127.0.0.1 -p 1053/-p 2053 chaos txt version.bind` answers from both
dns nodes; the capi routes (`/api/clients`, `/api/_uuids`, `/desk_drawer`,
desk_pad, unknown-collection 404) behave; a QR-bill invoice PDF renders
end-to-end in the worker container on WeasyPrint 69 + CairoSVG 2.9 + qrbill 1.2
+ pypdf 6.16 and looks right (`desk/tmp/m3_invoice_qrbill.pdf`). Suite green,
96 tests.

**Open, for M4 / the frontend round:** nothing — the two items that were open
here were decided in the review follow-up below.

---

**Review follow-up 2026-09-02** — actions from
`tmp/reviews/2026-09-02_m3-docker-code-review.md`.

**DECISIONS taken (user, 2026-09-02):**
- **capi gets `_session` and `_users`** (review C1). `require_valid_user = true`
  left the browser with no way to log in; `desk.conf` now proxies both through
  to CouchDB, which is what the old `vhost_global_handlers` line did. Verified
  route-by-route against a stub upstream — the 15 pre-existing routes are
  unchanged, `GET/POST /_session` and `/_users/<id>` pass through verbatim.
- **The SSE `_changes` feeds get `proxy_read_timeout 3600`** (review A1); every
  other route keeps 60s. nginx rejects a second `proxy_read_timeout` in the same
  context, so the 60s moved out of `desk_proxy.inc` up to the `server` block and
  `desk_changes.inc` overrides it in the feed locations.
- **Unknown collection names keep returning 404** (review A2) rather than being
  passed through to CouchDB unrewritten.
- **`install-db` keeps running on every foreman boot** (review B2). CouchDB only
  invalidates a view when the design doc content actually changes, so a re-PUT of
  identical content costs one request and no rebuild.
- **`tmp/etc/nginx/` is deleted** (review A6), `desk.conf.openresty` with it.
  Everything under `tmp/etc/` was only ever an example to work from; the live
  config is `desk/docker/capi/conf.d/`, which is tracked. **Nothing in production
  code may reference `tmp/` at all** — checked, and it doesn't (the `/tmp/` paths
  in `docker/worker/Dockerfile` are the container's own temp dir).

**Deviations from the spec, recorded rather than reverted** (review A3, C4 — not
put to the user):
- `S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0` instead of the plan's "keep the raised
  value": worker-init blocks until CouchDB answers, which has no useful upper
  bound, and 20s made stage2 fail.
- The dns image is `FROM yvess/desk-worker` instead of the plan's two `COPY`
  lines — the consequence of dropping pyinstaller, since dns needs Python too.
  `build_dns` therefore needs the worker tag; `build`/`push` order it first.

**Also fixed:** the `__main__` guard in `tests/test_commands.py` sat above two
test classes, which skipped them when the file was run directly; `INSTALL.rst`
still pointed at the deleted py2 `requirements.txt` and `.editorconfig` still had
a `[Makefile]` section; `tmp/s6-overlay-setup.md` documented the deprecated
`s6-rc.d/user/` layout (it now describes `user-bundles.d/` and the mandatory
empty `user2` bundle, with both messages verified against the built image).
`InstallWorkerCommand` got the regression test it was missing for the removed
`set_settings` call. Cleanups: `EXTRA_HOSTS`/`TESTING` deleted from `worker-init`
(nothing sets them since compose network aliases replaced them), `grep -q` in
`pdns-init`, both oneshot bodies renamed `run` → `init.sh` (in s6 vocabulary
`run` means a longrun), `taskfile.sh` spells each buildx invocation once
(`_buildx_worker`/`_buildx_dns`, helpers hidden from `help`), and
`docker-compose.yml` was **left alone**: YAML anchors for the repeated CouchDB
env/mounts/dns node were tried and reverted — the user prefers the services
spelled out in full over the indirection (now in `CLAUDE.md`, "Style").

**Re-verified:** both images build; a throwaway cdb + worker + dns stack boots
with the renamed oneshots, installs the design doc, registers the workers and
answers `dig chaos txt version.bind`; `nginx -t` passes on the capi config; suite
green, 97 tests.
