return {
  'nvim-telescope/telescope.nvim',
  branch = '0.1.x',
  dependencies = {
    'nvim-lua/plenary.nvim',
    { 'nvim-telescope/telescope-fzf-native.nvim', build = 'make' },
    'nvim-tree/nvim-web-devicons',
  },
  config = function()
    local telescope = require('telescope')
    local actions = require('telescope.actions')

    telescope.setup({
      defaults = {
        mappings = {
          i = {
            ["<C-k>"] = actions.move_selection_previous,
            ["<C-j>"] = actions.move_selection_next,
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
          }
        }
      },
      pickers = {
        find_files = {
          theme = "dropdown",
        }
      },
      extensions = {
        fzf = {
          fuzzy = true,
          override_generic_sorter = true,
          override_file_sorter = true,
          case_mode = "smart_case",
        }
      }
    })

    telescope.load_extension('fzf')

    -- Keymaps
    local builtin = require('telescope.builtin')
    vim.keymap.set('n', 'ff', builtin.find_files, { desc = 'Find files' })
    vim.keymap.set('n', 'fg', builtin.live_grep, { desc = 'Live grep' })
    vim.keymap.set('n', 'fb', builtin.buffers, { desc = 'Find buffers' })
    vim.keymap.set('n', 'fw', builtin.lsp_dynamic_workspace_symbols, { desc = 'Workspace symbols' })
    vim.keymap.set('n', 'fk', builtin.keymaps, { desc = 'Find keymaps' })

    -- Find files and open in new tab
    vim.keymap.set('n', 'ft', function()
      builtin.find_files({
        attach_mappings = function(_, map)
          map('i', '<CR>', actions.select_tab)
          map('n', '<CR>', actions.select_tab)
          return true
        end,
      })
    end, { desc = 'Find files (open in tab)' })
  end,
}
