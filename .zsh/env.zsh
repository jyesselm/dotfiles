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
# LS_COLORS - Catppuccin Mocha theme
# ============================================================
# Palette: green=151 teal=152 sky=153 sapphire=117 blue=153
#          lavender=189 mauve=183 pink=225 flamingo=224 rosewater=224
#          red=217 maroon=217 peach=223 yellow=223
#          overlay0=103 overlay1=109 surface2=102
export LS_COLORS="\
di=1;38;5;153:\
ln=38;5;225:\
ex=1;38;5;217:\
*.py=1;38;5;151:*.pyx=38;5;151:*.pyi=38;5;151:*.ipynb=38;5;151:\
*.md=1;38;5;223:*.rst=38;5;223:*.txt=38;5;223:\
*.docx=1;38;5;189:*.doc=1;38;5;189:*.xlsx=38;5;189:*.xls=38;5;189:*.pptx=38;5;189:*.pdf=1;38;5;183:\
*.csv=1;38;5;223:*.json=38;5;223:*.yaml=38;5;223:*.yml=38;5;223:*.toml=38;5;223:*.tsv=38;5;223:\
*.js=38;5;223:*.ts=38;5;153:*.tsx=38;5;153:*.jsx=38;5;223:*.html=38;5;224:*.css=38;5;183:\
*.c=1;38;5;152:*.cpp=1;38;5;152:*.h=38;5;152:*.hpp=38;5;152:*.rs=38;5;152:\
*.sh=38;5;217:*.zsh=38;5;217:*.bash=38;5;217:\
*.png=38;5;225:*.jpg=38;5;225:*.jpeg=38;5;225:*.gif=38;5;225:*.svg=38;5;225:*.ai=38;5;225:\
*.cif=1;38;5;117:*.pdb=1;38;5;117:*.pse=38;5;117:*.pml=38;5;117:\
*.zip=38;5;217:*.tar=38;5;217:*.gz=38;5;217:*.bz2=38;5;217:\
*.log=38;5;103:*.bak=38;5;103:*.tmp=38;5;103:\
*.ini=38;5;109:*.cfg=38;5;109:*.conf=38;5;109:*.env=38;5;109:\
*.gitignore=38;5;103:"

# ============================================================
# macOS Specific
# ============================================================
if [[ "$OSTYPE" == "darwin"* ]]; then
  # Disable "zsh: no matches found" error for globs
  setopt NO_NOMATCH
  
  # Homebrew
  [[ -f "/opt/homebrew/bin/brew" ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
fi
