# ~/.zshrc
# Main zsh configuration file

# Enable Powerlevel10k instant prompt (if using) or set up early
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# ============================================================
# Performance & Compatibility
# ============================================================
# Disable Oh My Zsh theme if using Starship (they conflict)
# Set to empty string to use Starship instead
ZSH_THEME=""

# Truecolor support
export COLORTERM=truecolor

# History configuration (before Oh My Zsh loads)
HISTFILE="$HOME/.zsh_history"
HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY          # Share history between sessions
setopt HIST_EXPIRE_DUPS_FIRST # Expire duplicates first
setopt HIST_IGNORE_DUPS       # Don't record duplicates
setopt HIST_IGNORE_ALL_DUPS   # Delete old recorded entry if new entry is duplicate
setopt HIST_FIND_NO_DUPS      # Don't display duplicates during search
setopt HIST_IGNORE_SPACE      # Don't record entries starting with space
setopt HIST_SAVE_NO_DUPS      # Don't write duplicate entries
setopt HIST_REDUCE_BLANKS     # Remove superfluous blanks
setopt HIST_VERIFY            # Show command with history expansion before running

# ============================================================
# Oh My Zsh Configuration
# ============================================================
export ZSH="$HOME/.oh-my-zsh"

# Oh My Zsh plugins (lazy load heavy ones if needed)
plugins=(
  git
  macos
  python
  docker
  docker-compose
  colored-man-pages
  command-not-found
  extract
  z
)

# Load Oh My Zsh (only if installed)
if [[ -d "$ZSH" ]]; then
  source "$ZSH/oh-my-zsh.sh"
else
  echo "⚠️  Oh My Zsh not found. Install with: sh -c \"\$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)\""
fi

# ============================================================
# Conda Configuration
# ============================================================
# Conda initialization (lazy - only if conda exists)
if [[ -f "/opt/homebrew/Caskroom/miniconda/base/bin/conda" ]]; then
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
  
  # Auto-activate default env (only if it exists)
  if conda env list | grep -q "^py3 "; then
    conda activate py3 2>/dev/null || true
  fi
fi

# ============================================================
# Custom Modular Configuration
# ============================================================
# Load custom configs in specific order for dependencies
if [ -d "$HOME/.zsh" ]; then
  # Load in order: env, paths, aliases, functions, plugins, completion
  for f in env.zsh paths.zsh aliases.zsh functions.zsh plugins.zsh completion.zsh; do
    [ -f "$HOME/.zsh/$f" ] && source "$HOME/.zsh/$f"
  done
fi

# ============================================================
# Modern Tools Initialization
# ============================================================
# Starship prompt (modern, fast, configurable)
# Only load if starship is installed and not using Oh My Zsh theme
if command -v starship &> /dev/null && [[ -z "$ZSH_THEME" || "$ZSH_THEME" == "" ]]; then
  eval "$(starship init zsh)"
fi

# zoxide - smarter cd (replaces z)
if command -v zoxide &> /dev/null; then
  eval "$(zoxide init zsh --cmd cd)"
fi

# ============================================================
# Performance Optimizations
# ============================================================
# Compile zsh files for faster loading (runs in background)
if [[ -n "$HOME/.zsh" ]]; then
  (zcompile "$HOME/.zshrc" 2>/dev/null &)
  for f in "$HOME"/.zsh/*.zsh; do
    [[ -r "$f" ]] && (zcompile "$f" 2>/dev/null &)
  done
fi
