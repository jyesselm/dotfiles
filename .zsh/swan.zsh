# Swan provides a supported tmux as a module; /usr/bin/tmux is still 2.7.
# This file is loaded only on Swan by the shared .zshrc.
if command -v module &>/dev/null; then
  module load tmux/3.6a 2>/dev/null
fi

# Discover bootstrap-managed tools before shell plugins load.
[[ -f "$HOME/.zsh/bootstrap.zsh" ]] && source "$HOME/.zsh/bootstrap.zsh"
