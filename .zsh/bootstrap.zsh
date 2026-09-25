# Paths installed by dotfiles-setup. Load before Oh My Zsh on each platform.
# Only terminal commands are exposed; the managed environment's Python is not.
if [[ -d "$HOME/.local/share/dotfiles/bin" ]]; then
  path=("$HOME/.local/share/dotfiles/bin" $path)
fi
for dotfiles_brew_prefix in /opt/homebrew /usr/local /home/linuxbrew/.linuxbrew; do
  if [[ -x "$dotfiles_brew_prefix/bin/brew" ]]; then
    path+=("$dotfiles_brew_prefix/bin" "$dotfiles_brew_prefix/sbin")
    break
  fi
done
unset dotfiles_brew_prefix
typeset -U path
export PATH
