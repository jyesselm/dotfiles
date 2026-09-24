#!/bin/sh
# Keep machine-local plugin files in sync with the yadm-managed menu.
set -eu
config_dir=${TMUX_CONFIG_DIR:-"$HOME/.config/tmux"}
plugin_root=${TMUX_PLUGIN_ROOT:-"$HOME/.tmux/plugins"}
plugin_dir=$plugin_root/tmux-which-key
[ -d "$plugin_dir/plugin" ] || exit 0
for pair in 'which-key.yaml:config.yaml' 'which-key.tmux:plugin/init.tmux'; do
    source_file=$config_dir/${pair%%:*}
    target_file=$plugin_dir/${pair#*:}
    if ! cmp -s "$source_file" "$target_file"; then
        cp "$source_file" "$target_file"
    fi
done
