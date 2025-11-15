# ~/.zsh/functions.zsh

# Obsidian snippet helper
snip() {
  local snippet=$1
  local keywords=$2
  obsidian-scripts snippet "$snippet" --keywords "$keywords"
}

# Upload sequences & oligos to Swan
upload_seqs_and_oligos() {
  local current_dir=$PWD
  cd "$SEQPATH/.." || return 1

  rm -rf sequences_and_oligos.zip
  zip -r sequences_and_oligos.zip sequences_and_oligos/

  scp sequences_and_oligos.zip jyesselm@swan.unl.edu:/work/yesselmanlab/jyesselm/ && \
  ssh jyesselm@swan.unl.edu "cd /work/yesselmanlab/jyesselm/ && unzip -o sequences_and_oligos.zip"

  cd "$current_dir" || return 1
}

# Save recent history as a script
history_to_script() {
  local count=${1:-10}
  local output_file=${2:-"script.sh"}
  fc -ln -"${count}" > "$output_file"
  chmod +x "$output_file"
  echo "Script created at $output_file with last $count commands"
}

unalias recent 2>/dev/null || true
unset -f recent 2>/dev/null || true

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
    count="$1"
  fi

  ls -lt -- "$dir" | head -n "$count"
}
