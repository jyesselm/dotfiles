# ~/.zsh/functions.zsh
# Custom shell functions
#
# File/content/fuzzy search tools (mff, ff, fdir, mf, sf, vf, vg, rgs, rgpy,
# rgjs, rgmd, rgd, rgpdf, recent, recentf, search-dropbox, search-projects, and
# the mff scope/cache machinery) were removed in favor of the `s` finder
# (search-cli): `s`, `s -t docs`, `s <scope>`, `s content`, `s docgrep`, `s recent`.


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
  local dir_name=$(basename "$SEQPATH")
  local archive_name="${dir_name}.tar.gz"

  if ! cd "$parent_dir" 2>/dev/null; then
    echo "Error: Cannot access $parent_dir"
    return 1
  fi

  echo "Creating tar.gz archive..."
  rm -f "$archive_name"
  if ! tar -czf "$archive_name" "$dir_name"; then
    echo "Error: Failed to create tar.gz archive"
    cd "$current_dir" || true
    return 1
  fi

  echo "Uploading to swan.unl.edu..."
  if scp "$archive_name" jyesselm@swan.unl.edu:/work/yesselmanlab/jyesselm/ && \
     ssh jyesselm@swan.unl.edu "cd /work/yesselmanlab/jyesselm/ && tar -xzf $archive_name && rm $archive_name"; then
    echo "✓ Upload successful"
    rm -f "$archive_name"
  else
    echo "✗ Upload failed"
  fi

  cd "$current_dir" || return 1
}


# ============================================================
# Filesystem Helpers
# ============================================================
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

  if command -v fd &>/dev/null; then
    fd --type f . "$dir" --exec du -h {} \; 2>/dev/null | sort -rh | head -n "$count"
  else
    find "$dir" -type f -exec du -h {} + 2>/dev/null | sort -rh | head -n "$count"
  fi
}


# ============================================================
# Development Helpers
# ============================================================
# Watch a Python script and re-run on save
# Usage: watchpy <script.py>
watchpy() {
  if [[ -z "$1" ]]; then
    echo "Usage: watchpy <script.py>"
    return 1
  fi
  echo "$1" | entr -c python "$1"
}
