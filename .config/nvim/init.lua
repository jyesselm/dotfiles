vim.opt.expandtab = true        -- Use spaces instead of tabs
vim.opt.tabstop = 4             -- Number of spaces tabs count for
vim.opt.softtabstop = 4         -- Number of spaces a <Tab> counts for while editing
vim.opt.shiftwidth = 4          -- Number of spaces to use for autoindent
vim.opt.termguicolors = true    -- Enable 24-bit colors
vim.g.mapleader = " "
vim.wo.number = true
vim.opt.colorcolumn = "80"
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
vim.keymap.set('n', '<C-h>', '<C-w>h', { noremap = true, silent = true })
vim.keymap.set('n', '<C-j>', '<C-w>j', { noremap = true, silent = true })
vim.keymap.set('n', '<C-k>', '<C-w>k', { noremap = true, silent = true })
vim.keymap.set('n', '<C-l>', '<C-w>l', { noremap = true, silent = true })
vim.keymap.set('n', '<C-s>', '<C-w>s', { noremap = true, silent = true })


-- Tab management
-- vim.keymap.set('n', '<leader>t', ':tabnew<CR>', { noremap = true, silent = true, desc = 'Create new tab' })
vim.keymap.set('n', '<leader>l', ':tabnext<CR>', { noremap = true, silent = true, desc = 'Move to next tab' })
vim.keymap.set('n', '<leader>h', ':tabprevious<CR>', { noremap = true, silent = true, desc = 'Move to previous tab' })
vim.keymap.set('n', '<leader>to', ':tabonly<CR>', { noremap = true, silent = true, desc = 'Close all tabs but the current one' })

