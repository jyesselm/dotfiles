# Shared tmux setup

The bottom bar has two rows: sessions with active-pane context, then windows
with the clock and menu hint. The active pane has a cyan ACTIVE label and a
lighter background. Ctrl+Space changes only the session-row label to red PREFIX while waiting
for the next key; the rest of the colors stay unchanged.

## Set up another computer

Install **tmux 3.6 or newer**, **fzf**, and **git**. On macOS:

```sh
brew install tmux fzf git
```

Then sync and bootstrap:

```sh
yadm pull --ff-only
yadm bootstrap
```

On Linux, use the system's package manager for these dependencies; verify
`tmux -V` is at least 3.6. The setup script does not install system packages.
If only the tmux portion of bootstrap is needed:

```sh
sh ~/.config/tmux/setup.sh
```

Open a new terminal and run `tmux`. A bare invocation opens or creates `work`.
Inside tmux it switches to `work` without nesting. Explicit tmux arguments
keep their normal behavior. The first automatic restoration returns to `work`.
The function lives in `.zsh/functions.zsh`, which the shared `.zshrc` loads.
For an already-open zsh, open a fresh shell to pick up the function.

If tmux is already running, reload after pulling:

```sh
tmux source-file ~/.tmux.conf
```

Session contents and running processes are local to each computer. They are
not shared through yadm. Resurrect/Continuum save each computer's own sessions.
On iTerm2, configure **left Option = Esc+** for the Option shortcuts. On Linux,
these are Alt shortcuts, provided the terminal/desktop does not intercept them.

## Navigation

- Ctrl+Space, then `?`: which-key menu (`s` sessions, `w` windows, `p` panes).
- From that menu, `?`: full shortcut cheat sheet; `q` closes the sheet.
- Ctrl+Space, then `f`: fuzzy popup switcher.
- Ctrl+Space, then `w`: original tree picker.
- Option/Alt+Tab: last session; Option/Alt+n or p: next/previous session.
- Option/Alt+w or r: work/remotes. `remotes` must exist first.
- Ctrl+h/j/k/l: move between panes and Neovim splits.

## Which-key ownership and updates

`which-key.yaml` is the editable menu source. `which-key.tmux` is the matching
generated menu, tracked so Python is not required just to run it. Both must be
updated together. Generate after editing:

```sh
python3 ~/.tmux/plugins/tmux-which-key/plugin/build.py \
  ~/.config/tmux/which-key.yaml ~/.config/tmux/which-key.tmux
tmux source-file ~/.tmux.conf
```

The upstream which-key plugin and its bundled PyYAML submodule are installed
by bootstrap. `sync-which-key.sh` copies the versioned menu into its ignored
local configuration files before TPM loads it. Automatic rebuilding is disabled
for predictable startup; the generated file is authoritative at runtime.

The generated menu derives from alexwforsythe/tmux-which-key:
https://github.com/alexwforsythe/tmux-which-key
Its MIT copyright and license are included in `which-key.LICENSE`.

`plugins.lock` pins new installs to the versions tested with this configuration.
Existing plugin checkouts are preserved. Plugin updates remain available through
TPM (`leader + U`). Plugin repositories, saved sessions, and machine-specific
shell settings are not tracked by this change.
