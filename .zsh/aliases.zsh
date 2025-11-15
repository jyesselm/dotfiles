# ~/.zsh/aliases.zsh

# Safer ls (you’re using lsd)
alias ls='lsd'
alias la='ls -A'
alias l='ls -CF'
alias lt='ls -lt | head'

# Editors
alias vi='nvim'
alias vim='nvim'

# Directories
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

# RNA tools
alias rnafoldp='rnafold -p --noLP -d2'

# Zip dir
alias zip-dir='function _zipdir(){ zip -r "${1%/}.zip" "$1"; }; _zipdir'

# TSV → CSV
alias tsv2csv='function _tsv2csv(){ local filename="${1%.*}"; awk -v OFS="," -F"\t" '\''{ $1=$1; print }'\'' "$1" > "${filename}.csv"; }; _tsv2csv'

alias z='zoxide'
alias zl='zoxide query -l | head -10'

# Config shortcuts
alias ez='nvim ~/.zshrc'
alias eza='nvim ~/.zsh/aliases.zsh'
alias ezp='nvim ~/.zsh/paths.zsh'


