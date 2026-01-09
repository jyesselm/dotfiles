return {
  'rafamadriz/friendly-snippets',
  cond = vim.fn.has('nvim-0.10') == 1,
  config = function()
    require('luasnip.loaders.from_vscode').lazy_load()
  end
}
