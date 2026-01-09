# ~/.zsh/aliases.zsh
# Command aliases and shortcuts

# ============================================================
# File Listing (lsd if available, fallback to ls)
# ============================================================
if command -v lsd &> /dev/null; then
  alias ls='lsd'
  alias la='lsd -A'
  alias ll='lsd -lh'
  alias l='lsd -CF'
  alias lt='lsd -lt | head'
  alias tree='lsd --tree'
else
  # Fallback to standard ls with colors
  alias ls='ls --color=auto'
  alias la='ls -A'
  alias ll='ls -lh'
  alias l='ls -CF'
  alias lt='ls -lt | head'
fi

# ============================================================
# Editors
# ============================================================
if command -v nvim &> /dev/null; then
  alias vi='nvim'
  alias vim='nvim'
  export EDITOR='nvim'
  export VISUAL='nvim'
else
  export EDITOR='vim'
  export VISUAL='vim'
fi

# ============================================================
# Directory Navigation
# ============================================================
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias -- -='cd -'  # Go to previous directory

# ============================================================
# Git Aliases
# ============================================================
alias g='git'
alias ga='git add'
alias gaa='git add --all'
alias gap='git add --patch'
alias gb='git branch'
alias gba='git branch --all'
alias gc='git commit'
alias gcm='git commit -m'
alias gco='git checkout'
alias gd='git diff'
alias gdc='git diff --cached'
alias gl='git log --oneline --graph --decorate'
alias gla='git log --oneline --graph --decorate --all'
alias gp='git push'
alias gpl='git pull'
alias gs='git status'
alias gst='git stash'
alias gstp='git stash pop'

# ============================================================
# System & Utilities
# ============================================================
alias df='df -h'                    # Human-readable disk usage
alias du='du -h'                     # Human-readable directory sizes
alias free='free -h'                 # Human-readable memory (Linux)
alias psg='ps aux | grep'           # Process grep
alias h='history'                    # History shortcut
alias hg='history | grep'            # History grep
alias c='clear'                      # Clear screen
alias reload='source ~/.zshrc'       # Reload zsh config
alias path='echo $PATH | tr ":" "\n"' # Pretty print PATH

# ============================================================
# macOS Specific
# ============================================================
if [[ "$OSTYPE" == "darwin"* ]]; then
  alias showfiles='defaults write com.apple.finder AppleShowAllFiles YES; killall Finder /System/Library/CoreServices/Finder.app'
  alias hidefiles='defaults write com.apple.finder AppleShowAllFiles NO; killall Finder /System/Library/CoreServices/Finder.app'
  alias cleanup='fd -H -I -t f ".DS_Store" . --exec rm -v {}'  # Remove .DS_Store files
  alias updatedb='sudo /usr/libexec/locate.updatedb'             # Update locate database
fi

# ============================================================
# Development Tools
# ============================================================
# Python
alias py='python3'
alias pip='pip3'
alias venv='python3 -m venv'
alias activate='source venv/bin/activate'

# Docker
if command -v docker &> /dev/null; then
  alias d='docker'
  alias dc='docker-compose'
  alias dps='docker ps'
  alias dpa='docker ps -a'
  alias di='docker images'
  alias dex='docker exec -it'
fi

# Tmux
alias mux='tmuxinator'

# ============================================================
# RNA/Bioinformatics Tools
# ============================================================
if command -v rnafold &> /dev/null; then
  alias rnafoldp='rnafold -p --noLP -d2'
fi

# ============================================================
# File Operations
# ============================================================
# Zip directory (remove alias if it exists, then define function)
unalias zip-dir 2>/dev/null || true
zip-dir() {
  local dir="${1:-.}"
  local name="${2:-$(basename "$dir")}"
  zip -r "${name}.zip" "$dir"
}

# ============================================================
# zoxide (if installed)
# ============================================================
if command -v zoxide &> /dev/null; then
  alias z='zoxide'
  alias zl='zoxide query -l | head -10'
  alias zi='zoxide query -i'  # Interactive
fi

# ============================================================
# 1Password CLI helpers (macOS)
# ============================================================
if [[ "$OSTYPE" == "darwin"* ]] && command -v op &>/dev/null; then
  # Copy password to clipboard: opp "Item Name"
  opp() { op item get "$1" --fields password | pbcopy && echo "Password copied!"; }
  # Copy username to clipboard: opu "Item Name"
  opu() { op item get "$1" --fields username | pbcopy && echo "Username copied!"; }
  # Copy OTP to clipboard: opo "Item Name"
  opo() { op item get "$1" --otp | pbcopy && echo "OTP copied!"; }
  # Search items: ops "search term"
  ops() { op item list | grep -i "$1"; }
fi

# ============================================================
# Dotfile Management (yadm)
# ============================================================
# Ensure yadm works on cluster where git needs login shell
if [[ -x "$HOME/.local/bin/yadm" ]]; then
  alias yadm='$HOME/.local/bin/yadm'
fi

# ============================================================
# Configuration File Shortcuts
# ============================================================
alias ez='nvim ~/.zshrc'
alias eza='nvim ~/.zsh/aliases.zsh'
alias ezp='nvim ~/.zsh/paths.zsh'
alias ezf='nvim ~/.zsh/functions.zsh'
alias ezc='nvim ~/.zsh/completion.zsh'
alias eze='nvim ~/.zsh/env.zsh'
alias egc='nvim ~/.gitconfig'


