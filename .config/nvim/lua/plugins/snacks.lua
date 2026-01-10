return {
    "folke/snacks.nvim",
    priority = 1000,
    lazy = false,
    opts = {
        -- Big file handling (disable heavy features for large files)
        bigfile = {
            enabled = true,
            size = 1.5 * 1024 * 1024, -- 1.5MB
        },
        -- Buffer delete without messing up layout
        bufdelete = {
            enabled = true,
        },
        -- Dim inactive code outside current scope
        dim = {
            enabled = true,
        },
        -- File explorer
        explorer = {
            enabled = true,
        },
        -- LazyGit integration
        lazygit = {
            enabled = true,
        },
        -- Better keymaps
        keymap = {
            enabled = true,
        },
        -- Scope detection
        scope = {
            enabled = true,
        },
        -- Picker (replaces Telescope)
        picker = {
            enabled = true,
            sources = {
                files = { hidden = true },
                grep = { hidden = true },
            },
            win = {
                input = {
                    keys = {
                        ["<C-j>"] = { "list_down", mode = { "i", "n" } },
                        ["<C-k>"] = { "list_up", mode = { "i", "n" } },
                        ["<C-t>"] = { "edit_tab", mode = { "i", "n" } },
                        ["<C-v>"] = { "edit_vsplit", mode = { "i", "n" } },
                        ["<C-x>"] = { "edit_split", mode = { "i", "n" } },
                    },
                },
            },
        },
        -- Dashboard (startup screen)
        dashboard = {
            enabled = true,
            sections = {
                { section = "header" },
                { section = "keys", gap = 1, padding = 1 },
                { section = "recent_files", limit = 8, padding = 1 },
                { section = "startup" },
            },
        },
        -- Better notifications
        notifier = {
            enabled = true,
            timeout = 3000,
        },
        -- Highlight word under cursor
        words = {
            enabled = true,
        },
        -- Quick file (faster file open)
        quickfile = {
            enabled = true,
        },
        -- Smooth scrolling
        scroll = {
            enabled = true,
            animate = {
                duration = { step = 15, total = 150 },
            },
        },
        -- Zen mode
        zen = {
            enabled = true,
        },
        -- Better input UI
        input = {
            enabled = true,
        },
        -- Indent guides (disable since we have indent-blankline)
        indent = {
            enabled = false,
        },
        -- Status column
        statuscolumn = {
            enabled = false,
        },
    },
    keys = {
        -- Picker keymaps (same as your Telescope ones)
        { "ff", function() Snacks.picker.files() end, desc = "Find files" },
        { "ft", function() Snacks.picker.files({ win = { input = { keys = { ["<CR>"] = { "edit_tab", mode = { "i", "n" } } } } } }) end, desc = "Find files (tab)" },
        { "fg", function() Snacks.picker.grep({ layout = "sidebar" }) end, desc = "Live grep (horizontal)" },
        { "fG", function() Snacks.picker.grep() end, desc = "Live grep (vertical)" },
        { "fb", function() Snacks.picker.buffers() end, desc = "Find buffers" },
        { "fw", function() Snacks.picker.lsp_workspace_symbols() end, desc = "Workspace symbols" },
        { "fs", function() Snacks.picker.lsp_symbols() end, desc = "Document symbols" },
        { "fk", function() Snacks.picker.keymaps() end, desc = "Find keymaps" },
        { "fr", function() Snacks.picker.recent() end, desc = "Recent files" },
        { "fh", function() Snacks.picker.help() end, desc = "Help pages" },
        { "fc", function() Snacks.picker.commands() end, desc = "Commands" },
        -- Grep word under cursor
        { "f*", function() Snacks.picker.grep_word() end, desc = "Grep word under cursor" },
        -- Git
        { "<leader>gs", function() Snacks.picker.git_status() end, desc = "Git status" },
        { "<leader>gc", function() Snacks.picker.git_log() end, desc = "Git commits" },
        -- Zen mode
        { "<leader>z", function() Snacks.zen() end, desc = "Zen mode" },
        -- Notifications
        { "<leader>n", function() Snacks.notifier.show_history() end, desc = "Notification history" },
        -- Explorer
        { "<C-n>", function() Snacks.explorer() end, desc = "File explorer" },
        -- LazyGit
        { "<leader>gg", function() Snacks.lazygit() end, desc = "LazyGit" },
        -- Buffer delete
        { "<leader>bd", function() Snacks.bufdelete() end, desc = "Delete buffer" },
        -- Dim toggle
        { "<leader>d", function() Snacks.dim() end, desc = "Toggle dim" },
    },
    init = function()
        -- Setup some globals for easy access
        vim.api.nvim_create_autocmd("User", {
            pattern = "VeryLazy",
            callback = function()
                -- Global toggle functions
                _G.Snacks = require("snacks")
            end,
        })
    end,
}
