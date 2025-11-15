return {
    "MattesGroeger/vim-bookmarks",
    config = function()
      -- Customize bookmark signs
      vim.g.bookmark_sign = '♥'
      vim.g.bookmark_highlight_lines = 1

      -- Key mappings
      vim.keymap.set('n', 'mm', '<Plug>BookmarkToggle', { noremap = false, silent = true })
      vim.keymap.set('n', 'mi', '<Plug>BookmarkAnnotate', { noremap = false, silent = true })
      vim.keymap.set('n', 'mn', '<Plug>BookmarkNext', { noremap = false, silent = true })
      vim.keymap.set('n', 'mp', '<Plug>BookmarkPrev', { noremap = false, silent = true })
      vim.keymap.set('n', 'ma', '<Plug>BookmarkShowAll', { noremap = false, silent = true })
      vim.keymap.set('n', 'mc', '<Plug>BookmarkClear', { noremap = false, silent = true })
      vim.keymap.set('n', 'mx', '<Plug>BookmarkClearAll', { noremap = false, silent = true })
    end,
  }
