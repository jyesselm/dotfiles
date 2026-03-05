return {
  "kylechui/nvim-surround",
  event = "VeryLazy",
  opts = {
    keymaps = {
      normal = "gs",
      normal_cur = "gss",
      normal_line = "gS",
      normal_cur_line = "gSS",
      visual = "gS",
      visual_line = "gSS",
    },
  },
}
-- Usage:
--   gsiw" - surround word with "
--   gss)  - surround entire line with ()
--   gS"   - surround selection (visual mode)
--   cs"'  - change " to '
--   ds"   - delete surrounding "
