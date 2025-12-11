# ~/.zshrc
# Main zsh configuration file

# ============================================================
# Truecolor & History (before Oh My Zsh)
# ============================================================
export COLORTERM=truecolor

HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000
setopt SHARE_HISTORY
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt HIST_SAVE_NO_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_REDUCE_BLANKS
setopt INC_APPEND_HISTORY

# ============================================================
# Oh My Zsh Configuration
# ============================================================
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME=""  # Using Starship instead
DISABLE_COMPFIX=true  # Skip compaudit checks

# Move zcompdump to cache directory
export ZSH_COMPDUMP="$HOME/.cache/zsh/zcompdump-${HOST}-${ZSH_VERSION}"
[[ -d "$HOME/.cache/zsh" ]] || mkdir -p "$HOME/.cache/zsh"

plugins=(
  git
  macos
  python
  docker
  docker-compose
  colored-man-pages
  extract
  fzf           # Fuzzy finder integration (Ctrl+R history, Ctrl+T files)
  copypath      # Copy current directory path with `copypath`
  copyfile      # Copy file contents with `copyfile <file>`
  dirhistory    # Alt+Left/Right to navigate directory history
)

[[ -d "$ZSH" ]] && source "$ZSH/oh-my-zsh.sh"

# ============================================================
# Custom Modular Configuration
# ============================================================
# Load in order: env, paths, aliases, functions, plugins
# NOTE: completion.zsh is NOT loaded - zsh-autocomplete handles it
if [[ -d "$HOME/.zsh" ]]; then
  for f in env.zsh paths.zsh aliases.zsh functions.zsh plugins.zsh; do
    [[ -f "$HOME/.zsh/$f" ]] && source "$HOME/.zsh/$f"
  done
fi

# ============================================================
# Mamba Initialization (before autocomplete for proper completions)
# ============================================================
# Mamba requires conda shell functions, so load conda.sh first
if [[ -f "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/conda.sh" ]]; then
  source "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/conda.sh"
fi
if [[ -f "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/mamba.sh" ]]; then
  source "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/mamba.sh"
fi
# Activate default environment
mamba activate py3 2>/dev/null

# ============================================================
# Modern Tools
# ============================================================
command -v starship &>/dev/null && eval "$(starship init zsh)"
command -v zoxide &>/dev/null && eval "$(zoxide init zsh --cmd cd)"

# fzf configuration - Ctrl+T searches directories only
export FZF_CTRL_T_COMMAND='find . -type d -not -path "*/\.git/*" 2>/dev/null'

# fzf keybindings and completion (Ctrl+R, Ctrl+T, **<Tab>)
[[ -f /opt/homebrew/opt/fzf/shell/key-bindings.zsh ]] && \
  source /opt/homebrew/opt/fzf/shell/key-bindings.zsh
[[ -f /opt/homebrew/opt/fzf/shell/completion.zsh ]] && \
  source /opt/homebrew/opt/fzf/shell/completion.zsh

# Ctrl+G: zoxide interactive - fuzzy search frequently used directories
zoxide-widget() {
  local selected
  selected=$(zoxide query -l | fzf --height 40% --reverse)
  if [[ -n "$selected" ]]; then
    LBUFFER+="${selected}"
  fi
  zle reset-prompt
}
zle -N zoxide-widget
bindkey '^G' zoxide-widget

# ============================================================
# Shell Plugins
# ============================================================
# Syntax highlighting (colors for commands as you type)
[[ -f /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && \
  source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# Autosuggestions (fish-like ghost text from history, press → to accept)
[[ -f /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && \
  source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh

# ============================================================
# Completion Settings (standard zsh completion)
# ============================================================
autoload -Uz compinit && compinit -d "$ZSH_COMPDUMP"

zstyle ':completion:*' menu select                          # Arrow key menu
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'   # Case insensitive
zstyle ':completion:*' list-colors ''                       # Colorize
zstyle ':completion:*' special-dirs true                    # Complete . and ..

# Keybindings
bindkey '^[[Z' reverse-menu-complete  # Shift-Tab: go back in menu
bindkey '^[[A' history-search-backward # Up: search history backward
bindkey '^[[B' history-search-forward  # Down: search history forward

# Edit command in nvim with Ctrl+X Ctrl+E
autoload -Uz edit-command-line
zle -N edit-command-line
bindkey '^X^E' edit-command-line



