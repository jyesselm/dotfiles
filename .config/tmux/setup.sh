#!/bin/sh
# Install the tested tmux plugin set without modifying existing checkouts.
set -eu
config_dir=${TMUX_CONFIG_DIR:-"$HOME/.config/tmux"}
plugin_root=${TMUX_PLUGIN_ROOT:-"$HOME/.tmux/plugins"}
for tool in tmux git fzf; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'tmux setup: install %s, then rerun yadm bootstrap.\n' "$tool" >&2
        exit 1
    fi
done
if ! tmux -V | awk '{split($2,v,"."); exit !(v[1]>3 || (v[1]==3 && v[2]+0>=6))}'; then
    printf 'tmux setup: tmux 3.6+ is required for this status-bar configuration.\n' >&2
    exit 1
fi
mkdir -p "$plugin_root"
while read -r name repository revision; do
    case "$name" in ''|'#'*) continue ;; esac
    destination=$plugin_root/$name
    if [ -e "$destination" ]; then
        printf 'Keeping installed tmux plugin: %s\n' "$name"
        continue
    fi
    git clone --no-checkout "$repository" "$destination"
    git -C "$destination" checkout --detach "$revision"
    git -C "$destination" submodule update --init --recursive
done < "$config_dir/plugins.lock"
sh "$config_dir/sync-which-key.sh"
printf 'tmux plugins ready. Start a new terminal and run tmux.\n'
printf 'For an existing tmux server: tmux source-file ~/.tmux.conf\n'
