# Hotkey rules

The full, live list of every shortcut is the **Hotkeys** app (`~/local/code/web/hotkeys`), also searchable
from Alfred with **Hyper+/** (keyword `hk`). This file is only the rules; Hotkeys checks them
(Clashes, Shared verbs). The machine-readable copy is `rules` in `~/.config/hotkeys/config.json`.

## Layers: each modifier has one owner

| Layer | Owner | Holds | Never |
|---|---|---|---|
| ⌘ ⇧⌘ ⌥⌘ | the app in front | everything inside an app | anything global |
| Hyper (Caps; tap = Esc) | the system | letters open apps · arrows, UIJK, numbers, Return, Delete place windows · Space, /, L, V, Q, X, [ ] call tools | app-specific actions |
| ⌃⌥ | Magnet (backend) | only what Karabiner forwards from Hyper | pressed by hand |
| Leader (⌘Space in terminals → ⌃Space) | tmux | panes, windows, sessions | outside terminals |
| ⌘h/j/k/l in terminals (→ ⌃) | tmux, Neovim | move between panes | — |
| Right ⌘ | Karabiner | always ⌃ (a thumb Ctrl) | — |
| Alfred keyword | rare things | anything used less than daily | a hotkey |

## Shared verbs: same key, same meaning, every app

| Key | Verb | Notes |
|---|---|---|
| ⌘K | Jump to (tab, chat, page, channel, folder) | Karabiner fixes Chrome (tab search), Claude, Finder (Go to Folder) |
| ⌘P | Open / switch in code tools and terminals | terminals: tmux switcher or Neovim smart open (Karabiner sends F12) |
| ⌘] / ⌘[ | Next / previous tab | Karabiner swap, every app |
| ⇧⌘] / ⇧⌘[ | Forward / back (iTerm: panes, editors: indent) | what ⌘[ ] did natively |
| ⌘F | Find | |
| ⌘T / ⇧⌘T | New tab / reopen closed tab | |
| ⌘W | Close tab | |
| ⌘N | New (chat, message, page, window) | |
| ⌘\ | Fill password (1Password) | the one global key on ⌘, on purpose |
| ⌘/ | Show keyboard shortcuts | |

## Deliberate exceptions

- Global keys allowed on ⌘ (`rules.globalOnCmd`): ⌘\ 1Password fill · ⌘Tab Contexts · ⌘` ⇧⌘` macOS next window · ⇧⌘/ search app menus.
- Native meanings left alone: Word ⌘K inserts a link · Slack ⇧⌘T Threads · iTerm ⇧⌘[ ] switch panes.

## Adding a shortcut

1. Used daily? If not, make it an Alfred keyword or find it with ⇧⌘/ (search the app's menus).
2. Pick the row in the layer table; global things go on Hyper, never on ⌘.
3. If it is a shared verb, use the key above (Karabiner can fix one app that disagrees).
4. Rescan Hotkeys: Clashes must stay at 0.

## Linux (home-gpu)

Same keys, same meanings. Toshy plays Karabiner, GNOME plays Magnet and `open -a`. Both are set from
`~/.config/hotkeys/linux/` by `converge sync`, so edit those files, not the live configs.

- Physical keys on a PC keyboard: Alt is ⌘, Win is ⌥, Ctrl is ⌃, Caps is Hyper (tap = Esc).
- Hyper+letter focuses or launches an app through the dock order in `gnome.dconf`, so keep the two lists aligned.
- Not on Linux: Hyper+1-6, numpad sixths (no tiling-assistant keys), Hyper+S/M/W/H/D/N/Q/V/Space/`/`
  (the app isn't installed or there's no Linux equivalent), and ⌘, → `s gui`.

## Where things live

Karabiner `~/.config/karabiner/karabiner.json` · Magnet's own settings · tmux `~/.config/tmux/shortcuts.txt` ·
Neovim `~/.config/nvim/KEYBINDINGS.md` · Alfred `~/cloud/Dropbox/Alfred.alfredpreferences` ·
Vimium `~/.config/yadm/files/vimium/` (restore via Vimium Options) · Hotkeys app list `~/.config/hotkeys/config.json`.
