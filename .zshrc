# ~/.zshrc
# Unified zsh configuration - works on macOS and HPC cluster

# ============================================================
# Platform Detection
# ============================================================
if [[ "$(uname)" == "Darwin" ]]; then
  IS_MACOS=true
  IS_CLUSTER=false
elif [[ -d /util/opt ]] || [[ "$HOSTNAME" == *swan* ]]; then
  IS_MACOS=false
  IS_CLUSTER=true
else
  IS_MACOS=false
  IS_CLUSTER=false
fi

# ============================================================
# Platform-Specific Configuration (EARLY - before Oh My Zsh)
# ============================================================
# Cluster needs modules loaded first for tools to be available
if $IS_CLUSTER; then
  [[ -f "$HOME/.zsh/cluster.zsh" ]] && source "$HOME/.zsh/cluster.zsh"
fi

# ============================================================
# History Settings
# ============================================================
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000
setopt SHARE_HISTORY HIST_IGNORE_ALL_DUPS HIST_FIND_NO_DUPS
setopt HIST_SAVE_NO_DUPS HIST_IGNORE_SPACE HIST_REDUCE_BLANKS
setopt INC_APPEND_HISTORY

# ============================================================
# Oh My Zsh Configuration
# ============================================================
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME=""  # Using Starship instead
DISABLE_COMPFIX=true

export ZSH_COMPDUMP="$HOME/.cache/zsh/zcompdump-${HOST}-${ZSH_VERSION}"
[[ -d "$HOME/.cache/zsh" ]] || mkdir -p "$HOME/.cache/zsh"

# Platform-specific plugins
if $IS_MACOS; then
  plugins=(git macos python colored-man-pages extract fzf copypath copyfile dirhistory)
else
  plugins=(git colored-man-pages extract fzf)
fi

[[ -d "$ZSH" ]] && source "$ZSH/oh-my-zsh.sh"

# ============================================================
# Modular Configuration (shared across platforms)
# ============================================================
if [[ -d "$HOME/.zsh" ]]; then
  for f in env.zsh paths.zsh aliases.zsh functions.zsh; do
    [[ -f "$HOME/.zsh/$f" ]] && source "$HOME/.zsh/$f"
  done
fi

# ============================================================
# macOS-Specific Configuration (after Oh My Zsh)
# ============================================================
if $IS_MACOS; then
  [[ -f "$HOME/.zsh/macos.zsh" ]] && source "$HOME/.zsh/macos.zsh"
fi

# ============================================================
# Modern Tools (shared)
# ============================================================
export PATH="$HOME/.local/bin:$PATH"

command -v starship &>/dev/null && eval "$(starship init zsh)"
command -v zoxide &>/dev/null && eval "$(zoxide init zsh --cmd cd)"

# fzf
export FZF_CTRL_T_COMMAND='fd --type d --hidden --exclude .git 2>/dev/null || find . -type d'
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Ctrl+G: zoxide interactive
zoxide-widget() {
  local selected
  selected=$(zoxide query -l 2>/dev/null | fzf --height 40% --reverse --no-sort) || return 0
  [[ -n "$selected" ]] && LBUFFER+="${selected}"
  zle reset-prompt
}
zle -N zoxide-widget
bindkey '^G' zoxide-widget

# ============================================================
# Completion & Keybindings
# ============================================================
autoload -Uz compinit && compinit -d "$ZSH_COMPDUMP"

zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' special-dirs true

bindkey '^[[Z' reverse-menu-complete
bindkey '^[[A' history-search-backward
bindkey '^[[B' history-search-forward

autoload -Uz edit-command-line
zle -N edit-command-line
bindkey '^X^E' edit-command-line
