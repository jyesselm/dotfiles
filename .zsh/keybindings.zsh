# Shared hotkeys. Load after plugins, Atuin, and local overrides.
bindkey -e

# Search history with Atuin, falling back to fzf or built-in history.
if (( $+widgets[atuin-search] )); then
  bindkey '^R' atuin-search
elif (( $+widgets[fzf-history-widget] )); then
  bindkey '^R' fzf-history-widget
else
  bindkey '^R' history-incremental-search-backward
fi

if (( $+widgets[fzf-file-widget] )); then
  bindkey '^T' fzf-file-widget
fi
if (( $+widgets[fzf-cd-widget] )); then
  bindkey '^[c' fzf-cd-widget
fi

# Ctrl+G: enter a frequent directory without replacing the pending command.
if (( $+commands[zoxide] && $+commands[fzf] )); then
  zoxide-widget() {
    local selected
    selected=$(zoxide query -l 2>/dev/null | fzf --height 40% --reverse --no-sort) || return 0
    if [[ -n $selected ]]; then
      builtin cd -- "$selected" || return
    fi
    zle reset-prompt
  }
  zle -N zoxide-widget
  bindkey '^G' zoxide-widget
fi

# Arrow keys: search history by the prefix already typed, in either cursor mode.
for key in '^[[A' '^[OA'; do
  bindkey "$key" history-search-backward
done
for key in '^[[B' '^[OB'; do
  bindkey "$key" history-search-forward
done
unset key

# Keep word movement consistent even when dirhistory is installed.
bindkey '^[b' backward-word
bindkey '^[f' forward-word
bindkey '^[[Z' reverse-menu-complete

autoload -Uz edit-command-line
zle -N edit-command-line
bindkey '^X^E' edit-command-line
