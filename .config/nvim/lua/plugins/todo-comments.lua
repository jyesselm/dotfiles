return {
    "folke/todo-comments.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    event = "VeryLazy",
    opts = {
        signs = true,
        keywords = {
            FIX = { icon = " ", color = "error", alt = { "FIXME", "BUG", "ISSUE" } },
            TODO = { icon = " ", color = "info" },
            HACK = { icon = " ", color = "warning" },
            WARN = { icon = " ", color = "warning", alt = { "WARNING" } },
            NOTE = { icon = " ", color = "hint", alt = { "INFO" } },
            PERF = { icon = " ", color = "default", alt = { "OPTIM", "PERFORMANCE" } },
        },
    },
    keys = {
        { "]t", function() require("todo-comments").jump_next() end, desc = "Next TODO" },
        { "[t", function() require("todo-comments").jump_prev() end, desc = "Prev TODO" },
        { "<leader>st", function() Snacks.picker.todo_comments() end, desc = "Search TODOs" },
    },
}
