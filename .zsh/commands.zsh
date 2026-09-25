# Everyday commands, grouped by purpose.

# File Listing (lsd if available, fallback to ls)
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

# Editors
if command -v nvim &> /dev/null; then
  alias vi='nvim'
  alias vim='nvim'
  export EDITOR='nvim'
  export VISUAL='nvim'
else
  export EDITOR='vim'
  export VISUAL='vim'
fi

# Directory Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias .....='cd ../../../..'
alias -- -='cd -'  # Go to previous directory

# Git helpers
# Quick git commit with message
quickcommit() {
  local message="$1"
  if [[ -z "$message" ]]; then
    echo "Usage: quickcommit <message>"
    return 1
  fi

  git add -A && git commit -m "$message"
}

# Git log with file changes (remove alias if it exists, then define function)
unalias glog 2>/dev/null || true
glog() {
  git log --oneline --graph --decorate --stat "${@}"
}

# System & Utilities
alias df='df -h'                    # Human-readable disk usage
alias du='du -h'                     # Human-readable directory sizes
alias free='free -h'                 # Human-readable memory (Linux)
alias psg='ps aux | grep'           # Process grep
alias h='history'                    # History shortcut
alias hg='history | grep'            # History grep
alias c='clear'                      # Clear screen
alias reload='source ~/.zshrc'       # Reload zsh config
alias path='echo $PATH | tr ":" "\n"' # Pretty print PATH

# Show disk usage for current directory
dus() {
  local dir="${1:-.}"
  if command -v du &> /dev/null; then
    du -sh "$dir"/* 2>/dev/null | sort -h
  else
    echo "du command not found"
    return 1
  fi
}

# Show largest files in directory
largest() {
  local count=${1:-10}
  local dir="${2:-.}"

  if command -v fd &>/dev/null; then
    fd --type f . "$dir" --exec du -h {} \; 2>/dev/null | sort -rh | head -n "$count"
  else
    find "$dir" -type f -exec du -h {} + 2>/dev/null | sort -rh | head -n "$count"
  fi
}

# macOS Specific
if [[ "$OSTYPE" == "darwin"* ]]; then
  alias showfiles='defaults write com.apple.finder AppleShowAllFiles YES; killall Finder /System/Library/CoreServices/Finder.app'
  alias hidefiles='defaults write com.apple.finder AppleShowAllFiles NO; killall Finder /System/Library/CoreServices/Finder.app'
  alias cleanup='fd -H -I -t f ".DS_Store" . --exec rm -v {}'  # Remove .DS_Store files
  alias updatedb='sudo /usr/libexec/locate.updatedb'             # Update locate database
fi

# Development Tools
# Python
alias py='python3'
alias pip='pip3'
alias venv='python3 -m venv'
alias activate='source venv/bin/activate'

# Tmux
alias mux='tmuxinator'

# Watch a Python script and re-run on save
# Usage: watchpy <script.py>
watchpy() {
  if [[ -z "$1" ]]; then
    echo "Usage: watchpy <script.py>"
    return 1
  fi
  echo "$1" | entr -c python "$1"
}

# Plain `tmux` opens work. Commands with arguments retain standard behavior.
function tmux {
  if (( $# )); then
    command tmux "$@"
  elif [[ -n ${TMUX-} ]]; then
    # Switch the current client instead of nesting tmux.
    command tmux has-session -t '=work' 2>/dev/null ||
      command tmux new-session -d -s work || return
    command tmux switch-client -t '=work'
  else
    # The marker is inherited only when this command starts a new server.
    TMUX_DEFAULT_STARTUP=work command tmux new-session -A -s work
  fi
}

# Yazi: q returns to the browsed directory; Q keeps the starting directory.
function y() {
  local yazi_cwd_file yazi_final_dir yazi_result
  yazi_cwd_file=$(mktemp -t yazi-cwd.XXXXXX) || return
  command yazi "$@" --cwd-file="$yazi_cwd_file"
  yazi_result=$?
  if IFS= read -r -d '' yazi_final_dir < "$yazi_cwd_file"; then
    :
  fi
  command rm -f -- "$yazi_cwd_file"
  if [[ $yazi_result -eq 0 && -n "$yazi_final_dir" && "$yazi_final_dir" != "$PWD" && -d "$yazi_final_dir" ]]; then
    builtin cd -- "$yazi_final_dir" || return
  fi
  return "$yazi_result"
}

# File Operations
# Zip directory (remove alias if it exists, then define function)
unalias zip-dir 2>/dev/null || true
zip-dir() {
  local dir="${1:-.}"
  local name="${2:-$(basename "$dir")}"
  zip -r "${name}.zip" "$dir"
}

# Make a directory and cd into it
mkcd() {
  local dir="$1"
  if [[ -z "$dir" ]]; then
    echo "Usage: mkcd <directory>"
    return 1
  fi

  if mkdir -p "$dir" && cd "$dir"; then
    echo "✓ Created and entered: $dir"
  else
    echo "✗ Failed to create directory: $dir"
    return 1
  fi
}

# Compress a directory to .tar.zst with a progress bar
tarzip() {
  if [ -z "$1" ]; then
    echo "Usage: tarzip <directory>"
    return 1
  fi
  local dir="$1"
  if [ ! -d "$dir" ]; then
    echo "Error: $dir is not a directory"
    return 1
  fi

  # Cross-platform byte size
  local size
  if du -sb "$dir" &>/dev/null; then
    size=$(du -sb "$dir" | awk '{print $1}')  # Linux (GNU)
  else
    size=$(find "$dir" -type f -exec stat -f%z {} + 2>/dev/null | awk '{s+=$1} END {print s}')  # macOS (BSD)
  fi

  echo "Compressing $dir ($(du -sh "$dir" | awk '{print $1}'))..."

  if [ -n "$size" ] && [ "$size" -gt 0 ] 2>/dev/null; then
    tar -c "$dir" | pv -s "$size" | zstd -T0 -19 > "${dir}.tar.zst"
  else
    tar -c "$dir" | pv | zstd -T0 -19 > "${dir}.tar.zst"  # No size estimate
  fi

  echo "Created ${dir}.tar.zst"
}

# Extract any archive
extract() {
  if [[ -z "$1" ]]; then
    echo "Usage: extract <archive>"
    return 1
  fi

  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "Error: File not found: $file"
    return 1
  fi

  case "$file" in
    *.tar.bz2|*.tbz2) tar xjf "$file" ;;
    *.tar.gz|*.tgz)   tar xzf "$file" ;;
    *.tar.xz)         tar xJf "$file" ;;
    *.tar)            tar xf "$file" ;;
    *.zip)            unzip "$file" ;;
    *.rar)            unrar x "$file" ;;
    *.7z)             7z x "$file" ;;
    *.gz)             gunzip "$file" ;;
    *.bz2)            bunzip2 "$file" ;;
    *)                echo "Unknown archive type: $file" && return 1 ;;
  esac
}

# zoxide (if installed)
if command -v zoxide &> /dev/null; then
  alias z='zoxide'
  alias zl='zoxide query -l | head -10'
  alias zi='zoxide query -i'  # Interactive
fi

# 1Password CLI helpers (macOS)
if [[ "$OSTYPE" == "darwin"* ]] && command -v op &>/dev/null; then
  # Copy password to clipboard: opp "Item Name"
  opp() { op item get "$1" --fields password --reveal | pbcopy && echo "Password copied!"; }
  # Copy username to clipboard: opu "Item Name"
  opu() { op item get "$1" --fields username --reveal | pbcopy && echo "Username copied!"; }
  # Copy OTP to clipboard: opo "Item Name"
  opo() { op item get "$1" --otp | pbcopy && echo "OTP copied!"; }
  # Search items: ops "search term"
  ops() { op item list | grep -i "$1"; }
fi

# Dotfile Management (yadm)
# Ensure yadm works on cluster where git needs login shell
if [[ -x "$HOME/.local/bin/yadm" ]]; then
  alias yadm='$HOME/.local/bin/yadm'
fi

# Configuration shortcuts (old shortcuts remain usable).
alias ez='nvim ~/.zshrc'
alias ezc='nvim ~/.zsh/commands.zsh'
alias ezt='nvim ~/.zsh/tools.zsh'
alias ezs='nvim ~/.zsh/science.zsh'
alias eza=ezc
alias ezf=ezc
alias ezp=ezt
alias eze=ezt
alias egc='nvim ~/.gitconfig'
