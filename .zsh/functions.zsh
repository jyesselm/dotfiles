# ~/.zsh/functions.zsh
# Custom shell functions

# ============================================================
# Obsidian / Note Management
# ============================================================
# Obsidian snippet helper
snip() {
  local snippet=$1
  local keywords=$2
  
  if [[ -z "$snippet" ]]; then
    echo "Usage: snip <snippet> [keywords]"
    return 1
  fi
  
  if command -v obsidian-scripts &> /dev/null; then
    obsidian-scripts snippet "$snippet" --keywords "${keywords:-}"
  else
    echo "Error: obsidian-scripts not found"
    return 1
  fi
}

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

# ============================================================
# History & Scripting
# ============================================================
# Save recent history as a script
history_to_script() {
  local count=${1:-10}
  local output_file=${2:-"script.sh"}
  
  if [[ ! "$count" =~ ^[0-9]+$ ]]; then
    echo "Usage: history_to_script [count] [output_file]"
    return 1
  fi
  
  if fc -ln -"${count}" > "$output_file" 2>/dev/null; then
    chmod +x "$output_file"
    echo "✓ Script created: $output_file (last $count commands)"
  else
    echo "✗ Failed to create script"
    return 1
  fi
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
