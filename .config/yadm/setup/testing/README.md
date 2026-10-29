# converge test harness

Each script prints `PASS <what>` / `FAIL <what>` per assertion and exits 1 if any failed. All are
idempotent (they tear down or reset what they made). Assertions marked `[phase1]` need `hub.py` and
the HTTP check-in (PLAN.md section 2).

Shared by all: `lib.sh` builds `~/.cache/converge-testing/remote.git`, a bare repo holding the
current yadm branch, by fetching from the yadm repo (refs there are never touched). `WORKTREE=1`
adds the uncommitted `~/.config/yadm` and `~/.local/bin` changes as one extra commit in that bare
repo only, so a change can be tested before it is committed. `BRANCH=x` overrides the branch.
`json_check.py` holds the JSON assertions on hub answers. Logs go to `~/.cache/converge-testing/`.

| script | needs | proves |
|---|---|---|
| `unit.sh` | Docker | the unittest suite passes under `python:3.9-slim` and `python:3.14-slim` with `setup/` mounted read-only; needs no packages and no `git` |
| `e2e.sh` | Docker (`compose.yml`, `Dockerfile.client`, `Dockerfile.hub`) | onboarding on a bare Linux box (yadm clone, class, `converge sync --plan`, `sync --skip`, `status`); linux clients POST to the hub, the cluster client pushes `status/cluster-swan-ci` and appears after `hub.py bridge-once`; `/machine/<host>`, `converge fleet` and `fleet --diff` read the hub |
| `linux-vm.sh` | OrbStack | the home-gpu rehearsal in VM `converge-test` with a real systemd user session: clone from the bare repo over `/mnt/mac`, `bootstrap --plan`, `yadm bootstrap` (micromamba tools), the `converge-hub.service` unit, `converge sync`, `converge schedule` crontab line |
| `mac-vm.sh` | Tart, image `sequoia-base` | new-Mac onboarding in VM `converge-mac`: Homebrew, `brew install yadm python`, clone, class `laptop`, `bootstrap --plan`, `yadm bootstrap`, `sync --plan`, `sync`, `status`, `schedule` (launchd job loaded), the hub on this Mac lists the VM |

```sh
~/.config/yadm/setup/testing/unit.sh
WORKTREE=1 ~/.config/yadm/setup/testing/e2e.sh          # KEEP=1 leaves the containers up
WORKTREE=1 ~/.config/yadm/setup/testing/linux-vm.sh     # KEEP=1 keeps the VM; next run reuses it
WORKTREE=1 ~/.config/yadm/setup/testing/mac-vm.sh > ~/.cache/converge-testing/mac-run.txt 2>&1 &   # about an hour
```

Details and known limits:

- e2e: the cluster client is named `swan-ci` because `detect_profile()` calls a Linux host with
  `swan` in its name `cluster`. Clients run as `joe` with a git identity from `GIT_*` variables (the
  dotfiles track `~/.gitconfig`). The hub serves the code of the branch under test, fetched from the
  same bare repo, and is started with `--host 0.0.0.0`: clients reach it as `http://hub:8790`, which
  a hub bound to 127.0.0.1 inside its container cannot answer.
- linux-vm: `yadm config local.hostname home-gpu` makes yadm link the `##hostname.home-gpu`
  alternates (the hub unit) although the VM is called `converge-test`; the fleet row still says
  `converge-test`. `loginctl enable-linger` gives `systemctl --user` a bus under `orb -m`. The real
  sync's repos phase fails (grc has no GitHub login), so the script asserts that the sync wrote
  `last.json`, not exit 0.
- mac-vm: ssh as `admin`/`admin` (cirruslabs default; `VM_PASSWORD` overrides) through
  `SSH_ASKPASS` + `SSH_ASKPASS_REQUIRE=force`, with `-F /dev/null` and no agent so this Mac's ssh
  config and keys stay out of it. The hub runs here on 127.0.0.1:8790 and the VM reaches it through
  `ssh -R 8790:127.0.0.1:8790` on every command (a 127.0.0.1 listener is not reachable at the VM's
  gateway). `SOURCE=local` (default) clones from the bare repo shared read-only with
  `tart run --dir`; `SOURCE=github` clones `BRANCH` from GitHub and needs it pushed. Read-only means
  pre-phase-1 status pushes from the VM fail (a note, not an error). No App Store, no Input
  Monitoring, so `mas` and Karabiner stay pending; cask installs make bootstrap slow.
- The scripts share `remote.git`: do not run two at once with different `WORKTREE`/`BRANCH`.
- PLAN.md items not asserted yet: `pending` recipes on `/machine/<host>` and `apps.txt` casks in
  the Mac VM (phase 2).
