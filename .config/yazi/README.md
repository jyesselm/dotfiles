# Yazi configuration

Yazi 26.9.1+, Catppuccin Mocha with teal selection, colorful file names and Nerd Font icons.

- `y`: shell launcher in `~/.zsh/functions.zsh`; q returns to the browsed directory, Q preserves the starting directory.
- tmux leader+y: open a dedicated `files` window.
- `?`: help; Esc closes help.
- `Z`: zoxide; visits inside Yazi update its history.
- `g n`: Notes; `g p`: Papers; `g w`: Code; `g d`: Downloads; `g y`: settings.
- `, r`: recent first; `, n`: natural name order.

On macOS: `brew install yazi fd ripgrep fzf zoxide jq sevenzip resvg poppler ffmpeg`.
Use a Nerd Font in the terminal. Reload Yazi after editing these files.

The full guide is in the Obsidian vault: `300-reference/tools/cli/yazi-terminal-file-browser.md`.

## Theme provenance

- https://github.com/catppuccin/yazi, commit `d62802be39210ea10e54b3e3b09735c6cb9e57c1`
  - Source: `themes/mocha/catppuccin-mocha-teal.toml`
  - Local changes: purple active tab, bold teal selection, extension-based file colors, special icons for notes/papers/code.
- https://github.com/catppuccin/bat, commit `6810349b28055dce54076712fc05fc68da4b8ec0`
  - Source: `themes/Catppuccin Mocha.tmTheme`

Both licenses are included alongside the theme files. Theme assets are stored locally; no downloads occur at startup.
