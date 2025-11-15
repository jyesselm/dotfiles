# ~/.zshrc

# Truecolor support
export COLORTERM=truecolor

# Path to your oh-my-zsh installation
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="nebirhos"

# Oh My Zsh plugins
plugins=(
  git
  macos
  python
)

# Load Oh My Zsh
source "$ZSH/oh-my-zsh.sh"

# --------------------------------------------------
# Conda (managed by conda init)
# --------------------------------------------------
# If you move away from this later, you can clean it up.
__conda_setup="$('/opt/homebrew/Caskroom/miniconda/base/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]; then
        . "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
    else
        export PATH="/opt/homebrew/Caskroom/miniconda/base/bin:$PATH"
    fi
fi
unset __conda_setup

# Auto-activate default env (optional)
conda activate py3

# --------------------------------------------------
# Custom modular config
# --------------------------------------------------
# All your paths, aliases, functions, etc. live in ~/.zsh/*.zsh
if [ -d "$HOME/.zsh" ]; then
  for f in "$HOME"/.zsh/*.zsh; do
    [ -r "$f" ] && source "$f"
  done
fi

# Starship prompt (after everything else)
eval "$(starship init zsh)"

# zoxide (use 'cd' as the command)
eval "$(zoxide init zsh --cmd cd)"
