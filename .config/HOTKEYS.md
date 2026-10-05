# Hotkey layers

One modifier per layer. A new binding must fit a row here or it does not get added.

| Modifier | Owner | Scope | Details |
|---|---|---|---|
| Caps Lock (Hyper = ⇧⌃⌥⌘) | Karabiner | Launch apps, place windows, clipboard | below |
| ⌃⌥ | Magnet | Window placement, system-wide | below |
| ⌘ | macOS + each app | Native in-app commands | untouched |
| ⌘Tab (Contexts) / ⌘` | Contexts, macOS | Switch apps / windows | below |
| ⌃Space | tmux | Leader | `tmux/shortcuts.txt` |
| ⌃h/j/k/l | tmux, Neovim, Zed | Move between panes, identical everywhere | `nvim/KEYBINDINGS.md`, `zed/keymap.json` |
| Left ⌥ | tmux, zsh | Sessions; word motion; fzf cd | `tmux/shortcuts.txt`, `~/.zsh/keybindings.zsh` |
| Space | Neovim | Leader | `nvim/KEYBINDINGS.md` |

Tap Caps Lock alone = Escape. F3 = screenshot to clipboard.

## Hyper + letter → app  (`karabiner/karabiner.json`)

| Key | App | | Key | App |
|---|---|---|---|---|
| A | Claude | | M | Messages |
| B | Chrome (browser) | | O | Obsidian |
| C | Cursor | | S | Slack |
| E | Finder (explorer) | | T | iTerm (terminal) |
| G | ChatGPT | | W | Word |
| H | Google Chat | | V | Alfred clipboard history |

Hyper + ←→↑↓ = halves · U I J K = quarters · Return = maximize · Delete = restore (all forwarded to Magnet).

Free: D F L N P Q R X Y Z, digits.

## ⌃⌥ + key → window placement (Magnet, native keys)

Arrows = halves · U I J K = quarters · D F G = thirds · E R T = two-thirds ·
Return = maximize · C = center · Delete = restore · ⌘⌃⌥ ←/→ = move to display.

## Switching without the mouse

- ⌘Tab = Contexts' app switcher (sidebar list). ⌘` next window of this app, ⇧⌘` previous, ⌃↓ all windows of this app.
- ⇧⌘/ in any app searches menus; type the command name and press Return.

## Chrome: Vimium (`yadm/files/vimium/`)

`f` click a link · `F` open in new tab · `H` / `L` prev/next tab · `J` / `K` page down/up ·
`x` close tab · `X` reopen · `o` / `O` open URL or bookmark here/new tab · `T` search tabs ·
`/` find · `gi` focus first input · `⌃o` / `⌃i` back/forward · `?` show all.
Settings sync through Chrome Sync; the dotfiles copy is a backup, restore via Vimium Options → Backup and Restore.

## Retired

Rectangle and BetterTouchTool (removed 2026-10-05): both bound ⌃⌥ and clashed with Magnet.
