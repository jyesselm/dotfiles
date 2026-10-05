# Hotkey layers

One modifier per layer. A new binding must fit a row here or it does not get added.
Search all of this from anywhere with **Hyper+/** (Alfred, keyword `hk`).

| Modifier | Owner | Scope | Details |
|---|---|---|---|
| Caps Lock (Hyper = ⇧⌃⌥⌘) | Karabiner | Launch apps, place windows, clipboard, search | below |
| ⌃⌥ | Magnet | Backend for Hyper placement only; never used directly | — |
| ⌘ | macOS + each app | Native in-app commands | untouched |
| ⌘Tab (Contexts) / ⌘` | Contexts, macOS | Switch apps / windows | below |
| ⌃Space | tmux | Leader | `tmux/shortcuts.txt` |
| ⌃h/j/k/l | tmux, Neovim, Zed | Move between panes, identical everywhere | `nvim/KEYBINDINGS.md`, `zed/keymap.json` |
| Left ⌥ | tmux, zsh | Sessions; word motion; fzf cd | `tmux/shortcuts.txt`, `~/.zsh/keybindings.zsh` |
| Space | Neovim | Leader | `nvim/KEYBINDINGS.md` |

## Hyper: apps  (`karabiner/karabiner.json`)

| Key | Action |
|---|---|
| Hyper+A | Claude |
| Hyper+B | Chrome (browser) |
| Hyper+C | Cursor |
| Hyper+E | Finder (explorer) |
| Hyper+G | ChatGPT |
| Hyper+H | Google Chat |
| Hyper+M | Messages |
| Hyper+O | Obsidian |
| Hyper+S | Slack |
| Hyper+T | iTerm (terminal) |
| Hyper+W | Word |
| Hyper+V | Alfred clipboard history |
| Hyper+/ | Search hotkeys (this sheet, tmux, Neovim) |
| Caps Lock tap | Escape |
| F3 | Screenshot to clipboard |

Free: D L Q R X Y Z, 7 8 9 0.

## Hyper: window placement  (forwarded to Magnet)

| Key | Action |
|---|---|
| Hyper+← → ↑ ↓ | Left / right / top / bottom half |
| Hyper+U I J K | Top-left / top-right / bottom-left / bottom-right quarter |
| Hyper+F | Center (keeps size) |
| Hyper+1 2 3 | Left / center / right third |
| Hyper+4 5 6 | Left / center / right two-thirds |
| Hyper+numpad 1–6 | Sixths, left to right (full keyboard only) |
| Hyper+N / P | Move to next / previous display |
| Hyper+Return | Maximize |
| Hyper+Delete | Restore |

Magnet's own ⌃⌥ bindings stay enabled: Karabiner forwards each Hyper chord to one of them. Don't bind ⌃⌥ elsewhere.

## Switching without the mouse

| Key | Action |
|---|---|
| ⌘Tab | Contexts app switcher (sidebar list) |
| ⌘` | Next window of this app |
| ⇧⌘` | Previous window of this app |
| ⌃↓ | All windows of this app |
| ⇧⌘/ | Search any app's menus; type the command, Return runs it |
| ⌘Space | Alfred |
| ⇧⌘S | Alfred snippets |

Alfred's live preferences (workflows, these hotkeys) sync via `~/Library/CloudStorage/Dropbox/Alfred.alfredpreferences`; the copy under Application Support is unused.

## Chrome: Vimium  (`yadm/files/vimium/`)

| Key | Action |
|---|---|
| f | Click a link (hints) |
| F | Open link in new tab |
| H / L | Previous / next tab |
| J / K | Page down / up |
| x / X | Close / reopen tab |
| o / O | Open URL or bookmark here / in new tab |
| T | Search open tabs |
| / | Find in page |
| gi | Focus first input |
| ⌃o / ⌃i | Back / forward |
| ? | Show all Vimium keys |

Settings sync through Chrome Sync; the dotfiles copy is a backup, restore via Vimium Options → Backup and Restore.

## Retired

Rectangle and BetterTouchTool (removed 2026-10-05): both bound ⌃⌥ and clashed with Magnet.
