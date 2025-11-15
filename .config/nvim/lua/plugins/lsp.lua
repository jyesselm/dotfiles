return {
  {
    'VonHeikemen/lsp-zero.nvim',
    branch = 'v3.x',
    lazy = false,
    config = false,
    init = function()
      -- Disable automatic setup, we are doing it manually
      vim.g.lsp_zero_extend_cmp = 0
      vim.g.lsp_zero_extend_lspconfig = 0
    end,
  },
  {
    'williamboman/mason.nvim',
    lazy = false,
    config = true,
  },
  {
    'williamboman/mason-lspconfig.nvim',
    lazy = false,
    opts = {
      ensure_installed = {'pyright', 'ruff_lsp', 'lua_ls'},
    },
  },
  {
    'neovim/nvim-lspconfig',
    lazy = false,
    dependencies = {
      {'hrsh7th/cmp-nvim-lsp'},
    },
  },
  -- Autocompletion
  {
    'hrsh7th/nvim-cmp',
    lazy = false,
    dependencies = {
      {'L3MON4D3/LuaSnip'},
      {'saadparwaiz1/cmp_luasnip'},
      {'hrsh7th/cmp-nvim-lsp'},
      {'hrsh7th/cmp-nvim-lua'},
      {'onsails/lspkind.nvim'},
    },
    config = function()
      local lsp_zero = require('lsp-zero')
      lsp_zero.extend_cmp()

      local cmp = require('cmp')
      local cmp_action = lsp_zero.cmp_action()
      local lspkind = require('lspkind')

      cmp.setup({
        formatting = {
          format = lspkind.cmp_format({
            mode = 'symbol_text',
            maxwidth = 50,
            ellipsis_char = '...',
          })
        },
        mapping = cmp.mapping.preset.insert({
          ['<C-Space>'] = cmp.mapping.complete(),
          ['<Tab>'] = cmp_action.luasnip_supertab(),
          ['<S-Tab>'] = cmp_action.luasnip_shift_supertab(),
        }),
        sources = cmp.config.sources({
          {name = 'nvim_lsp'},
          {name = 'luasnip'},
          {name = 'path'},
          {name = 'nvim_lua'},
        }),
        snippet = {
          expand = function(args)
            require('luasnip').lsp_expand(args.body)
          end,
        },
        sorting = {
          comparators = {
            cmp.config.compare.offset,
            cmp.config.compare.exact,
            cmp.config.compare.score,
            cmp.config.compare.kind,
            cmp.config.compare.sort_text,
            cmp.config.compare.length,
            cmp.config.compare.order,
          },
        },
      })
    end
  },
  -- LSP
  {
    'neovim/nvim-lspconfig',
    cmd = {'LspInfo', 'LspInstall', 'LspStart'},
    event = {'BufReadPre', 'BufNewFile'},
    dependencies = {
      {'hrsh7th/cmp-nvim-lsp'},
      {'williamboman/mason-lspconfig.nvim'},
    },
    config = function()
      local lsp_zero = require('lsp-zero')
      lsp_zero.extend_lspconfig()

      lsp_zero.on_attach(function(client, bufnr)
        lsp_zero.default_keymaps({buffer = bufnr})
      end)

    -- Get the Conda environment path
    local conda_prefix = os.getenv("CONDA_PREFIX")
    local py3_path = conda_prefix and (conda_prefix .. "/envs/py3") or nil

      require('mason-lspconfig').setup_handlers({
        function(server_name)
          require('lspconfig')[server_name].setup({
            capabilities = require('cmp_nvim_lsp').default_capabilities(),
          })
        end,
        ['pyright'] = function()
          require('lspconfig').pyright.setup({
            settings = {
              python = {
                analysis = {
                  autoSearchPaths = true,
                  useLibraryCodeForTypes = false,
                  typeCheckingMode = 'basic',
                  diagonosticSeverityOverrides = {
                    reportGeneralTypeIssues = 'none',
                  },
                },
              },
            },
          })
        end,
        ['lua_ls'] = function()
          local lua_opts = lsp_zero.nvim_lua_ls()
          require('lspconfig').lua_ls.setup(lua_opts)
        end,
        ['ruff_lsp'] = function()
          require('lspconfig').ruff_lsp.setup({
            init_options = {
              settings = {
                args = {},
              }
            }
          })
        end,
      })
    end
  }
}
