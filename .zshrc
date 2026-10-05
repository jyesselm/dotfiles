# ~/.zshrc
# Unified zsh configuration - works on macOS and HPC cluster

# Platform Detection
# MACHINE_TYPE: macos, cluster, linux, or specific hostname
# Add new machines by extending the case statement below
export _ZO_DOCTOR=0

IS_MACOS=false
IS_CLUSTER=false
IS_LINUX=false
MACHINE_TYPE="unknown"

case "$(uname)" in
  Darwin)
    IS_MACOS=true
    MACHINE_TYPE="macos"
    ;;
  Linux)
    IS_LINUX=true
    # Detect specific clusters/servers
    if [[ -d /util/opt ]] || [[ "$HOSTNAME" == *swan* ]]; then
      IS_CLUSTER=true
      MACHINE_TYPE="swan"
    else
      MACHINE_TYPE="linux"
    fi
    ;;
esac

# Configuration map: tools = setup; science = lab tools; commands = shortcuts.
source "$HOME/.zsh/tools.zsh"
if $IS_CLUSTER; then
  source "$HOME/.zsh/swan.zsh"
fi

# History Settings
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000
setopt SHARE_HISTORY HIST_IGNORE_ALL_DUPS HIST_FIND_NO_DUPS
setopt HIST_SAVE_NO_DUPS HIST_IGNORE_SPACE HIST_REDUCE_BLANKS

# Oh My Zsh Configuration
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME=""  # Using Starship instead
DISABLE_COMPFIX=true

export ZSH_COMPDUMP="$HOME/.cache/zsh/zcompdump-${HOST}-${ZSH_VERSION}"
[[ -d "$HOME/.cache/zsh" ]] || mkdir -p "$HOME/.cache/zsh"

# fzf configuration
export FZF_DEFAULT_OPTS='--height 40% --reverse'
export FZF_CTRL_T_COMMAND='fd --type f --hidden --exclude .git 2>/dev/null || find . -type f'
export FZF_ALT_C_COMMAND='fd --type d --hidden --exclude .git 2>/dev/null || find . -type d'

# Platform-specific plugins
if $IS_MACOS; then
  plugins=(macos python colored-man-pages extract fzf copypath copyfile dirhistory zsh-autosuggestions zsh-syntax-highlighting)
else
  plugins=(colored-man-pages extract fzf zsh-autosuggestions zsh-syntax-highlighting)
fi

[[ -f "$ZSH/oh-my-zsh.sh" ]] && source "$ZSH/oh-my-zsh.sh"

# Everyday aliases and functions.
source "$HOME/.zsh/commands.zsh"

# Prompt
command -v starship &>/dev/null && eval "$(starship init zsh)"

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

# Completion
if (( ! $+functions[compdef] )); then
  autoload -Uz compinit && compinit -d "$ZSH_COMPDUMP"
fi

zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' special-dirs true

command -v zoxide &>/dev/null && eval "$(zoxide init zsh --cmd cd)"

if $IS_MACOS; then
  if (( ! $+functions[_zsh_autosuggest_start] )); then
    [[ -f /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
  fi
  if (( ! $+functions[_zsh_highlight] )); then
    [[ -f /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  fi
fi

# Local Overrides (not tracked in git)
# Create ~/.zsh/local.zsh for machine-specific settings
[[ -f "$HOME/.zsh/local.zsh" ]] && source "$HOME/.zsh/local.zsh"

# Discover science tools after machine overrides, so explicit paths take priority.
source "$HOME/.zsh/science.zsh"

# Apply hotkeys after all plugins and machine overrides.
source "$HOME/.zsh/keybindings.zsh"

# search-cli: allow s dir to change this shell directory.
[[ -f "$HOME/local/code/python/developing/search-cli/shell/search-cli.sh" ]] && source "$HOME/local/code/python/developing/search-cli/shell/search-cli.sh"
