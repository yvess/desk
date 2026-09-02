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
Lua output. It lives in `tmp/etc/nginx/conf.d/`:
`desk.conf` (maps + locations), `desk_proxy.inc` (shared proxy headers),
`desk_changes.inc` (the SSE `_changes` rewrite). The original is kept beside it as
`desk.conf.openresty` — it is the behavioral reference; delete it once M3 lands.
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
