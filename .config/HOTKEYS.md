# Hotkey layers

One job per layer. A new binding must fit a row here or it does not get added.
Search all of this from anywhere with **Hyper+/** (Alfred, keyword `hk`).

| Layer | Job | Rule |
|---|---|---|
| Hyper (Caps) | System: apps, windows, launchers | Letters open apps; arrows, numbers, Return, Delete place windows |
| ⌘ | Inside an app | Native Mac keys, plus overrides with one meaning everywhere: ⌘[ ] tabs, ⌘Space tmux (terminals), and the switcher: **⌘P in code tools** (VS Code, Cursor, tmux, Neovim), **⌘K in browser and chat** |
| ⌃ (Right ⌘) | Terminal and Vim | Shell, tmux, Neovim only; in terminals ⌘h/j/k/l is the way to move panes |
| Alfred keyword | Anything used rarely | No hotkey: type the word in Hyper+Space (`snip`, `1p`, `hk`) |

| Modifier | Owner | Scope | Details |
|---|---|---|---|
| Caps Lock (Hyper = ⇧⌃⌥⌘) | Karabiner | Launch apps, place windows, clipboard, search | below |
| ⌃⌥ | Magnet | Backend for Hyper placement only; never used directly | — |
| ⌘ | macOS + each app | Native in-app commands | untouched, except ⌘[ ] (below) |
| ⌘Tab (Contexts) / ⌘` | Contexts, macOS | Switch apps / windows | below |
| Right ⌘ | Karabiner | Always ⌃, so Ctrl is a thumb key (⌃C, ⌃R, Vimium ⌃o/⌃i) | below |
| ⌃Space (⌘Space in terminals) | tmux | Leader | `tmux/shortcuts.txt` |
| ⌃h/j/k/l (⌘h/j/k/l in terminals) | tmux, Neovim, Zed | Move between panes, identical everywhere | `nvim/KEYBINDINGS.md`, `zed/keymap.json` |
| Left ⌥ | tmux, zsh | Sessions; word motion; fzf cd | `tmux/shortcuts.txt`, `~/.zsh/keybindings.zsh` |
| Space | Neovim | Leader | `nvim/KEYBINDINGS.md` |

## Hyper: apps  (`karabiner/karabiner.json`)

| Key | Action |
|---|---|
| Hyper+A | Claude |
| Hyper+B | Chrome (browser) |
| Hyper+C | Cursor |
| Hyper+D | Tasks (do) |
| Hyper+E | Finder (explorer) |
| Hyper+G | ChatGPT |
| Hyper+H | Google Chat |
| Hyper+M | Messages |
| Hyper+N | notes |
| Hyper+O | Obsidian |
| Hyper+S | Slack |
| Hyper+T | iTerm (terminal) |
| Hyper+W | Word |
| Hyper+V | Alfred clipboard history |
| Hyper+L | 1Password login search (Alfred `1p`): ↩ open site and fill · ⌘↩ copy password · ⌥↩ copy username · ⌃↩ view in 1Password · ⇧↩ copy one-time code |
| Hyper+/ | Search hotkeys (this sheet, tmux, Neovim) |
| Hyper+Space | Alfred |
| Hyper+[ / ] | Previous / next window of this app |
| Hyper+X | All windows of this app (sends ⌃↓) |
| Caps Lock tap | Escape |
| F3 | Screenshot to clipboard |

Free: P Q R Y Z, 7 8 9 0.

## Hyper: window placement  (forwarded to Magnet)

| Key | Action |
|---|---|
| Hyper+← → ↑ ↓ | Left / right / top / bottom half |
| Hyper+U I J K | Top-left / top-right / bottom-left / bottom-right quarter |
| Hyper+F | Center (keeps size) |
| Hyper+1 2 3 | Left / center / right third |
| Hyper+4 5 6 | Left / center / right two-thirds |
| Hyper+numpad 1–6 | Sixths, left to right (full keyboard only) |
| Hyper+. / , | Move to next / previous display |
| Hyper+Return | Maximize |
| Hyper+Delete | Restore |

Magnet's own ⌃⌥ bindings stay enabled: Karabiner forwards each Hyper chord to one of them. Don't bind ⌃⌥ elsewhere.

## Switching without the mouse

| Key | Action |
|---|---|
| ⌘Tab | Contexts app switcher (sidebar list). Quick tap = jump back to the last app; hold ⌘ and tap Tab to go further back; ⇧ reverses |
| Hyper+] / Hyper+[ | Next / previous window of this app (Karabiner sends ⌘` / ⇧⌘`) |
| Hyper+X | All windows of this app |
| ⇧⌘/ | Search any app's menus; type the command, Return runs it |
| ⌘[ / ⌘] | Previous / next tab, every app (Karabiner swap) |
| ⇧⌘[ / ⇧⌘] | What ⌘[ ] did natively: back/forward, outdent/indent, iTerm panes |
| ⌘K (Chrome) | Search open tabs (Karabiner sends ⇧⌘A) |
| ⌘P (terminals) | tmux: fuzzy switch session/window · Neovim: smart open (Karabiner sends F12) |
| Hyper+Space | Alfred |
| ⌘Space | tmux leader in terminals (Karabiner sends ⌃Space) |
| ⌘h/j/k/l | In terminals: pane moves (Karabiner sends ⌃); also over SSH |
| ⌘\ | 1Password: fill login into the focused field, every app including terminals |
| `snip` in Alfred | Snippets (no hotkey, so ⇧⌘S stays Save As) |

Alfred's live preferences (workflows, these hotkeys) sync via `~/Library/CloudStorage/Dropbox/Alfred.alfredpreferences`; the copy under Application Support is unused.

## Chat apps: Claude + ChatGPT (same keys in both)

| Key | Action |
|---|---|
| ⌘K | Search chats (Karabiner swaps Claude's ⌘K/⇧⌘K so this matches ChatGPT) |
| ⇧⌘K | Claude only: command palette |
| ⌘N | New chat / session |
| ⌘[ / ⌘] | Previous / next chat (global Karabiner swap) |
| ⇧⌘[ / ⇧⌘] | Back / forward |
| ⌘B | Toggle sidebar (ChatGPT's own is ⇧⌘S; Karabiner maps ⌘B to it) |
| ⌘J | Bottom panel (Claude terminal / ChatGPT panel) |
| ⌘W | Close chat |
| ⌘/ | Show every shortcut |

## Chrome: Vimium  (`yadm/files/vimium/`)

| Key | Action |
|---|---|
| f | Click a link (hints) |
| F | Open link in new tab |
| J / K | Page down / up |
| o / O | Open URL or bookmark here / in new tab |
| ⇧T | Search open tabs (or ⌘K, which works on every page) |
| / | Find in page |
| gi | Focus first input |
| ? | Show all Vimium keys |

Settings sync through Chrome Sync; the dotfiles copy is a backup, restore via Vimium Options → Backup and Restore.

## Retired

Rectangle and BetterTouchTool (removed 2026-10-05): both bound ⌃⌥ and clashed with Magnet.
