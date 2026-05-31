return {
    "akinsho/bufferline.nvim",
    version = "*",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = {
        options = {
            mode = "buffers",
            separator_style = "thin",
            name_formatter = function(buf)
                return vim.fn.fnamemodify(buf.path or "", ":t")
            end,
            show_buffer_close_icons = true,
            show_close_icon = true,
            color_icons = true,
            diagnostics = "nvim_lsp",
            close_command = function(n) require("snacks").bufdelete(n) end,
            right_mouse_command = function(n) require("snacks").bufdelete(n) end,
        },
    },
}
