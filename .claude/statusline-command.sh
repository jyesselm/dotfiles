#!/bin/bash
# Claude Code status line.
# Mirrors the user's Starship prompt (directory truncated to repo root, git
# branch) and adds the active Claude model name.

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir')
model=$(echo "$input" | jq -r '.model.display_name')

# --- Directory: repo-relative path if inside a git repo, else basename ---
repo_root=$(git -C "$cwd" --no-optional-locks rev-parse --show-toplevel 2>/dev/null)
if [ -n "$repo_root" ]; then
  repo_name=$(basename "$repo_root")
  rel_path="${cwd#$repo_root}"
  rel_path="${rel_path#/}"
  if [ -z "$rel_path" ]; then
    dir_display="$repo_name"
  else
    dir_display="$repo_name/$rel_path"
  fi
else
  dir_display=$(basename "$cwd")
fi

# --- Git branch ---
branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)

# --- Colors (dimmed, since the status line renders in dimmed color already) ---
DIM_BLUE='\033[2;34m'
DIM_GREEN='\033[2;32m'
DIM='\033[2m'
RESET='\033[0m'

line="${DIM_BLUE}${dir_display}${RESET}"
if [ -n "$branch" ]; then
  line="${line} ${DIM_GREEN}${branch}${RESET}"
fi
line="${line} ${DIM}[${model}]${RESET}"

printf "%b" "$line"
