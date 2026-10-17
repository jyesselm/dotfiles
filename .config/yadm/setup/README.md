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
converge status                          # last sync: each warning's details and how to clear it
converge adopt-extras                    # Mac: allow this computer's brew extras (appends to setup/extras.txt)
converge schedule                        # daily launchd job (Mac) or crontab line (Linux)
converge fleet                           # last check-in of every machine
converge checkin                         # push this machine's last sync result now, then the fleet view
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

The pending search-cli ↔ Yazi integration is a separate feature; this bootstrap installs their current configurations and tools.

## Daily sync

`converge sync` runs these phases in order: layout, dotfiles, packages, repos, apps, defaults, hotkeys, doctor. Preview with `--plan` (read-only). One failed phase never stops the others; any failure makes the exit code 1.

- **Dotfiles** auto-commit modified *tracked* files only, `pull --rebase`, then push, and only on branch `main`. A rebase conflict is aborted and reported (fix with `yadm pull --rebase origin main`); offline, it commits locally and skips pull/push.
- **Packages:** Brewfiles per class (Linux: the tool environment). Installed packages in no Brewfile are reported as extras, never removed. Anything wanted on every Mac goes into a Brewfile; `setup/extras.txt` lists what some computers may keep without a warning, and `converge adopt-extras` appends this computer's current extras to it (the next sync commits and pushes the file). Casks present outside Homebrew are informational.
- **Defaults:** the saved snapshot is applied every day, so run `mac-settings save` to keep a preference change (Magnet also syncs itself through iCloud).
- **Apps:** `setup/apps.json` installs the home-made Mac apps from their GitHub releases. An app without releases (Hotkeys) is built from its grc-managed checkout instead, rerunning its `build` command whenever that checkout's commit changes; a commit on main is what propagates, as with `s`.
- Run the first sync on a new Mac in a terminal; cask installs may exceed the timeout under launchd.
- State and log: `~/.local/state/dotfiles/sync/last.json` and `sync.log`. The `com.git-repo-checker.active` LaunchAgent stays; sync fast-forwards git-repo-checker and refreshes `grc`, runs `grc active sync --apply`, then refreshes `s` from its checkout (tool refreshes are skipped where uv is absent).

**Layout.** `setup/layout.txt` lists the `~`-relative directories every computer gets. Bootstrap and sync create missing ones and report unplanned top-level entries without touching them; `<glob>  ignore` lines name entries other programs create (cloud sync folders), which are never created or reported. `<dir>  link:<target>` makes `~/<dir>` a symlink to `~/<target>` once that target exists, which is how every cloud mount appears under `~/cloud`. Doctor flags literal home paths in tracked files: use `~` or `$HOME`.

**Seeing what is off.** `converge status` prints the last sync with calm phases first, then a "Needs attention" section: for every warn or failed phase, the details grouped (first 12 per group; `--all` for everything) and the edit or command that clears it. `converge sync --plan` previews what the next sync would change.

**Fleet.** Every real sync ends by checking in: it force-pushes its `last.json` as a one-commit branch `status/<class>-<host>` on the yadm remote, then warns in its summary about any machine that has not checked in for two days. No machine needs to reach another; each only needs GitHub. `converge fleet` fetches those branches on any machine and prints one line per machine, newest check-in first: host, class, age, exit code and the phases that were not `ok`, plus `never` for a class in `setup/fleet.txt` that has not checked in yet. `--checkin` pushes this machine's last result first, for example after a manual sync. The exit code is 0 only when every machine's last sync succeeded and none is stale.

**Classes.** `yadm config local.class laptop|studio|linux|cluster` selects `##class.<x>` alternates and the Brewfiles.

**Onboard a computer.** Run this at the machine's own terminal (ssh or sitting at it); nothing reaches in from elsewhere. Prerequisites are the ones above: Mac needs Homebrew, `brew install yadm python`; Linux needs Python 3.9+, Git and yadm; on Swan load the Git/Anaconda modules first.

```sh
yadm clone --no-bootstrap https://github.com/jyesselm/dotfiles.git   # already cloned: yadm pull
yadm config local.class studio          # laptop | studio | linux | cluster
~/.config/yadm/bootstrap --plan         # read-only preview; fix any reported conflict first
yadm bootstrap                          # terminal environment; Mac Studio: add --desktop afterwards
converge sync --plan            # read-only preview of the daily sync
converge sync                   # first real sync, in a terminal; checks this machine in
converge schedule               # daily 10:00 launchd job or crontab line
converge fleet                  # this machine now appears on every computer
```

Then the manual steps under "Finish once per computer": Nerd Font on the terminal client, `gh auth login` and Atuin, and any permission prompts macOS raises during the first sync. On Swan, `--install-schedule` prints "schedule skipped" when crontab is unavailable; run `converge sync` by hand there, and it still checks in. The sync and `--fleet` only need GitHub, so a machine behind a firewall or off Tailscale works the same.

## Validation

Run `python3 -m unittest discover -s ~/.config/yadm/setup -v` for isolated filesystem/mocked-process tests. Package managers and desktop applications are never run by the test suite. Mac/Linux plans and the current Mac doctor can be checked without installing anything. A full fresh Linux dependency solve still depends on conda-forge availability and that machine's runtime.

## Your Mac preferences

The separate `~/.local/bin/mac-settings save` command captures selected current Mac preferences into yadm. On a new Mac, preview with `mac-settings plan` and explicitly apply with `mac-settings restore`; every restore first saves a rollback snapshot. Regular bootstrap never applies these system preferences; `converge sync` re-applies the saved snapshot daily. See `~/.config/yadm/macos/README.md` for coverage, app exports, and limitations.

### Hourly search indexing on the MacBook

The laptop-only `Library/LaunchAgents/com.yesselman.search-cli-prewarm.plist##class.laptop` runs `s warm` every 3,600 seconds at low priority while logged in. It is specific to this computer’s executable path; other computers need their own matching job. After restoring this Mac’s dotfiles, load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yesselman.search-cli-prewarm.plist`. It does not run immediately on load. Logs are in `~/Library/Logs/search-cli/`; create that directory before loading the job on a fresh installation.
