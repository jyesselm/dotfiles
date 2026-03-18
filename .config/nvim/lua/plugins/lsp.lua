-- LSP requires Neovim 0.10+
local has_modern_nvim = vim.fn.has('nvim-0.10') == 1
local is_ssh = os.getenv("SSH_TTY") ~= nil

return {
  {
    'williamboman/mason.nvim',
    cond = has_modern_nvim,
    lazy = false,
    config = function()
      require('mason').setup({
        -- Disable log notifications on SSH to avoid popups
        log_level = is_ssh and vim.log.levels.OFF or vim.log.levels.INFO,
        ui = {
          icons = {
            package_installed = "✓",
            package_pending = "➜",
            package_uninstalled = "✗"
          },
        },
      })
    end,
  },
  {
    'williamboman/mason-lspconfig.nvim',
    cond = has_modern_nvim,
    lazy = false,
    dependencies = {
      'williamboman/mason.nvim',
      'neovim/nvim-lspconfig',
      'hrsh7th/cmp-nvim-lsp',
    },
    config = function()
      local lspconfig = require('lspconfig')
      local capabilities = require('cmp_nvim_lsp').default_capabilities()

      -- Common on_attach function for keymaps
      local on_attach = function(client, bufnr)
        local opts = { buffer = bufnr, noremap = true, silent = true }
        vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
        vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
        vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
        vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
        vim.keymap.set('n', '<leader>k', vim.lsp.buf.hover, opts)
        vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
        vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, opts)
        vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, opts)
        vim.keymap.set('n', ']d', vim.diagnostic.goto_next, opts)
      end

      require('mason-lspconfig').setup({
        -- Skip auto-install on SSH/remote machines to avoid constant failures
        ensure_installed = is_ssh and {} or { 'pyright', 'ruff', 'lua_ls' },
        handlers = {
          -- Default handler for all servers
          function(server_name)
            lspconfig[server_name].setup({
              capabilities = capabilities,
              on_attach = on_attach,
            })
          end,
          -- Pyright config
          ['pyright'] = function()
            lspconfig.pyright.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              root_dir = function(fname)
                local util = require('lspconfig.util')
                return util.root_pattern(
                  'pyrightconfig.json',
                  'pyproject.toml',
                  'setup.py',
                  'setup.cfg',
                  '.git'
                )(fname) or util.path.dirname(fname)
              end,
              settings = {
                python = {
                  analysis = {
                    autoSearchPaths = true,
                    useLibraryCodeForTypes = false,
                    typeCheckingMode = 'basic',
                    diagnosticSeverityOverrides = {
                      reportGeneralTypeIssues = 'none',
                    },
                  },
                },
              },
            })
          end,
          -- Lua config
          ['lua_ls'] = function()
            lspconfig.lua_ls.setup({
              capabilities = capabilities,
              on_attach = on_attach,
              settings = {
                Lua = {
                  diagnostics = { globals = { 'vim' } },
                },
              },
            })
          end,
          -- Ruff config
          ['ruff'] = function()
            lspconfig.ruff.setup({
              capabilities = capabilities,
              on_attach = function(client, bufnr)
                on_attach(client, bufnr)
                -- Auto-format with ruff on save
                vim.api.nvim_create_autocmd("BufWritePre", {
                  buffer = bufnr,
                  callback = function()
                    vim.lsp.buf.format({ async = false, name = "ruff" })
                  end,
                })
              end,
            })
          end,
        },
      })
    end,
  },
  -- Autocompletion
  {
    'hrsh7th/nvim-cmp',
    cond = has_modern_nvim,
    lazy = false,
    dependencies = {
      'L3MON4D3/LuaSnip',
      'saadparwaiz1/cmp_luasnip',
      'hrsh7th/cmp-nvim-lsp',
      'hrsh7th/cmp-nvim-lua',
      'onsails/lspkind.nvim',
    },
    config = function()
      local cmp = require('cmp')
      local lspkind = require('lspkind')
      local luasnip = require('luasnip')

      local compare = require('cmp.config.compare')

      cmp.setup({
        performance = {
          max_view_entries = 5,
        },
        sorting = {
          priority_weight = 2,
          comparators = {
            compare.exact,
            function(entry1, entry2)
              local types = require('cmp.types')
              local kind1 = entry1:get_kind()
              local kind2 = entry2:get_kind()
              local snippet = types.lsp.CompletionItemKind.Snippet
              if kind1 == snippet and kind2 ~= snippet then return true end
              if kind1 ~= snippet and kind2 == snippet then return false end
              return nil
            end,
            compare.score,
            compare.recently_used,
            compare.locality,
            compare.kind,
            compare.length,
            compare.order,
          },
        },
        formatting = {
          format = lspkind.cmp_format({
            mode = 'symbol_text',
            maxwidth = 50,
            ellipsis_char = '...',
          })
        },
        mapping = cmp.mapping.preset.insert({
          ['<C-Space>'] = cmp.mapping.complete(),
          ['<Tab>'] = cmp.mapping(function(fallback)
            if cmp.visible() then
              cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then
              luasnip.expand_or_jump()
            else
              fallback()
            end
          end, { 'i', 's' }),
          ['<S-Tab>'] = cmp.mapping(function(fallback)
            if cmp.visible() then
              cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then
              luasnip.jump(-1)
            else
              fallback()
            end
          end, { 'i', 's' }),
          ['<CR>'] = cmp.mapping.confirm({ select = true }),
        }),
        sources = cmp.config.sources({
          { name = 'luasnip', priority = 1000 },
          { name = 'nvim_lsp', priority = 750 },
          { name = 'path' },
          { name = 'nvim_lua' },
        }),
        snippet = {
          expand = function(args)
            luasnip.lsp_expand(args.body)
          end,
        },
      })
    end
  },
}
