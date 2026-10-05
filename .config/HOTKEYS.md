# Hotkey layers

One modifier per layer. A new binding must fit a row here or it does not get added.

| Modifier | Owner | Scope | Details |
|---|---|---|---|
| Caps Lock (Hyper = ⇧⌃⌥⌘) | Karabiner | Launch / focus apps, system-wide | below |
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
| H | Google Chat | | | |

Free: D F I J K L N P Q R U V X Y Z, digits, arrows.

## ⌃⌥ + key → window placement (Magnet)

Arrows = halves · U I J K = quarters · D F G = thirds · E R T = two-thirds ·
Return = maximize · C = center · Delete = restore · ⌘⌃⌥ ←/→ = move to display.

## Switching without the mouse

- ⌘Tab = Contexts' app switcher (sidebar list). ⌘` next window of this app, ⇧⌘` previous, ⌃↓ all windows of this app.
- ⇧⌘/ in any app searches menus; type the command name and press Return.

## Retired

Rectangle and BetterTouchTool (removed 2026-10-05): both bound ⌃⌥ and clashed with Magnet.
