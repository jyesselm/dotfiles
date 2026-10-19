# Tool paths and environment; loaded before plugins.
typeset -U path

# Paths installed by converge. Load before Oh My Zsh on each platform.
# Only terminal commands are exposed; the managed environment's Python is not.
if [[ -d "$HOME/.local/share/dotfiles/bin" ]]; then
  path=("$HOME/.local/share/dotfiles/bin" $path)
fi
for dotfiles_brew_prefix in /opt/homebrew /usr/local /home/linuxbrew/.linuxbrew; do
  if [[ -x "$dotfiles_brew_prefix/bin/brew" ]]; then
    if $IS_MACOS; then
      eval "$("$dotfiles_brew_prefix/bin/brew" shellenv)"
    else
      path+=("$dotfiles_brew_prefix/bin" "$dotfiles_brew_prefix/sbin")
    fi
    break
  fi
done
unset dotfiles_brew_prefix
export PATH

# Load secrets (API tokens, etc.) - not tracked by yadm; the old way, kept until every key is in secrets.refs
[[ -f ~/.zsh/secrets.zsh ]] && source ~/.zsh/secrets.zsh

# API keys: ~/.zsh/secrets.refs (tracked, no values) lists `NAME  op://vault/item/field`. `keys sync` copies the values from
# 1Password into the login Keychain (one Touch ID); every shell loads them from there with no prompt and no op call.
# `keys` shows which are set, `keys add NAME op://…` adds one and syncs.
_KEYS=~/.zsh/secrets.refs
_op_id() {   # newest Personal item titled $1 (several can share a title), or nothing
  op item list --vault Personal --format json | python3 -c "import json,sys
m=sorted((i['created_at'],i['id']) for i in json.load(sys.stdin) if i['title']=='$1'); print(m[-1][1] if m else '')"
}
keys() {
  local n r v
  case $1 in
    sync)
      while read -r n r; do
        [[ -z $n || $n == \#* ]] && continue
        v=$(op read "$r") || { print -u2 "keys: cannot read $n from $r"; continue }
        security add-generic-password -U -s zsh-keys -a "$n" -w "$v" && export "$n=$v" && print "synced $n"
      done < $_KEYS ;;
    add) [[ $2 =~ '^[A-Z_][A-Z0-9_]*$' ]] || { print -u2 'usage: keys add NAME [1Password item | op://vault/item/field]'; return 1 }
      r=$3
      if [[ -z $r ]]; then   # paste the value (hidden, not in history): a new 1Password API Credential, or a new value for it
        read -rs "v?Paste $2 (hidden): "; print
        [[ -n $v ]] || return 1
        local id=$(_op_id "$2")
        if [[ -n $id ]]; then op item edit "$id" "credential=$v" </dev/null >/dev/null || return 1
        else op item create --category 'API Credential' --title "$2" --vault Personal "credential=$v" </dev/null >/dev/null || return 1; fi
        r="op://Personal/$2/credential"
      elif [[ $r != op://* ]]; then r="op://Personal/$r/credential"
      fi
      sed -i '' "/^$2 /d" $_KEYS; print -r -- "$2  $r" >> $_KEYS && keys sync ;;
    *) while read -r n r; do
        [[ -z $n || $n == \#* ]] && continue
        [[ -n ${(P)n} ]] && v=set || v=missing
        print "$n  $v  $r"
      done < $_KEYS ;;
  esac
}
# Logins: `pw add NAME [url] [username]` saves a 1Password Login (password typed hidden, or Enter for a generated one; an existing
# NAME gets the new password), `pw NAME` copies its password for 45 s, `pw` lists your logins,
# `pw new [length|words]` copies a fresh random password (24 characters) or a five-word passphrase without saving it. Logins never enter the shell.
pw() {
  local id v
  case $1 in
    '') op item list --vault Personal --categories Login --format json | python3 -c "import json,sys
print('\n'.join(sorted(i['title'] for i in json.load(sys.stdin))))" ;;
    add) [[ -n $2 ]] || { print -u2 'usage: pw add NAME [url] [username]'; return 1 }
      read -rs "v?Password for $2 (hidden; Enter to generate): "; print
      id=$(_op_id "$2")
      if [[ -n $id ]]; then
        if [[ -n $v ]]; then op item edit "$id" "password=$v" </dev/null >/dev/null; else op item edit "$id" --generate-password=letters,digits,symbols,24 </dev/null >/dev/null; fi || return 1
        print "updated $2"
      else
        local u=$4 a=(--category Login --title "$2" --vault Personal)
        [[ -n $3 ]] && a+=(--url "$3")
        [[ -z $u ]] && read -r "u?Username for $2: "
        [[ -n $u ]] && a+=("username=$u")
        if [[ -n $v ]]; then a+=("password=$v"); else a+=(--generate-password=letters,digits,symbols,24); fi
        op item create "${a[@]}" </dev/null >/dev/null || return 1
        print "saved $2"
      fi
      [[ -z $v ]] && pw "$2" ;;
    new) local g=${2:-24}
      python3 -c "import secrets,string,sys
g=sys.argv[1]; sym='!@#%^&*-_=+?'
if g=='words':
    w=[l.strip().lower() for l in open('/usr/share/dict/words') if 4<=len(l.strip())<=8 and l.strip().isalpha()]
    print('-'.join(secrets.choice(w) for _ in range(5))+'-'+str(10+secrets.randbelow(90)))
else:
    while True:   # until it has lower, upper, digit and symbol
        p=''.join(secrets.choice(string.ascii_letters+string.digits+sym) for _ in range(int(g)))
        if all(any(c in k for c in p) for k in (string.ascii_lowercase, string.ascii_uppercase, string.digits, sym)): break
    print(p)" "$g" | tr -d '\n' | pbcopy || return 1
      [[ $g == words ]] && print "copied a five-word passphrase; clears in 45 s" || print "copied a $g-character password; clears in 45 s"
      ( sleep 45; pbcopy < /dev/null ) &! ;;
    *) id=$(_op_id "$1"); [[ -n $id ]] || { print -u2 "pw: no login named $1 (pw lists them)"; return 1 }
      op read "op://Personal/$id/password" | tr -d '\n' | pbcopy && print "copied $1's password; clears in 45 s"
      ( sleep 45; pbcopy < /dev/null ) &! ;;
  esac
}
if [[ -f $_KEYS ]]; then
  while read -r n r; do
    [[ -z $n || $n == \#* ]] && continue
    v=$(security find-generic-password -s zsh-keys -a "$n" -w 2>/dev/null) && export "$n=$v"
  done < $_KEYS
  unset n r v
fi

# Locale & Language
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"

# Editor Configuration
# Set editor (will be overridden by commands.zsh if nvim is available)
export EDITOR="${EDITOR:-vim}"
export VISUAL="${VISUAL:-$EDITOR}"

# Pager Configuration
export PAGER="less"
export LESS="-R -X -F"  # -R: color, -X: no clear, -F: quit if one screen

# Directory Paths
export DROPBOX="$HOME/cloud/Dropbox"
export NOTES="${DROPBOX}/0_notes/"
export ICLOUD="$HOME/cloud/icloud"

# Development Directories
export CODE_DIR="$HOME/local/code"
export PROJECTS_DIR="$HOME/projects"

# Shell Options
# Disable core dumps (optional - can be removed if debugging)
ulimit -c 0 2>/dev/null || true

# Terminal Configuration
# Disable terminal flow control (Ctrl+S/Ctrl+Q)
stty -ixon 2>/dev/null || true

# Application-Specific
# Python
export PYTHONUNBUFFERED=1  # Unbuffered output for Python
export PYTHONDONTWRITEBYTECODE=1  # Don't create .pyc files

# Node.js / npm
export NPM_CONFIG_PREFIX="$HOME/.local"

# Rust (if installed)
[[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"

# LS_COLORS - Catppuccin Mocha theme
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

# macOS Specific
if [[ "$OSTYPE" == "darwin"* ]]; then
  # Disable "zsh: no matches found" error for globs
  setopt NO_NOMATCH
fi

path=("$HOME/.local/bin" $path "$HOME/go/bin")

# Additional system paths; path is unique, so reloads do not duplicate entries.
[[ -d /usr/local/bin ]] && path+=(/usr/local/bin /usr/local/sbin)

# Language Runtimes
# Java (OpenJDK via Homebrew) - appended
if [[ -d "/opt/homebrew/opt/openjdk/bin" ]]; then
  export PATH="$PATH:/opt/homebrew/opt/openjdk/bin"
  export JAVA_HOME="/opt/homebrew/opt/openjdk"
fi

# OrbStack's docker CLI (Plex server media stack) - appended
if [[ -d "/Applications/OrbStack.app/Contents/MacOS/xbin" ]]; then
  export PATH="$PATH:/Applications/OrbStack.app/Contents/MacOS/xbin"
fi

# TeX/LaTeX (macOS only)
if [[ "$(uname)" == "Darwin" ]]; then
  for tex_path in /usr/local/texlive/*/bin/universal-darwin(N); do
    if [[ -d "$tex_path" ]]; then
      export PATH="$PATH:$tex_path"
      break
    fi
  done
fi

if $IS_MACOS; then
  export COLORTERM=truecolor
# Mamba/Conda (Homebrew installation)
if [[ -f "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/conda.sh" ]]; then
  source "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/conda.sh"
  [[ -f "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/mamba.sh" ]] && \
    source "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/mamba.sh"
elif command -v mamba &>/dev/null; then
  export MAMBA_ROOT_PREFIX="$HOME/micromamba"
  eval "$(mamba shell hook --shell zsh)"
fi

mamba activate py3 2>/dev/null

# Force conda/mamba paths to front
if [[ -n "$CONDA_PREFIX" ]]; then
  export PATH="$CONDA_PREFIX/bin:${PATH//$CONDA_PREFIX\/bin:/}"
fi

fi

# uv tool installs (grc, s) win over same-named commands in the conda env; converge doctor checks this.
path=("$HOME/.local/bin" $path)
