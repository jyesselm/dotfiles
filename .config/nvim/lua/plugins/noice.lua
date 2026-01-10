return {
    "folke/noice.nvim",
    event = "VeryLazy",
    dependencies = {
        "MunifTanjim/nui.nvim",
    },
    opts = {
        -- Use Snacks notifier instead of noice's
        messages = { enabled = false },
        notify = { enabled = false },
        lsp = {
            -- Override LSP hover and signature help with nicer UI
            override = {
                ["vim.lsp.util.convert_input_to_markdown_lines"] = true,
                ["vim.lsp.util.stylize_markdown"] = true,
                ["cmp.entry.get_documentation"] = true,
            },
            hover = {
                enabled = true,
                silent = true,  -- don't show message if hover is empty
            },
            signature = {
                enabled = true,
            },
            message = {
                enabled = false,
            },
        },
        presets = {
            bottom_search = true,         -- classic bottom cmdline for search
            command_palette = true,       -- position cmdline and popupmenu together
            long_message_to_split = true, -- long messages go to split
            lsp_doc_border = true,        -- add border to hover docs and signature help
        },
        -- Disable some noisy messages
        routes = {
            {
                filter = {
                    event = "msg_show",
                    kind = "",
                    find = "written",
                },
                opts = { skip = true },
            },
            -- Catch-all for "No information available"
            {
                filter = { find = "No information available" },
                opts = { skip = true },
            },
        },
    },
}
