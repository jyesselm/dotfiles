-- Disable treesitter in VSCode BEFORE anything else loads
if vim.g.vscode then
    vim.g.loaded_nvim_treesitter = 1
end

vim.opt.expandtab = true        -- Use spaces instead of tabs
vim.opt.tabstop = 4             -- Number of spaces tabs count for
vim.opt.softtabstop = 4         -- Number of spaces a <Tab> counts for while editing
vim.opt.shiftwidth = 4          -- Number of spaces to use for autoindent
vim.opt.termguicolors = true    -- Enable 24-bit colors
vim.g.mapleader = " "
vim.wo.number = true
vim.opt.colorcolumn = "80"
vim.opt.mouse = "a"              -- Enable mouse in all modes

-- Clipboard: use OSC 52 over SSH (works through terminal), otherwise system clipboard
if os.getenv("SSH_TTY") then
    vim.g.clipboard = {
        name = 'OSC 52',
        copy = {
            ['+'] = require('vim.ui.clipboard.osc52').copy('+'),
            ['*'] = require('vim.ui.clipboard.osc52').copy('*'),
        },
        paste = {
            ['+'] = require('vim.ui.clipboard.osc52').paste('+'),
            ['*'] = require('vim.ui.clipboard.osc52').paste('*'),
        },
    }
end
vim.opt.clipboard = "unnamedplus"

-- Auto-copy mouse selection to system clipboard
vim.keymap.set('v', '<LeftRelease>', '"+y<LeftRelease>', { noremap = true, silent = true })

-- Load lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

local opts = {}

require("lazy").setup("plugins")

vim.keymap.set('n', '<C-n>', ':Neotree filesystem reveal left<CR>')
-- Normal mode mappings
vim.keymap.set('n', 'J', '5j', { noremap = true, silent = true, desc = 'Go down faster' })
vim.keymap.set('n', 'K', '5k', { noremap = true, silent = true, desc = 'Go up faster' })
vim.keymap.set('n', '<leader>/', ':noh<CR>', { noremap = true, silent = true, desc = 'Clear highlighted text' })
vim.keymap.set('n', '<leader>w', ':w<CR>', { noremap = true, silent = true, desc = 'Save file' })
vim.keymap.set('n', 'fs', ':Telescope treesitter<CR>', { noremap = true, silent = true, desc = 'Go to symbol in file' })


-- Window navigation
if vim.g.vscode then
    -- VSCode/Cursor: use VS Code commands for window navigation
    vim.keymap.set('n', '<C-h>', '<Cmd>call VSCodeNotify("workbench.action.navigateLeft")<CR>', { noremap = true, silent = true })
    vim.keymap.set('n', '<C-j>', '<Cmd>call VSCodeNotify("workbench.action.navigateDown")<CR>', { noremap = true, silent = true })
    vim.keymap.set('n', '<C-k>', '<Cmd>call VSCodeNotify("workbench.action.navigateUp")<CR>', { noremap = true, silent = true })
    vim.keymap.set('n', '<C-l>', '<Cmd>call VSCodeNotify("workbench.action.navigateRight")<CR>', { noremap = true, silent = true })

    -- VSCode/Cursor: Telescope-like commands
    vim.keymap.set('n', 'ff', '<Cmd>call VSCodeNotify("workbench.action.quickOpen")<CR>', { noremap = true, silent = true, desc = 'Find files' })
    vim.keymap.set('n', 'fg', '<Cmd>call VSCodeNotify("workbench.action.quickTextSearch")<CR>', { noremap = true, silent = true, desc = 'Live grep' })
    vim.keymap.set('n', 'fb', '<Cmd>call VSCodeNotify("workbench.action.showAllEditors")<CR>', { noremap = true, silent = true, desc = 'Find buffers' })
    vim.keymap.set('n', 'fw', '<Cmd>call VSCodeNotify("workbench.action.showAllSymbols")<CR>', { noremap = true, silent = true, desc = 'Workspace symbols' })
    vim.keymap.set('n', 'fs', '<Cmd>call VSCodeNotify("workbench.action.gotoSymbol")<CR>', { noremap = true, silent = true, desc = 'File symbols' })

    -- VSCode/Cursor: Window splits (matches tmux prefix + | and prefix + -)
    vim.keymap.set('n', '<leader>\\', '<Cmd>call VSCodeNotify("workbench.action.splitEditorRight")<CR>', { noremap = true, silent = true, desc = 'Split vertical' })
    vim.keymap.set('n', '<leader>-', '<Cmd>call VSCodeNotify("workbench.action.splitEditorDown")<CR>', { noremap = true, silent = true, desc = 'Split horizontal' })
    vim.keymap.set('n', '<leader>x', '<Cmd>call VSCodeNotify("workbench.action.closeActiveEditor")<CR>', { noremap = true, silent = true, desc = 'Close split' })

    -- VSCode/Cursor: Move editor to another split
    vim.keymap.set('n', '<leader>mh', '<Cmd>call VSCodeNotify("workbench.action.moveEditorToLeftGroup")<CR>', { noremap = true, silent = true, desc = 'Move editor left' })
    vim.keymap.set('n', '<leader>ml', '<Cmd>call VSCodeNotify("workbench.action.moveEditorToRightGroup")<CR>', { noremap = true, silent = true, desc = 'Move editor right' })
    vim.keymap.set('n', '<leader>mk', '<Cmd>call VSCodeNotify("workbench.action.moveEditorToAboveGroup")<CR>', { noremap = true, silent = true, desc = 'Move editor up' })
    vim.keymap.set('n', '<leader>mj', '<Cmd>call VSCodeNotify("workbench.action.moveEditorToBelowGroup")<CR>', { noremap = true, silent = true, desc = 'Move editor down' })
else
    -- Terminal Neovim: Window splits (matches tmux prefix + | and prefix + -)
    vim.keymap.set('n', '<leader>\\', '<C-w>v', { noremap = true, silent = true, desc = 'Split vertical' })
    vim.keymap.set('n', '<leader>-', '<C-w>s', { noremap = true, silent = true, desc = 'Split horizontal' })
    vim.keymap.set('n', '<leader>x', '<C-w>c', { noremap = true, silent = true, desc = 'Close split' })
end


-- Tab management
-- vim.keymap.set('n', '<leader>t', ':tabnew<CR>', { noremap = true, silent = true, desc = 'Create new tab' })
vim.keymap.set('n', '<leader>l', ':tabnext<CR>', { noremap = true, silent = true, desc = 'Move to next tab' })
vim.keymap.set('n', '<leader>h', ':tabprevious<CR>', { noremap = true, silent = true, desc = 'Move to previous tab' })
vim.keymap.set('n', '<leader>to', ':tabonly<CR>', { noremap = true, silent = true, desc = 'Close all tabs but the current one' })

