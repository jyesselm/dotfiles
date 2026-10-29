# New-computer setup

One entry point: **`yadm bootstrap`** installs the terminal environment, restores plugin dependencies and installs `grc` (git-repo-checker) from its developing checkout. Desktop apps, rich file previews, private games and search-cli are explicit options.

## New Mac

1. Install Apple's command-line developer tools (`xcode-select --install`) and [Homebrew](https://brew.sh). Follow Homebrew's displayed shell setup instructions.
2. Clone and inspect your dotfiles, then install:

```sh
brew install yadm python
yadm clone --no-bootstrap https://github.com/jyesselm/dotfiles.git
~/.config/yadm/bootstrap --plan
yadm bootstrap
```

Existing home-directory files may conflict with a yadm clone. Review those conflicts instead of using a forced checkout.

The default Brewfile installs Git, Python, Zsh, tmux, Neovim, Yazi, fzf, fd, ripgrep, zoxide, Starship, Atuin, bat, lsd, jq, uv, GitHub CLI, LazyGit, Node, and JetBrains Mono Nerd Font. Homebrew installs missing packages without a blanket upgrade or cleanup; dependency installation can still upgrade a required dependency. A too-old existing tmux/Neovim/Yazi is reported by doctor instead of silently accepted.

## Linux, WSL and Swan

Start with Python 3.9+, Git and yadm installed via your distribution or cluster modules. On Swan, load the Git/Anaconda modules if those commands aren't initially available. Then:

```sh
yadm clone --no-bootstrap https://github.com/jyesselm/dotfiles.git
~/.config/yadm/bootstrap --plan --profile cluster  # use linux on a workstation
~/.config/yadm/bootstrap --profile cluster
```

Linux uses a checksum-verified Micromamba 2.9.0-0 binary and a dedicated conda-forge environment at `~/.local/share/dotfiles/tools`. It supports x86_64 and aarch64. It needs network access, sufficient home-directory space, and a compatible Linux runtime; it never uses sudo, runs conda init, activates or modifies an existing research environment.

Terminal-command wrappers go in `~/.local/share/dotfiles/bin`. There is intentionally no managed Python wrapper in your shell PATH. Neovim is constrained to the 0.11 series for this configuration. Linux `lsd` is omitted because it isn't in this package channel; the shared aliases already fall back to `ls`.

Repeat runs retain the tool environment when its manifest and required executables match. A changed manifest triggers dependency reconciliation only in this dedicated environment. Conda dependencies and Homebrew formulae are not completely version-locked; this is a repeatable setup recipe, not a bit-for-bit machine image.

Install/select the Nerd Font **on the terminal's client computer**, not on an SSH server. Existing tmux servers do not change version when binaries/configs change: detach and use `tmux-modern` on Swan. Running jobs and tmux servers are never killed or restarted by bootstrap.

## Options

After cloning, use either `~/.config/yadm/bootstrap` (runs `converge setup`) or `~/.local/bin/converge`. Open a new terminal to get `converge` on PATH; `converge -h` lists the commands. The old name `dotfiles-setup` and its flag form (`dotfiles-setup --sync`) still work.

```sh
converge setup --plan                    # bootstrap preview: no changes, installs or downloads
converge setup --previews                # PDF / SVG / archive / video previews
converge setup --desktop                 # Mac: iTerm2, Cursor
gh auth login
converge setup --games                   # private tmux-dojo and nvim-dojo
converge setup --search                  # search-cli (s) from the developing checkout
converge setup --skip-packages --skip-nvim   # shell/menu/config setup only
converge doctor                          # read-only health check (add --search --games --previews to cover them)
converge sync [--plan]                   # converge this computer (see Daily sync)
converge sync --skip packages,repos      # record those phases as skipped this run
converge status                          # last sync: each warning's details and how to clear it
converge adopt KIND                      # allow what this computer has undeclared: extras (brew) or a setup/declared/ kind
converge recipes                         # the manual steps pending since the last sync
converge recipe NAME                     # one recipe's numbered steps (gh-login, atuin-sync, ...)
converge schedule                        # daily launchd job (Mac) or crontab line (Linux)
converge fleet                           # last check-in of every machine, from the hub on home-gpu
converge fleet --checkin                 # send this machine's last sync result first (also: converge checkin)
converge fleet --diff                    # what differs between machines (setup/compare.yml selects the keys; --all for every key)
converge fleet --keys                    # everything this machine's snapshot holds, to pick from for compare.yml
```

Flags combine, for example `converge setup --plan --desktop --previews --games --search`. To check optional components, include them with doctor: `converge doctor --games --search --previews`.

**Use the wrapper for options.** The installed yadm version executes its bootstrap without forwarding arguments; `yadm bootstrap --plan` is not the documented interface here.

## What it does

- Keeps the tracked Yazi theme, icons, bindings and zoxide configuration as the source of truth.
- Installs pinned Oh My Zsh and its two configured community plugins without running an installer that rewrites `.zshrc` or changes your login shell.
- Uses the existing pinned tmux setup and generated menu.
- Runs Neovim's `Lazy! restore` against the committed lockfile, not a bulk plugin upgrade. Plugin builds can download parsers or language servers and need a working compiler/toolchain.
- Links Cursor settings and keybindings only for an installed app or an explicitly requested desktop setup. Existing settings receive unique backup names; earlier backups are never overwritten.
- Reports missing tools, incompatible versions and failed stages with a nonzero exit code. The final message says “incomplete” if a required step fails.

Existing shell/plugin/private-repository checkouts are retained, including local changes. Bootstrap does not pull or reset those checkouts. To update a game, use `git pull --ff-only` then its `install.sh` in `~/.local/share/dotfiles/repos/<name>` (Neovim uses `--lazy`). Private game source stays outside the public yadm repository.

`grc` (git-repo-checker) and `s` (search-cli) are installed with `uv tool install --editable` from their grc-managed developing checkouts under `~/local/code/python/developing` (cloned there if absent), so each command tracks its checkout; bootstrap always installs `grc`, and `s` with `--search`. `s` is installed with its `gui` and `docs` extras, so `s gui` and document previews work on every machine, and the sync's apps phase writes `/Applications/Search CLI.app`, a launcher for `s gui` with the icon from the checkout. A commit on `main` is what propagates: the daily sync fast-forwards every machine's checkout and reinstalls the command when it is missing or `pyproject.toml`/`uv.lock` changed. Because `grc` cannot update its own checkout before it runs, the sync fast-forwards git-repo-checker itself first. Doctor also starts a login zsh and checks that `grc` (and `s`) resolve to `~/.local/bin`, so a conda copy of the same command cannot shadow the uv install; `.zsh/tools.zsh` puts `~/.local/bin` back in front after the conda/mamba init for that reason. Uncommitted work, the database, vaults and papers stay local. The portable shell helper is loaded only when that optional checkout exists. The tracked `~/.config/search-cli/config.yaml` configures `~/notes` as the Obsidian vault on each computer; sync the notes themselves separately. If a computer uses a different layout, edit `live.vaults` in that file. Search indexes are built locally and are not synced.

## Finish once per computer

- Open a new terminal; select JetBrainsMono Nerd Font and enable Option-as-Esc if you want Option tmux shortcuts.
- Log into GitHub/Atuin and any desktop apps as needed. No credentials or shell history are copied by bootstrap.
- Run `converge doctor`. Use `:checkhealth` in Neovim for language-server/parser details.
- If Git still expects `cursor --wait` but you chose terminal-only setup, use `git config --global core.editor nvim`.
- A local override in `~/.zsh/local.zsh` can configure host-specific paths. Bootstrap preserves it.
- API keys: in 1Password turn on Settings → Developer → Integrate with 1Password CLI, then run `keys sync` (one Touch ID). It copies
  every key named in `~/.zsh/secrets.refs` from 1Password into the login Keychain, where each shell reads it without a prompt.
  `keys add NAME` pastes a new key (hidden) into 1Password, or replaces its value; `keys` lists which are set. Values never go in a file.
  Logins: `pw add NAME [url]` saves a 1Password Login (password hidden, or Enter to generate), `pw NAME` copies its password for
  45 s, `pw` lists them; `pw new [length|words]` copies a fresh password or passphrase.

The pending search-cli ↔ Yazi integration is a separate feature; this bootstrap installs their current configurations and tools.

## Daily sync

The idea is declarative, like Nix, without Nix: tracked files say what every computer should have (`layout.txt`, the Brewfiles, `apps.json`, `declared/`, `recipes.txt`), each sync applies what a program can apply through the real tools and reports what is missing or undeclared, and what only a person can do (logins, App Store, sudo, macOS permissions) becomes a recipe with a check and exact steps. Nothing is ever removed automatically. The hub shows desired versus actual per machine and the drift between machines.

`converge sync` runs these phases in order: layout, dotfiles, keys, packages, repos, apps, declared, defaults, hotkeys, doctor, recipes. Preview with `--plan` (read-only); `--skip packages,repos` records the named phases as `skipped` for this run (containers without brew or micromamba). One failed phase never stops the others; any failure makes the exit code 1.

**Passwordless ssh between the computers.** `setup/ssh-keys.txt` lists one public key per computer. The keys phase appends every listed key to `~/.ssh/authorized_keys` (never removing anything) and appends this computer's own `~/.ssh/id_ed25519.pub` and `id_ecdsa.pub` to the list, which the next dotfiles phase commits; so a computer that has synced once can log into every other synced computer without a password. Make both keys, without a passphrase: `ssh-keygen -t ed25519` and `ssh-keygen -t ecdsa -b 256`; the university's MDM profile on the Studio accepts only ECDSA P-256 keys (`/etc/ssh/sshd_config.d/01-mscp-sshd.conf`), ed25519 is for everything else. Hosts that do not run the sync (the cluster disallows keys; the NAS) still need `ssh-copy-id`.

- **Dotfiles** auto-commit modified *tracked* files only, `pull --rebase`, then push, and only on branch `main`. A rebase conflict is aborted and reported (fix with `yadm pull --rebase origin main`); offline, it commits locally and skips pull/push.
- **Packages:** Brewfiles per class (Linux: the tool environment). Installed packages in no Brewfile are reported as extras, never removed. Anything wanted on every Mac goes into a Brewfile; `setup/extras.txt` lists what some computers may keep without a warning, and `converge adopt extras` appends this computer's current extras to it (the next sync commits and pushes the file). Casks present outside Homebrew are informational.
- **Defaults:** the saved snapshot is applied every day, so run `mac-settings save` to keep a preference change (Magnet also syncs itself through iCloud).
- **Hotkeys:** runs the hotkeys repo's clash checker, then checks that Karabiner is really applying the tracked `karabiner.json`: app installed, daemon running, file reloaded since its last edit without errors, and at least one keyboard grabbed (Input Monitoring). A warning here means a mapping is in git but not live on this Mac.
- **Apps:** `setup/apps.json` installs the home-made Mac apps from their GitHub releases. An app without releases (Hotkeys) is built from its grc-managed checkout instead, rerunning its `build` command whenever that checkout's commit changes; a commit on main is what propagates, as with `s`. Every other GUI app is declared in `setup/declared/apps.txt` (see Declared).
- Run the first sync on a new Mac in a terminal; cask installs may exceed the timeout under launchd.
- State and log: `~/.local/state/dotfiles/sync/last.json` and `sync.log`. The `com.git-repo-checker.active` LaunchAgent stays; sync fast-forwards git-repo-checker and refreshes `grc`, runs `grc active sync --apply`, then refreshes `s` from its checkout (tool refreshes are skipped where uv is absent).

**Layout.** `setup/layout.txt` lists the `~`-relative directories every computer gets. Bootstrap and sync create missing ones and report unplanned top-level entries without touching them; `<glob>  ignore` lines name entries other programs create (cloud sync folders), which are never created or reported. `<dir>  link:<target>` makes `~/<dir>` a symlink to `~/<target>` once that target exists, which is how every cloud mount appears under `~/cloud`. `<glob>  unlink` names the symlinks Google Drive and OneDrive re-create in `~` at every launch; each sync removes them (symlinks only, never a real folder), so `~/cloud` stays the one way in. Doctor flags literal home paths in tracked files: use `~` or `$HOME`.

**Seeing what is off.** `converge status` prints the last sync with calm phases first, then a "Needs attention" section: for every warn or failed phase, the details grouped (first 12 per group; `--all` for everything), then every pending recipe as a title and numbered steps. `converge sync --plan` previews what the next sync would change.

**Declared.** `setup/declared/<kind>.txt` lists what each computer should have, one entry per line with optional `class:laptop,studio` (default every class) and `allowed` (may be present, never installed). The kinds are `apps`, `agents` (`~/Library/LaunchAgents` labels) and `login-items` on the Mac, `apt` (packages installed on request), `snap`, `flatpak` and `gnome-extensions` on Linux. Each `apps` line also names its `source:` (brew, release, mas, manual, system; `cask:` when the token differs from the name, `url:` for a manual download). The declared phase compares each kind with what is present: a wanted entry that is missing is reported with the command that installs it (flatpaks and installed-but-disabled GNOME extensions are fixed by the sync itself; apt and snap need sudo, apps come from the packages and apps phases or by hand), and anything present that no line lists is reported as undeclared (Apple's own apps and vendor updater agents are ignored). The phase only reports, never removes. `converge adopt <kind>` appends this computer's undeclared entries as `allowed` lines under a dated comment; edit them into wanted lines, or delete the app, to keep the list honest.

**Recipes.** `setup/recipes.txt` holds the manual steps converge cannot take itself (logins, macOS permissions, App Store installs, sudo), each with checks on the snapshot (`converge fleet --keys`) or a phase's status, for example `check: gh.auth == jyesselm`. The recipes phase runs last: it snapshots the machine and lists every recipe whose check fails here, plus generated ones for declared entries only a person can install (`install-apps-magnet`) and for undeclared leftovers (`adopt-apps`). `converge status` and `converge recipes` print their numbered steps, `converge recipe NAME` one recipe's, and the pending list goes to the hub in `last.json`.

**Fleet.** Every real sync ends by checking in: it POSTs `{"last": last.json, "state": state.json}` to the hub, `https://home-gpu.tail2813f4.ts.net/converge/report` (`CONVERGE_HUB` overrides the base URL), then notes in its summary any machine that has not checked in for two days. A machine off the tailnet or with the hub down just prints `check-in skipped: <reason>`; the sync's exit code is unchanged. The cluster is the exception: Swan reaches only GitHub, so there the check-in force-pushes `last.json` and `state.json` as a one-commit branch `status/<class>-<host>` on the yadm remote, and the hub's bridge fetches those branches every 30 minutes. `converge fleet` asks the hub and prints one line per host, newest check-in first: host, class, age, exit code, `fixed N` (how many phases had to change something, recorded as `corrective` in `last.json`; a machine that keeps re-fixing the same thing stands out) and the phases that were not `ok`, plus `never` for a class in `setup/fleet.txt` that has not checked in yet. `--checkin` sends this machine's last result first, for example after a manual sync. The exit code is 0 only when every machine's last sync succeeded and none is stale; 2 when the hub does not answer (the message names the URL). The hub is `setup/hub.py serve` on home-gpu: stdlib Python on 127.0.0.1:8790, every report in `~/.local/state/dotfiles/hub.sqlite` for 90 days, `GET /fleet`, `/machines` and `/machine/<host>` as JSON. In a browser, `https://home-gpu.tail2813f4.ts.net/converge/` is the fleet page (the `converge fleet` table, the drift between machines from `setup/compare.yml`, `?all=1` for every key, and each machine's pending recipes) and each host links to `/machine/<host>`: its phases with details, declared entries missing or undeclared, pending recipes with numbered steps, and the snapshot keys where it differs from most machines of its profile. With `CONVERGE_TASKS=http://100.73.70.25:8767` (or `serve --tasks URL`) the hub also files each pending recipe as a chain `🖥 <host> · <title>` in the Tasks project Computers and marks it done when a later check-in passes; it is off by default, and the unit file carries the line commented out. It accepts a check-in only through `tailscale serve` (which adds the `Tailscale-User-Login` header) or, for tests, with `--trust-local`; `hub.py bridge-once` runs one bridge pass by hand. Install it once on home-gpu: yadm writes `~/.config/systemd/user/converge-hub.service` there (a template alternate, since systemd rejects a symlinked unit), then `systemctl --user daemon-reload && systemctl --user enable --now converge-hub`; `tailscale serve` needs root once, `sudo tailscale set --operator=$USER`, then `tailscale serve --bg --set-path /converge http://127.0.0.1:8790` (the existing `/` mapping stays).

**Differences.** Git makes the tracked files identical everywhere, so what still differs between computers is untracked state. Each sync therefore also writes `state.json`, a snapshot of this computer's effective state, and sends it with the check-in: OS, git identity, `gh` login, SSH keys, versions of every doctor tool and `uv` tool, HEAD of every grc-managed checkout (`+dirty` when uncommitted), every brew formula and cask version, every app in /Applications with its version, Karabiner version, profile, grabbed keyboards and problems, the fn-key setting, every macOS symbolic hotkey (screenshots, Spotlight, Mission Control), the live values of the allowlisted preferences, launch agents, fonts and login items. `converge fleet --diff` asks the hub for every machine's newest snapshot and prints only the keys whose values differ, one column per machine; a machine with no keys in a group (a Linux box has no `apps.*`, nor does the server) is left out of that group's rows. `setup/compare.yml` is the tracked list of which keys to compare (`compare:` globs) and which may legitimately differ (`ignore:`); `--all` ignores it and shows every difference, and `converge fleet --keys` lists everything the snapshot holds so you can pick. The daily check-in notes how many compared keys differ. Permissions such as Input Monitoring are not readable, so they show up indirectly: Karabiner grabbing no keyboard.

**Classes.** `yadm config local.class laptop|studio|server|linux|cluster` selects `##class.<x>` alternates and the Brewfiles. `server` (the Plex Mac) gets the terminal Brewfile plus Karabiner, no desktop apps, home-made apps or preference restores. Each class has its own repo list: `~/.config/git-repo-checker/active.yml##class.<x>` where one exists, otherwise `active.yml##default`; yadm links `active.yml` to the matching file, so the Plex server syncs only the repos listed for it (none until you add some).

**Onboard a computer.** Run this at the machine's own terminal (ssh or sitting at it); nothing reaches in from elsewhere. Prerequisites are the ones above: Mac needs Homebrew, `brew install yadm python`; Linux needs Python 3.9+, Git and yadm; on Swan load the Git/Anaconda modules first.

```sh
yadm clone --no-bootstrap https://github.com/jyesselm/dotfiles.git   # already cloned: yadm pull
yadm config local.class studio          # laptop | studio | server | linux | cluster
~/.config/yadm/bootstrap --plan         # read-only preview; fix any reported conflict first
yadm bootstrap                          # terminal environment; Mac Studio: add --desktop afterwards
converge sync --plan            # read-only preview of the daily sync
converge sync                   # first real sync, in a terminal; checks this machine in
converge schedule               # daily 10:00 launchd job or crontab line
converge fleet                  # this machine now appears in the hub's fleet
```

Then the manual steps under "Finish once per computer": Nerd Font on the terminal client, `gh auth login` and Atuin, and any permission prompts macOS raises during the first sync. On Swan, `--install-schedule` prints "schedule skipped" when crontab is unavailable; run `converge sync` by hand there, and it still checks in through its status branch. Every other machine checks in over Tailscale; `converge fleet` needs the tailnet too, so on Swan it exits 2.

## Validation

Run `python3 -m unittest discover -s ~/.config/yadm/setup -v` for isolated filesystem/mocked-process tests. `setup/testing/` (see its README) runs the same suite in Docker on Python 3.9 and 3.14, a hub with three clients end to end, and a fresh Linux VM (OrbStack) and macOS VM (Tart) through clone, bootstrap, sync, hub check-in and schedule. Package managers and desktop applications are never run by the test suite. Mac/Linux plans and the current Mac doctor can be checked without installing anything. A full fresh Linux dependency solve still depends on conda-forge availability and that machine's runtime.

## Your Mac preferences

The separate `~/.local/bin/mac-settings save` command captures selected current Mac preferences into yadm. On a new Mac, preview with `mac-settings plan` and explicitly apply with `mac-settings restore`; every restore first saves a rollback snapshot. Regular bootstrap never applies these system preferences; `converge sync` re-applies the saved snapshot daily. See `~/.config/yadm/macos/README.md` for coverage, app exports, and limitations.

### Hourly search indexing on the MacBook

The laptop-only `Library/LaunchAgents/com.yesselman.search-cli-prewarm.plist##class.laptop` runs `s warm` every 3,600 seconds at low priority while logged in. It is specific to this computer’s executable path; other computers need their own matching job. After restoring this Mac’s dotfiles, load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yesselman.search-cli-prewarm.plist`. It does not run immediately on load. Logs are in `~/Library/Logs/search-cli/`; create that directory before loading the job on a fresh installation.

### Media stack on the Plex server

Seerr, Radarr, Sonarr, Prowlarr, qBittorrent behind a NordVPN gluetun tunnel, the Homepage dashboard and Uptime Kuma run in OrbStack from `~/.config/media-stack/compose.yml`; Plex stays native. Setup, everyday commands and the move to Linux are in `~/.config/media-stack/README.md`.

## Chrome Home across computers

`~/.config/search-cli/dashboard.json` is tracked by yadm: it carries pinned
bookmarks, service URLs, and the weather location. It contains no Raindrop token,
Chrome history, or generated search index. Treat this as shared configuration:
after editing shortcuts in Home, commit that file with yadm on the source
computer, push, and pull on the other computer. Uncommitted edits on both
computers require resolving the normal Git conflict; sync does not overwrite them.

On a macOS or Linux desktop with the dotfiles and uv installed:

```sh
converge chrome-home --plan
converge chrome-home
# Follow the printed Load unpacked path in chrome://extensions, then:
converge chrome-home --extension-id THE_ID_SHOWN_ON_THIS_COMPUTER
```

The command installs Search CLI from its existing developing checkout (clones if
missing) and prints the extension directory. It does not force checkout changes,
reload Chrome, grant browser permissions, or store credentials. The second command
registers the native bridge with this machine's Python executable and Chrome ID.
Chrome IDs may differ between computers for unpacked extensions. After extension
updates, use Reload on its Chrome extensions card. Enable history separately on
each computer; connect Raindrop with a device-local token. Tailscale services need
Tailscale connectivity, and localhost links refer to each computer itself.

The Chrome dashboard must exist in the search-cli checkout; until its feature
branch is merged/pushed, a new clone of main may not have the latest interface.

### Search desktop convergence

On Mac desktops/laptops, `converge sync` now converges the Search GUI as part of
its apps phase after repository and package updates: it writes the Search CLI app
bundle, binds F4 and Apple's Spotlight key in the active Karabiner profile, and
retires the old background GUI when the source fingerprint changes. The next F4
loads current code; unchanged syncs leave the running app alone. Only a process
identified by Search's resident lock, current UID, and GUI command is stopped;
indexers and terminal searches are untouched. Other Karabiner rules/profiles are
preserved and changed configuration is backed up. Missing Karabiner setup or a
resident that will not exit is reported as a warning, not silent success.
`converge setup --search` and `converge chrome-home` apply the same desktop steps.
Once F4 is configured, convergence also clears the obsolete Cmd+, hotkey from
Alfred's exact `Search CLI Launcher` workflow in its configured sync folder.
It backs up the plist and preserves the workflow, other triggers, and all other
workflows. This migration is Mac-only and idempotent.
