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

# fzf configuration
export FZF_DEFAULT_OPTS='--height 40% --reverse'
export FZF_CTRL_T_COMMAND='fd --type f --hidden --exclude .git 2>/dev/null || find . -type f'
export FZF_ALT_C_COMMAND='fd --type d --hidden --exclude .git 2>/dev/null || find . -type d'

# Source fzf keybindings (BEFORE atuin so atuin takes Ctrl+R)
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
[ -f /opt/homebrew/opt/fzf/shell/key-bindings.zsh ] && source /opt/homebrew/opt/fzf/shell/key-bindings.zsh
[ -f /opt/homebrew/opt/fzf/shell/completion.zsh ] && source /opt/homebrew/opt/fzf/shell/completion.zsh

# Atuin - synced shell history (AFTER fzf to override Ctrl+R)
if command -v atuin &>/dev/null; then
  eval "$(atuin init zsh)"
elif [[ -f "$HOME/.atuin/bin/env" ]]; then
  source "$HOME/.atuin/bin/env"
  eval "$(atuin init zsh)"
fi

# 1Password CLI integration (macOS only)
if $IS_MACOS && command -v op &>/dev/null; then
  # Shell plugins for auto-complete
  [[ -f ~/.config/op/plugins.sh ]] && source ~/.config/op/plugins.sh
  # Completions
  eval "$(op completion zsh)" 2>/dev/null
fi

# Ctrl+G: zoxide interactive - fuzzy cd to frequent directories
zoxide-widget() {
  local selected
  selected=$(zoxide query -l 2>/dev/null | fzf --height 40% --reverse --no-sort) || return 0
  [[ -n "$selected" ]] && LBUFFER+="${selected}"
  zle reset-prompt
}
zle -N zoxide-widget
bindkey '^G' zoxide-widget

# Ctrl+F: file search - fuzzy find files with preview
file-widget() {
  local selected
  selected=$(fd --type f --hidden --exclude .git 2>/dev/null | fzf --height 40% --reverse --preview 'bat --style=numbers --color=always {} 2>/dev/null || cat {}') || return 0
  [[ -n "$selected" ]] && LBUFFER+="${selected}"
  zle reset-prompt
}
zle -N file-widget
bindkey '^F' file-widget

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
