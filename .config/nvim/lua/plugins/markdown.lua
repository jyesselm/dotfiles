return {
    'MeanderingProgrammer/render-markdown.nvim',
    dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-tree/nvim-web-devicons' },
    ft = { 'markdown' },
    enabled = not vim.g.vscode,  -- Disable when running in VS Code
    opts = {
        heading = {
            enabled = true,
            icons = { '󰲡 ', '󰲣 ', '󰲥 ', '󰲧 ', '󰲩 ', '󰲫 ' },
        },
        code = {
            enabled = true,
            style = 'full',
            border = 'thin',
        },
        bullet = {
            enabled = true,
            icons = { '●', '○', '◆', '◇' },
        },
        checkbox = {
            enabled = true,
            unchecked = { icon = '󰄱 ' },
            checked = { icon = '󰱒 ' },
        },
    },
    keys = {
        { '<leader>mr', ':RenderMarkdown toggle<CR>', desc = 'Toggle markdown render' },
    },
}
