# converge v2: hub on home-gpu, declarations, recipes

Working plan for the redesign Joe asked for on 2026-10-28. Implemented on yadm branch
`converge-v2`; this file is folded into README.md and deleted when the branch merges to main.

## 0. Goals and non-goals

Goals, in Joe's words: host the fleet state on home-gpu instead of the GitHub status-branch relay;
track packages, GUI apps, logins (gh, atuin, op, Tailscale) and Mac state; make a *direct*
desired-vs-actual comparison so every machine is accounted for; "something that works like nix
but handles gui stuff too", with "procedures and recipes" for the parts no program can apply.

- Declarative like Nix: every kind of thing on a machine has a tracked file that says what is wanted,
  and sync reports exactly what is missing and what is present but undeclared.
- Unlike Nix, no sandboxed build: apply through the real tools (brew, apps.json releases, flatpak,
  gnome-extensions) where possible, and where not possible (App Store, downloaded installers, sudo
  on home-gpu, logins, macOS permissions) turn the gap into a recipe: a check plus the exact
  manual steps, visible on the hub and optionally as a chain in the Tasks app.
- Direct comparison: one hub page per machine (desired vs actual, pending recipes) and one fleet
  page (who checked in, drift between machines).

Non-goals: Nix/Ansible rewrite; automatic deletion of GUI apps or packages (reported, removed by
hand); replacing yadm, the Brewfiles, apps.json, layout.txt, mac-settings or the daily schedule.

Constraints that shape every decision below:

- Clients run on macOS system Python 3.9 (`/usr/bin/python3`, no YAML/TOML/requests) and on
  Python 3.14 (home-gpu). Stdlib only, `python3.9`-compatible syntax everywhere.
- Swan (cluster) is not on the tailnet and reaches only GitHub.
- home-gpu has no passwordless sudo: user systemd units and `tailscale serve` only.
- The repo is public: no secrets, no private hostnames beyond what is already there.
- Style: `~/.claude/standards/python-style.md` (nesting <= 3, complexity <= 10, <= 4 params,
  type hints, docstrings, early returns) and `leanness.md` (reuse, edit don't append, delete what
  becomes obsolete in the same change).

## 1. Architecture

```
laptop / studio / plex-server / home-gpu          Swan (cluster)
   converge sync (daily 10:00, or by hand)           converge sync
   |  phases -> last.json + state.json                |  same files
   |  POST https://home-gpu.tail2813f4.ts.net/converge/report
   v                                                  v  git push --force status/cluster-swan (as today)
 hub.py on home-gpu (127.0.0.1:8790, user systemd) <-- bridge thread: git fetch status/* every 30 min
   sqlite ~/.local/state/dotfiles/hub.sqlite
   GET /fleet  GET /machine/<host>  GET /          (JSON for the CLI, HTML for the browser)
   optional: Tasks app chains (http://mac-studio:8767) for pending recipes
```

What each machine computes locally (so a machine with no hub still gets the full report in
`converge status`): phase results, the snapshot, the declared desired-vs-actual lists, the recipe
check results. The hub only stores, compares across machines, renders and (optionally) files tasks.

## 2. Phase 1: hub and transport

### 2.1 `setup/hub.py` (new, stdlib: `http.server`, `sqlite3`, `threading`, `subprocess`)

- `hub.py serve [--port 8790] [--db PATH] [--bridge REMOTE|none]`: `ThreadingHTTPServer` on
  127.0.0.1. Env overrides for tests: `CONVERGE_HUB_DB`, `CONVERGE_BRIDGE_REMOTE`,
  `CONVERGE_TASKS` (phase 3).
- DB schema (one table, created on start, `PRAGMA journal_mode=WAL`):
  `reports(id INTEGER PRIMARY KEY, host TEXT, class TEXT, profile TEXT, finished TEXT, exit INTEGER,
  received TEXT, last_json TEXT, state_json TEXT)`; index on `(host, received)`. Rows older than 90
  days pruned on every insert.
- Routes (a `/converge` prefix is stripped so the same handler serves behind `tailscale serve
  --set-path /converge`):
  - `POST /report` body `{"last": {...}, "state": {...}}`, 2 MB cap, `Content-Type:
    application/json`. Requires the `Tailscale-User-Login` header that `tailscale serve` adds to
    proxied requests (an empty value means a direct local request: accepted only when the server
    was started with `--trust-local`, which the tests use). Returns 204. Host and class come from
    `last["machine"]` (`class@host`, already written by `Sync._save`).
  - `GET /fleet` -> `[{"host", "class", "profile", "finished", "exit", "received", "phases": {...},
    "stale": bool}]`, newest row per host, newest first. This is exactly what `fleet_lines()` needs.
  - `GET /machine/<host>` -> the newest `last` and `state` dicts for that host.
  - `GET /machines` -> every host's newest `state` dict (`{host: state}`) for `--diff`.
  - `GET /` and `GET /machine/<host>` with `Accept: text/html` -> the HTML pages (section 4).
  - Anything else 404; errors 400 with a one-line body; no stack traces to the client.
- Bridge thread: every 30 min (`--bridge-interval`), in `~/.local/state/dotfiles/hub-bridge/`
  (a bare clone of the yadm remote, created on first run) `git fetch --force REMOTE
  '+refs/heads/status/*:refs/heads/status/*'`, then for each `status/*` ref read `last.json` and
  `state.json` with `git show` and insert a report when `finished` is newer than the stored one for
  that host. Uses `git`, not `gh`: the repo is public. Remote defaults to the yadm remote URL
  (`https://github.com/jyesselm/dotfiles.git`); tests pass a `file://` bare repo.
- Pure helpers, unit-testable without a server: `store_report(db, last, state)`, `fleet_rows(db)`,
  `machine(db, host)`, `prune(db, days)`, `bridge_once(db, remote, workdir)`, `strip_prefix(path)`,
  `render_fleet(rows)`, `render_machine(last, state, ...)`.

### 2.2 Serving on home-gpu

- `~/.config/systemd/user/converge-hub.service##hostname.home-gpu,template` (yadm alternate, same shape as
  `clips-relay.service`): `ExecStart=%h/.config/yadm/setup/hub.py serve`, `Restart=on-failure`,
  `RestartSec=5`, `WantedBy=default.target`, `Environment=PATH=%h/.local/bin:/usr/bin:/bin`.
- `tailscale serve --bg --set-path /converge http://127.0.0.1:8790` (one-time, by hand; documented
  in README). The existing `/` -> clips mapping stays.
- Clients reach `https://home-gpu.tail2813f4.ts.net/converge/...` over the tailnet with `urllib`
  (already verified from every Mac: valid cert, no setup).

### 2.3 `setup/sync.py` changes

- `HUB = 'https://home-gpu.tail2813f4.ts.net/converge'`, `HUB_TIMEOUT = 20`; `CONVERGE_HUB` env
  overrides (tests and the VM runs point it at a local hub).
- `Sync.checkin()`: profile `cluster` keeps `publish_status` (git relay). Every other profile POSTs
  `{"last": last.json, "state": state.json}` to `HUB/report`. Failure stays a note
  (`check-in skipped: <reason>`), never an error, as today.
- `fetch_statuses(setup, yadm)` is replaced by `fetch_fleet(setup)` (GET `/fleet`) and
  `fetch_machines(setup)` (GET `/machines`); `fleet()` and `print_differences()` consume those. The
  git fetch of `status/*` is deleted together with `status_ref`, `publish_status` stays (cluster).
- `converge fleet` prints the same table as today from `/fleet`; `--diff` from `/machines`;
  `--checkin` POSTs first. Offline hub = error exit 2 with the URL, as the offline fetch is today.
- Stale warning at the end of a sync comes from the `/fleet` answer (`stale` computed by the hub,
  `STALE_DAYS` moves to hub.py; sync.py keeps printing the names).
- New field in last.json: `corrective` = number of phases whose status was `changed` (what the run
  had to fix). The fleet table shows it as a column so a machine that keeps re-fixing the same
  thing stands out (Puppet's corrective-change idea).
- `fleet_lines(rows) -> List[str]` and `difference_lines(states, rules) -> List[str]` factored out
  so the CLI and the hub page render from the same functions (the hub imports sync/snapshot; both
  modules are already import-safe).
- New `--skip PHASES` flag on `converge sync` (comma-separated phase keys): a skipped phase is
  recorded as `skipped` with summary `--skip`. Needed by the container runs (no brew/micromamba) and
  handy by hand; replaces nothing existing.

### 2.4 Tests (phase 1)

- `test_hub.py`: store/fleet/machine/prune on a temp DB; `strip_prefix`; `bridge_once` against a
  temporary bare repo with a fake `status/x-y` branch made with the same plumbing `publish_status`
  uses; HTTP round trip on an ephemeral port with `--trust-local` (POST then GET /fleet, 2 MB cap,
  missing header -> 403, bad JSON -> 400, HTML page contains the host).
- `test_sync.py`: rewrite the six fleet/check-in tests for the HTTP transport (fake `urllib` via a
  stubbed `sync.request` function so no socket is opened), keep the cluster test on the git path,
  add `--skip` and `corrective`.
- `test_sync_mac.py`: fix the two counts that broke when apps.json grew to four apps.
- Everything green under `/usr/bin/python3` (3.9) and `python3` (3.11); the container run (section
  5) repeats it under `python:3.9-slim` and `python:3.14-slim`.

### 2.5 README

Rewrite the Fleet, Differences and Onboard paragraphs: hub URL, what the check-in sends, cluster
exception, how to run the hub, `tailscale serve` line, `--skip`.

## 3. Phase 2: declarations and recipes

### 3.1 Declaration files (`setup/declared/`)

One file per kind, the layout.txt line format (`entry  key:value ...`, `#` comments). Every kind
has an *observer* (what is present) and, where a program can do it without sudo, an *installer*.
`setup/declared.py` holds the kinds table, parsing, the comparison and the `declared` sync phase.

| file | entry | qualifiers | observer | installer |
|---|---|---|---|---|
| `apps.txt` | `.app` name without the suffix | `source:brew\|release\|mas\|manual\|system`, `class:` list, `url:` (manual), `allowed` | `/Applications`, `~/Applications`, `/System/Applications` | none here: `brew` entries must match a cask in a Brewfile (a unit test enforces it), `release` entries must match apps.json; `mas`/`manual` become recipes |
| `agents.txt` | LaunchAgent label | `class:`, `allowed` | `~/Library/LaunchAgents/*.plist` (label from the plist) | none (reported) |
| `login-items.txt` | login item name | `class:`, `allowed` | System Events (already in the snapshot) | none (recipe: System Settings > General > Login Items) |
| `apt.txt` | package | `class:`, `allowed` | `apt-mark showmanual` | none (recipe prints `sudo apt install ...`) |
| `snap.txt` | snap name | `class:`, `allowed` | `snap list` | none (recipe) |
| `flatpak.txt` | app id | `class:`, `allowed` | `flatpak list --app --columns=application` | `flatpak install --user -y flathub <id>` |
| `gnome-extensions.txt` | extension uuid | `class:`, `allowed` | `gnome-extensions list --enabled` | `gnome-extensions enable <uuid>` when installed, else recipe (`gext`/extensions.gnome.org) |

Rules shared by every kind (one implementation):

- `wanted` = entries whose `class:` includes this machine's class (default: every class the kind
  applies to; a kind applies to mac or linux profiles only). `allowed` = may be present anywhere,
  never installed, never reported.
- `missing` = wanted - present. `undeclared` = present - wanted - allowed - the kind's built-in
  ignore list (Apple's system apps, Homebrew-owned agents, `homebrew.mxcl.*`).
- Phase result: `ok` when both empty; `changed` when the installer fixed every missing entry;
  `warn` otherwise, details grouped `missing:` / `undeclared:` with the source hint per entry
  (`App Store`, `download: <url>`, `sudo apt install a b c`). `--plan` prints the same without
  installing.
- `converge adopt declared [KIND]` appends this machine's undeclared entries as `allowed` lines
  under a dated comment, exactly like `adopt-extras` does for brew (which stays as is, Brewfiles are
  already the declaration for brew). `adopt-extras` becomes `adopt extras` with a legacy alias.
- Snapshot keys added so the hub can compare and the recipes can check: `declared.<kind>.missing`,
  `declared.<kind>.undeclared` (lists), plus `apt`, `snap`, `flatpak`, `gnome_extensions` inventories
  on Linux, mirroring `brew.*` on the Mac.
- Removal is never automatic. The report is exact, Joe deletes by hand or adopts.

Initial content comes from the machines themselves: an Opus agent runs the observers on studio,
laptop, plex-server and home-gpu (ssh), seeds each file with what is wanted everywhere vs per class,
and marks the rest `allowed` so the first sync is quiet; Joe prunes later.

### 3.2 Recipes (`setup/recipes.txt`, `setup/recipes.py`)

A recipe is a check against snapshot keys plus the exact manual steps. Records separated by blank
lines, `key: value` lines, `step:` repeated:

```
recipe: gh-login
title: Sign in to GitHub CLI
on: mac, linux, cluster
check: gh.auth == jyesselm
step: Open a terminal
step: Run: gh auth login --hostname github.com --web
step: Pick SSH, choose ~/.ssh/id_ed25519.pub, finish in the browser
step: Run: converge sync
```

- `check:` grammar, deliberately tiny: `<key> <op> <value>` with ops `==`, `!=`, `<`, `>` (numbers
  and ISO ages like `1d`), `has <item>`, `empty`, `present`. Lists match any element. Evaluated by
  `recipes.evaluate(recipes, state, profile, class) -> List[Pending]` which is pure, so the client
  and the hub run the same function on the same `state.json`.
- Snapshot gatherers added for the checks: `atuin.synced` (age of
  `~/.local/share/atuin/last_sync_time`), `op.account` (`op account list`), `tailscale.online`
  (`tailscale status --json` BackendState/Self.Online, Mac path
  `/Applications/Tailscale.app/Contents/MacOS/Tailscale`), `keys.present` (own public keys),
  `secrets.missing` (names in `~/.zsh/secrets.refs` with no `zsh-keys` Keychain entry, via
  `security find-generic-password`; Linux: not applicable), `karabiner.keyboards` exists already.
- First recipes: gh-login, atuin-sync (`atuin.synced < 1d`), op-signin (`op.account ==
  jyesselm@unl.edu`), tailscale-up, ssh-keys (`keys.present has id_ed25519.pub` and `id_ecdsa.pub`
  on Macs), keychain-secrets (`secrets.missing empty`), karabiner-input-monitoring
  (`karabiner.keyboards != none`), plus one generated recipe per `mas`/`manual` app and per Linux
  package kind without an installer (steps from the declaration's `url:`/source).
- Sync phase `recipes` (after `doctor`): status `ok` when nothing is pending, `warn` with one detail
  line per pending recipe (title + first step), and `last.json` gains `pending: [{name, title,
  steps}]`. `converge status` prints the steps under "Needs attention" (replaces the `HINTS` dict
  and the hotkeys/layout hint lines: those become recipes too, so one mechanism remains).
- `converge recipe NAME` prints a recipe's steps; `converge recipes` lists pending ones.

### 3.3 Tests (phase 2)

`test_declared.py` (parse every qualifier, class filter, missing/undeclared/allowed, installer
called only when present, `--plan`, adopt appends under a dated comment, Brewfile/apps.json
cross-check on the real files), `test_recipes.py` (grammar, every op, ages, list keys, evaluate on
a canned state, the generated recipes), snapshot gatherer tests with stubbed commands. Manifest
tests load the real `declared/*.txt` and `recipes.txt` so a typo fails the suite.

## 4. Phase 3: hub pages and the Tasks hook

- `GET /` fleet page: the `fleet_lines` table, then "Drift" (`difference_lines` over the newest
  states with compare.yml rules, `?all=1` lifts them), then "Pending recipes" grouped by machine.
  Plain HTML, one `<style>` block, no JS, readable on the phone.
- `GET /machine/<host>`: phases with details, declared missing/undeclared per kind, pending recipes
  with their steps, and this machine's snapshot keys that differ from the fleet majority.
- Tasks hook (opt-in: `CONVERGE_TASKS=http://100.73.70.25:8767` in the unit's environment): after
  each stored report, for every pending recipe create one chain in project "Computers" (created if
  absent) titled `🖥 <host> · <recipe title>`, steps = the recipe's steps (title <= 6 words, note =
  the exact line), skipped when an open task with that title exists; when a recipe clears on a later
  report, `POST /api/tasks/<id>/done` on the matching open task. Joe's chain format from
  `task-step-format.md`, no secrets in any step.
- Tests: page rendering on canned rows (contains host, phase glyphs, recipe steps), the hook against
  a fake Tasks server on an ephemeral port (create once, no duplicate, done on clear).

## 5. Test harness (`setup/testing/`)

OrbStack provides Docker and Linux VMs on the Macs (already on plex-server; installed on the
studio 2026-10-28; the cask moves from Brewfile.server to Brewfile.desktop so the laptop gets it).
Tart (installed at `~/.local/opt/tart`, symlinked in `~/.local/bin`) provides macOS VMs.

1. `unit.sh`: runs the whole unittest suite in `python:3.9-slim` and `python:3.14-slim` with
   `setup/` bind-mounted read-only (`docker run --rm -v $PWD:/setup:ro -w /setup python:3.9-slim
   python3 -m unittest discover -v`). Fails on the first red.
2. `e2e.sh` (Docker, one compose file): a `hub` container (Ubuntu, python3, git) running
   `hub.py serve --trust-local --bridge file:///remote`, a bare git repo volume standing in for
   GitHub, two `linux` client containers and one `cluster` client container. Each client gets a yadm
   clone of the branch under test (served from the same bare repo), `CONVERGE_HUB=http://hub:8790`,
   runs `converge sync --skip packages,repos,apps,defaults,hotkeys`, then the script asserts with
   `curl`: `/fleet` lists both linux hosts with exit 0; the cluster host appears after `hub.py
   bridge-once`; `/machine/<host>` has `pending` recipes (gh-login pending in a container is the
   expected answer); `converge fleet --diff` from a client prints the differing `os`/`dotfiles` keys.
3. `linux-vm.sh` (OrbStack VM `orb create ubuntu:24.04 converge-test`): real systemd user session.
   Installs yadm/git/python3, clones the branch, `bootstrap --plan`, `bootstrap`, installs the
   `converge-hub.service` unit (`systemctl --user enable --now`), checks `curl 127.0.0.1:8790/fleet`,
   runs `converge sync` against it, then `converge schedule` and checks the crontab line. This is the
   rehearsal for home-gpu. `orb delete converge-test` at the end unless `KEEP=1`.
4. `mac-vm.sh` (Tart, image `sequoia-base` from `ghcr.io/cirruslabs/macos-sequoia-base:latest`,
   downloading now): `tart clone sequoia-base converge-mac`, `tart run --no-graphics`, ssh
   `admin@$(tart ip converge-mac)`; install Homebrew, `brew install yadm python`, `yadm clone -b
   converge-v2 --no-bootstrap` from GitHub, `yadm config local.class laptop`, `bootstrap --plan`,
   `yadm bootstrap`, `converge sync --plan`, `converge sync` with `CONVERGE_HUB` pointing at a hub
   run on the host (reachable from the VM at the default gateway), `converge status`, `converge
   schedule`, then assert the hub lists the VM and that `apps.txt` reports the casks that cask
   installs put in place. Known limits: no App Store (mas recipes stay pending), no Input Monitoring
   (Karabiner recipe stays pending), cask installs take a while. `tart delete converge-mac` unless
   `KEEP=1`.

Every script is idempotent, prints PASS/FAIL per assertion and exits non-zero on any FAIL. The
Opus agents run 1 and 2 themselves after each phase; 3 and 4 run once at the end (step 11).

## 6. Order of work

1. Branch: `yadm checkout -b converge-v2` on the studio (the daily sync's dotfiles phase commits
   and pushes only on main, so nothing half-done is published). Commit after each phase with
   `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
2. Opus agent A: phase 1 (section 2). Opus agent B, in parallel: `testing/unit.sh`, `e2e.sh`,
   `linux-vm.sh`, `mac-vm.sh` against the spec above (they only touch `setup/testing/`).
3. Review A's diff against the standards; run unit (both Pythons) + `unit.sh` + `e2e.sh`.
4. Opus agent C: phase 2 (section 3), including seeding the declaration files from the real machines.
5. Review, run everything again.
6. Opus agent D: phase 3 (section 4).
7. Deploy on home-gpu: look at its modified `~/.ssh/config` first (do not clobber), `yadm fetch &&
   yadm checkout converge-v2`, `systemctl --user daemon-reload && systemctl --user enable --now
   converge-hub`, `tailscale serve --bg --set-path /converge http://127.0.0.1:8790`, then `converge
   fleet --checkin` on studio, laptop, plex-server, home-gpu, `converge schedule` on home-gpu, and
   `converge sync` on Swan so the bridge picks it up.
8. `linux-vm.sh` and `mac-vm.sh` end to end.
9. Final review, README, delete this file, merge `converge-v2` into main, push; leave the `status/*`
   branches (the bridge still reads the cluster's).

Decisions left to Joe, none blocking: drop `colima` from the Brewfile now that OrbStack covers
Docker on every Mac; delete the stale `status/*` branches of non-cluster machines after the merge;
whether the Tasks hook should be on from the start.
