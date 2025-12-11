# ~/.zsh/functions.zsh
# Custom shell functions


# ============================================================
# File Transfer & Remote Operations
# ============================================================
# Upload sequences & oligos to Swan
upload_seqs_and_oligos() {
  if [[ -z "$SEQPATH" ]]; then
    echo "Error: SEQPATH not set"
    return 1
  fi
  
  local current_dir=$PWD
  local parent_dir=$(dirname "$SEQPATH")
  local zip_name="sequences_and_oligos.zip"
  
  if ! cd "$parent_dir" 2>/dev/null; then
    echo "Error: Cannot access $parent_dir"
    return 1
  fi
  
  echo "Creating zip archive..."
  rm -f "$zip_name"
  if ! zip -r "$zip_name" "$(basename "$SEQPATH")/" &>/dev/null; then
    echo "Error: Failed to create zip file"
    cd "$current_dir" || true
    return 1
  fi
  
  echo "Uploading to swan.unl.edu..."
  if scp "$zip_name" jyesselm@swan.unl.edu:/work/yesselmanlab/jyesselm/ && \
     ssh jyesselm@swan.unl.edu "cd /work/yesselmanlab/jyesselm/ && unzip -o $zip_name && rm $zip_name"; then
    echo "✓ Upload successful"
    rm -f "$zip_name"
  else
    echo "✗ Upload failed"
  fi
  
  cd "$current_dir" || return 1
}

# Show recent files in directory
recent() {
  # Usage:
  #   recent              → 10 most recent in .
  #   recent 20           → 20 most recent in .
  #   recent DIR          → 10 most recent in DIR
  #   recent DIR 20       → 20 most recent in DIR

  local dir="."
  local count=10

  if [[ $# -ge 1 && -d "$1" ]]; then
    dir="$1"
    [[ $# -ge 2 ]] && count="$2"
  elif [[ $# -ge 1 ]]; then
    if [[ "$1" =~ ^[0-9]+$ ]]; then
      count="$1"
    else
      echo "Usage: recent [DIR] [COUNT]"
      return 1
    fi
  fi

  if command -v lsd &> /dev/null; then
    lsd -lt "$dir" | head -n "$((count + 1))"
  else
    ls -lt "$dir" | head -n "$((count + 1))"
  fi
}



# ============================================================
# File Operations
# ============================================================
# Create directory and cd into it
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

# Find files by name (case-insensitive)
ff() {
  local pattern="$1"
  local dir="${2:-.}"
  
  if [[ -z "$pattern" ]]; then
    echo "Usage: ff <pattern> [directory]"
    return 1
  fi
  
  find "$dir" -iname "*${pattern}*" -type f 2>/dev/null
}

# Find directories by name (case-insensitive)
fd() {
  local pattern="$1"
  local dir="${2:-.}"
  
  if [[ -z "$pattern" ]]; then
    echo "Usage: fd <pattern> [directory]"
    return 1
  fi
  
  find "$dir" -iname "*${pattern}*" -type d 2>/dev/null
}

# ============================================================
# Git Helpers
# ============================================================
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

# ============================================================
# System Information
# ============================================================
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

  if command -v find &> /dev/null; then
    find "$dir" -type f -exec du -h {} + 2>/dev/null | sort -rh | head -n "$count"
  else
    echo "find command not found"
    return 1
  fi
}

# ============================================================
# Search Functions
# ============================================================

# Spotlight search excluding Library and system folders
# Usage: mf <name>  or  mf <name> <folder>
mf() {
  local query="$1"
  local folder="${2:-$HOME}"
  if [[ -z "$query" ]]; then
    echo "Usage: mf <filename> [folder]"
    return 1
  fi
  mdfind -name "$query" -onlyin "$folder" 2>/dev/null | grep -v -E "(Library|\.Trash|/\\.)"
}

# Search file contents with ripgrep (excludes hidden, respects .gitignore)
# Usage: rgs <pattern>  or  rgs <pattern> <path>
rgs() {
  local pattern="$1"
  local path="${2:-.}"
  if [[ -z "$pattern" ]]; then
    echo "Usage: rgs <pattern> [path]"
    return 1
  fi
  rg --smart-case --hidden --glob '!.git' "$pattern" "$path"
}

# Search in specific file types
# Usage: rgpy <pattern>  (Python files)
rgpy() { rg --type py "$@"; }
rgjs() { rg --type js "$@"; }
rgmd() { rg --type md "$@"; }

# Search Dropbox
search-dropbox() {
  local query="$1"
  if [[ -z "$query" ]]; then
    echo "Usage: search-dropbox <pattern>"
    return 1
  fi
  mdfind -name "$query" -onlyin ~/Dropbox 2>/dev/null
}

# Search projects folder
search-projects() {
  local query="$1"
  if [[ -z "$query" ]]; then
    echo "Usage: search-projects <pattern>"
    return 1
  fi
  mdfind -name "$query" -onlyin ~/projects 2>/dev/null
}

# Interactive file search with fzf + preview
# Usage: sf [directory]
sf() {
  local dir="${1:-.}"
  local file
  file=$(fd --type f --hidden --exclude .git . "$dir" | fzf --preview 'bat --style=numbers --color=always {} 2>/dev/null || cat {}')
  if [[ -n "$file" ]]; then
    echo "$file"
  fi
}

# Interactive file search and open in nvim
# Usage: vf [directory]
vf() {
  local dir="${1:-.}"
  local file
  file=$(fd --type f --hidden --exclude .git . "$dir" | fzf --preview 'bat --style=numbers --color=always {} 2>/dev/null || cat {}')
  if [[ -n "$file" ]]; then
    nvim "$file"
  fi
}

# Search content and open in nvim (ripgrep + fzf)
# Usage: vg <pattern> [directory]
vg() {
  local pattern="$1"
  local dir="${2:-.}"
  if [[ -z "$pattern" ]]; then
    echo "Usage: vg <pattern> [directory]"
    return 1
  fi
  local file
  file=$(rg --files-with-matches "$pattern" "$dir" 2>/dev/null | fzf --preview "rg --color=always -C 3 '$pattern' {}")
  if [[ -n "$file" ]]; then
    nvim "$file"
  fi
}

# Search inside PDFs, Office docs, etc. with ripgrep-all
# Usage: rgd <pattern> [directory]
rgd() {
  local pattern="$1"
  local dir="${2:-.}"
  if [[ -z "$pattern" ]]; then
    echo "Usage: rgd <pattern> [directory]"
    echo "Searches PDFs, Word docs, spreadsheets, etc."
    return 1
  fi
  rga --smart-case "$pattern" "$dir"
}

# Search PDFs only
# Usage: rgpdf <pattern> [directory]
rgpdf() {
  local pattern="$1"
  local dir="${2:-.}"
  if [[ -z "$pattern" ]]; then
    echo "Usage: rgpdf <pattern> [directory]"
    return 1
  fi
  rga --type pdf "$pattern" "$dir"
}
