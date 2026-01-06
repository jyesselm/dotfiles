# ~/.zsh/env.zsh
# Environment variables and locale settings

# Load secrets (API tokens, etc.) - not tracked by yadm
[[ -f ~/.zsh/secrets.zsh ]] && source ~/.zsh/secrets.zsh

# ============================================================
# Locale & Language
# ============================================================
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"

# ============================================================
# Editor Configuration
# ============================================================
# Set editor (will be overridden by aliases.zsh if nvim is available)
export EDITOR="${EDITOR:-vim}"
export VISUAL="${VISUAL:-$EDITOR}"

# ============================================================
# Pager Configuration
# ============================================================
export PAGER="less"
export LESS="-R -X -F"  # -R: color, -X: no clear, -F: quit if one screen

# ============================================================
# Directory Paths
# ============================================================
export DROPBOX="$HOME/Dropbox"
export NOTES="${DROPBOX}/0_notes/"
export SEQPATH="$HOME/cloud/gdrive/sequences_and_oligos"
export OBSIDIAN="$HOME/Dropbox/notes"
export BASESPACE="$HOME/BaseSpace"
export ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs"

# ============================================================
# Development Directories
# ============================================================
export CODE_DIR="$HOME/Dropbox/2_code"
export PROJECTS_DIR="$HOME/projects"

# ============================================================
# Shell Options
# ============================================================
# Disable core dumps (optional - can be removed if debugging)
ulimit -c 0 2>/dev/null || true

# ============================================================
# Terminal Configuration
# ============================================================
# Disable terminal flow control (Ctrl+S/Ctrl+Q)
stty -ixon 2>/dev/null || true

# ============================================================
# Application-Specific
# ============================================================
# Python
export PYTHONUNBUFFERED=1  # Unbuffered output for Python
export PYTHONDONTWRITEBYTECODE=1  # Don't create .pyc files

# Node.js / npm
export NPM_CONFIG_PREFIX="$HOME/.local"

# Rust (if installed)
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# ============================================================
# macOS Specific
# ============================================================
if [[ "$OSTYPE" == "darwin"* ]]; then
  # Disable "zsh: no matches found" error for globs
  setopt NO_NOMATCH
  
  # Homebrew
  [[ -f "/opt/homebrew/bin/brew" ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
fi
