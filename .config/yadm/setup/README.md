# New-computer setup

One entry point: **`yadm bootstrap`** installs the terminal environment and restores plugin dependencies. Desktop apps, rich file previews, private games and search-cli are explicit options.

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

After cloning, use either `~/.config/yadm/bootstrap` or `~/.local/bin/dotfiles-setup`. Open a new terminal to get the shorter `dotfiles-setup` command on PATH.

```sh
dotfiles-setup --plan                       # no changes, installs or downloads
dotfiles-setup --doctor                     # read-only health check
dotfiles-setup --previews                   # PDF / SVG / archive / video previews
dotfiles-setup --desktop                    # Mac: iTerm2, VS Code, Cursor, Obsidian
gh auth login
dotfiles-setup --games                      # private tmux-dojo and nvim-dojo
dotfiles-setup --search                     # search-cli, default GitHub branch
dotfiles-setup --skip-packages --skip-nvim   # shell/menu/config setup only
```

Flags combine, for example `dotfiles-setup --plan --desktop --previews --games --search`. To check optional components, include them with doctor: `dotfiles-setup --doctor --games --search --previews`.

**Use the wrapper for options.** The installed yadm version executes its bootstrap without forwarding arguments; `yadm bootstrap --plan` is not the documented interface here.

## What it does

- Keeps the tracked Yazi theme, icons, bindings and zoxide configuration as the source of truth.
- Installs pinned Oh My Zsh and its two configured community plugins without running an installer that rewrites `.zshrc` or changes your login shell.
- Uses the existing pinned tmux setup and generated menu.
- Runs Neovim's `Lazy! restore` against the committed lockfile, not a bulk plugin upgrade. Plugin builds can download parsers or language servers and need a working compiler/toolchain.
- Links VS Code/Cursor settings only for installed apps or an explicitly requested desktop setup. Existing settings receive unique backup names; earlier backups are never overwritten.
- Reports missing tools, incompatible versions and failed stages with a nonzero exit code. The final message says “incomplete” if a required step fails.

Existing shell/plugin/private-repository checkouts are retained, including local changes. Bootstrap does not pull or reset those checkouts. To update a game, use `git pull --ff-only` then its `install.sh` in `~/.local/share/dotfiles/repos/<name>` (Neovim uses `--lazy`). Private game source stays outside the public yadm repository.

Search CLI is installed into a uv-managed tool environment from its default branch. It does not copy a developer's uncommitted checkout, database, vaults or papers. The portable shell helper is loaded only when that optional checkout exists. Configure your search roots/vaults on the new machine.

## Finish once per computer

- Open a new terminal; select JetBrainsMono Nerd Font and enable Option-as-Esc if you want Option tmux shortcuts.
- Log into GitHub/Atuin and any desktop apps as needed. No credentials or shell history are copied by bootstrap.
- Run `dotfiles-setup --doctor`. Use `:checkhealth` in Neovim for language-server/parser details.
- If Git still expects `cursor --wait` but you chose terminal-only setup, use `git config --global core.editor nvim`.
- A local override in `~/.zsh/local.zsh` can configure host-specific paths. Bootstrap preserves it.

The pending search-cli ↔ Yazi integration is a separate feature; this bootstrap installs their current configurations and tools.

## Validation

Run `python3 ~/.config/yadm/setup/test_setup.py` for isolated filesystem/mocked-process tests. Package managers and desktop applications are never run by the test suite. Mac/Linux plans and the current Mac doctor can be checked without installing anything. A full fresh Linux dependency solve still depends on conda-forge availability and that machine's runtime.

## Your Mac preferences

The separate `~/.local/bin/mac-settings save` command captures selected current Mac preferences into yadm. On a new Mac, preview with `mac-settings plan` and explicitly apply with `mac-settings restore`; every restore first saves a rollback snapshot. Regular bootstrap never applies these system preferences automatically. See `~/.config/yadm/macos/README.md` for coverage, app exports, and limitations.
