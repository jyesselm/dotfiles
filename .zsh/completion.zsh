# ~/.zsh/completion.zsh
# Enhanced tab completion configuration

# ============================================================
# Enable Completion System
# ============================================================
autoload -Uz compinit

# Only run compinit once per day (faster startup)
# Delete ~/.zcompdump to force regeneration
if [[ -n "${HOME}/.zcompdump(#qN.mh+24)" ]]; then
  compinit
else
  compinit -C
fi

# ============================================================
# Completion Options
# ============================================================
setopt AUTO_LIST              # Automatically list choices on ambiguous completion
setopt AUTO_MENU              # Show completion menu on successive tab presses
setopt AUTO_PARAM_SLASH        # Add trailing slash when completing directories
setopt COMPLETE_IN_WORD        # Complete from both ends of a word
setopt ALWAYS_TO_END          # Move cursor to end after completion
setopt LIST_PACKED             # Use compact completion lists
setopt LIST_ROWS_FIRST         # Show rows first instead of columns

# ============================================================
# Completion Styles
# ============================================================
zstyle ':completion:*' menu select                    # Use menu selection
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'  # Case-insensitive matching
zstyle ':completion:*' list-colors ''                 # Colorize completion
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:kill:*' command 'ps -u $USER -o pid,%cpu,tty,cputime,cmd'

# ============================================================
# Completion Caching
# ============================================================
zstyle ':completion:*' use-cache yes
zstyle ':completion:*' cache-path "$HOME/.cache/zsh"

# ============================================================
# Completion Grouping
# ============================================================
zstyle ':completion:*' group-name ''
zstyle ':completion:*' format '%B%d%b'

# ============================================================
# Specific Completions
# ============================================================
# Git
zstyle ':completion:*:*:git:*' user-commands \
  'add:Add file contents to the index' \
  'branch:List, create, or delete branches' \
  'checkout:Switch branches or restore working tree files' \
  'clone:Clone a repository' \
  'commit:Record changes to the repository' \
  'diff:Show changes' \
  'fetch:Download objects and refs' \
  'merge:Join two or more development histories' \
  'pull:Fetch and integrate changes' \
  'push:Update remote refs' \
  'status:Show working tree status'

# Docker
if command -v docker &> /dev/null; then
  zstyle ':completion:*:*:docker:*' option-stacking yes
  zstyle ':completion:*:*:docker-*:*' option-stacking yes
fi

# ============================================================
# Ignore Completion
# ============================================================
zstyle ':completion:*' ignore-parents parent pwd
zstyle ':completion:*:(rm|kill|diff):*' ignore-line other
zstyle ':completion:*:rm:*' file-patterns '*:all-files'

# ============================================================
# Fuzzy Matching
# ============================================================
# Allow approximate completions
zstyle ':completion:*' completer _complete _match _approximate
zstyle ':completion:*:match:*' original only
zstyle ':completion:*:approximate:*' max-errors 1 numeric

# ============================================================
# Directory Completion
# ============================================================
# Complete . and .. directories
zstyle ':completion:*' special-dirs true

# ============================================================
# Process Completion
# ============================================================
zstyle ':completion:*:processes' command 'ps -ax'
zstyle ':completion:*:processes-names' command 'ps -aeo comm='
zstyle ':completion:*:*:kill:*' menu yes select
zstyle ':completion:*:kill:*' force-list always

# ============================================================
# SSH/SCP Completion
# ============================================================
# Complete hosts from ~/.ssh/known_hosts
zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh/ssh_known_hosts,~/.ssh/known_hosts} 2>/dev/null)"} | awk "/^#?[a-z]/ {print \$1}" | tr "," "\n" | sort -u})})'

# ============================================================
# Custom Completion Functions
# ============================================================
# Completion for custom functions
compdef _gnu_generic snip upload_seqs_and_oligos history_to_script

