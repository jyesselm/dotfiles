# Neovim Keybindings Cheatsheet

Leader key: `<space>`

## Navigation (Most Important)

| Key | Action |
|-----|--------|
| `s` | Flash jump - type chars, press label to jump |
| `S` | Flash treesitter - select code blocks |
| `gd` | Go to definition |
| `gr` | Find references |
| `gi` | Go to implementation |
| `gD` | Go to declaration |
| `<C-o>` | Jump back (after gd, etc.) |
| `<C-i>` | Jump forward |
| `J` | Move down 5 lines |
| `K` | Move up 5 lines |
| `%` | Jump to matching bracket |
| `gg` | Go to top of file |
| `G` | Go to bottom of file |
| `42G` | Go to line 42 |

## File Finding (Telescope)

| Key | Action |
|-----|--------|
| `ff` | Find files |
| `ft` | Find files (open in new tab) |
| `fg` | Live grep (search in files) |
| `fb` | Find buffers |
| `fs` | Go to symbol in file |
| `fw` | Workspace symbols |
| `fk` | Search all keymaps |

### Inside Telescope
| Key | Action |
|-----|--------|
| `<CR>` | Open file |
| `<C-t>` | Open in new tab |
| `<C-v>` | Open in vertical split |
| `<C-x>` | Open in horizontal split |
| `<C-j>` | Move down in list |
| `<C-k>` | Move up in list |

## LSP (Code Intelligence)

| Key | Action |
|-----|--------|
| `gd` | Go to definition |
| `gr` | Find references |
| `gi` | Go to implementation |
| `<space>k` | Hover docs (show type info) |
| `<space>rn` | Rename symbol |
| `<space>ca` | Code actions |
| `[d` | Previous diagnostic/error |
| `]d` | Next diagnostic/error |

## Tabs

| Key | Action |
|-----|--------|
| `<space>l` | Next tab |
| `<space>h` | Previous tab |
| `<space>tc` | Close current tab |
| `<space>to` | Close all other tabs |

## Splits

| Key | Action |
|-----|--------|
| `<space>\` | Split vertical |
| `<space>-` | Split horizontal |
| `<space>x` | Close split |
| `<C-h/j/k/l>` | Navigate between splits |

## TODOs

| Key | Action |
|-----|--------|
| `]t` | Next TODO comment |
| `[t` | Previous TODO comment |
| `<space>st` | Search all TODOs |

## File Tree

| Key | Action |
|-----|--------|
| `<C-n>` | Toggle Neo-tree |

## Editing

| Key | Action |
|-----|--------|
| `<space>w` | Save file |
| `<space>/` | Clear search highlight |
| `u` | Undo |
| `<C-r>` | Redo |
| `ciw` | Change inner word |
| `ci"` | Change inside quotes |
| `di(` | Delete inside parentheses |
| `yy` | Yank (copy) line |
| `dd` | Delete line |
| `p` | Paste after |
| `P` | Paste before |

## Scrolling

| Key | Action |
|-----|--------|
| `<C-d>` | Scroll down half page |
| `<C-u>` | Scroll up half page |
| `zz` | Center cursor line |

## Visual Mode

| Key | Action |
|-----|--------|
| `v` | Visual mode (character) |
| `V` | Visual line mode |
| `<C-v>` | Visual block mode |
| `gv` | Reselect last selection |

## Macros

| Key | Action |
|-----|--------|
| `qa` | Start recording macro 'a' |
| `q` | Stop recording |
| `@a` | Play macro 'a' |
| `@@` | Replay last macro |

## Help

| Key | Action |
|-----|--------|
| `<space>` | Show which-key (wait 300ms) |
| `<space>?` | Buffer local keymaps |
| `fk` | Search all keymaps |

## Quick Workflow Examples

**Find and edit a function:**
1. `ff` → find file
2. `fs` → jump to symbol/function
3. Edit
4. `<space>w` → save

**Rename a variable project-wide:**
1. `gd` → go to definition
2. `<space>rn` → rename
3. Type new name, Enter

**Jump to any word on screen:**
1. `s` → start flash
2. Type first 2 chars of target
3. Press label letter

**Fix all TODOs:**
1. `<space>st` → see all TODOs
2. `<CR>` → jump to one
3. Fix it
4. `]t` → next TODO
