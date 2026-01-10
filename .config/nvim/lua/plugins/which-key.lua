return {
    "folke/which-key.nvim",
    event = "VeryLazy",
    opts = {
        delay = 300,  -- ms before showing popup
        icons = {
            breadcrumb = "»",
            separator = "➜",
            group = "+",
        },
    },
    keys = {
        {
            "<leader>?",
            function()
                require("which-key").show({ global = false })
            end,
            desc = "Buffer Local Keymaps",
        },
    },
    config = function(_, opts)
        local wk = require("which-key")
        wk.setup(opts)

        -- Register key groups for better organization
        wk.add({
            { "<leader>c", group = "code" },
            { "<leader>m", group = "move editor" },
            { "<leader>t", group = "tabs" },
        })
    end,
}
