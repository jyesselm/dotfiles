return {
    "akinsho/bufferline.nvim",
    version = "*",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = {
        options = {
            mode = "tabs",
            separator_style = "thin",
            show_buffer_close_icons = true,
            show_close_icon = true,
            color_icons = true,
            diagnostics = "nvim_lsp",
            close_command = function(n) require("snacks").bufdelete(n) end,
            right_mouse_command = function(n) require("snacks").bufdelete(n) end,
        },
    },
}
