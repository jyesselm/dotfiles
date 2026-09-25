# Preserve your Mac preferences

Keep yadm as the source of truth for your customizations. Nix, if adopted later, only needs to install terminal programs; it does not need to replace these settings.

## Save on your configured Mac

```sh
~/.local/bin/mac-settings save
yadm diff -- .config/yadm/macos/preferences.plist
# After reviewing the snapshot:
yadm add .config/yadm/macos/preferences.plist
yadm commit -m 'Save current Mac preferences'
yadm push
```

Saving reads preferences and writes a snapshot. It does not change live preferences. The snapshot contains selected explicit settings and records which supported keys are unset (using macOS defaults). It is not an image of the whole Mac. Each replaced snapshot receives a unique local backup.

## Restore on a new Mac

Clone your yadm repository and run the regular bootstrap first. Desktop apps remain optional. Then:

```sh
~/.local/bin/mac-settings plan       # show changed key names; read-only
# Close System Settings and affected apps before restoring:
~/.local/bin/mac-settings restore
```

Restore is deliberately separate from `yadm bootstrap` and `--desktop`. It changes only the allowlisted keys recorded in the snapshot. Other preferences remain untouched. No applications are killed or restarted. Log out and back in when convenient to refresh cached settings; a running app can otherwise overwrite preferences.

Before any restore changes, the tool saves the current supported settings under `~/.local/state/dotfiles/mac-settings/`. The displayed backup is itself restorable:

```sh
~/.local/bin/mac-settings plan --file /path/to/backup.plist
~/.local/bin/mac-settings restore --file /path/to/backup.plist
```

A failed write stops the restore with the backup path; earlier writes may have applied. Rollback is explicit. The backup directory is local, outside the public yadm repository. Snapshot files are mode 0600 on creation (Git does not preserve Unix read permissions on another clone).

## Included in the system snapshot

- Keyboard repeat, press-and-hold, full keyboard navigation, text correction toggles, global app menu shortcuts, and macOS symbolic shortcuts.
- Dock size, position, hiding, effects, recent-app visibility, hot corners, and selected Spaces behavior.
- Finder visibility, preferred view, path/status bars, and desktop disk visibility.
- Mouse/trackpad scrolling, tracking, clicking, dragging, and supported gestures.
- Appearance/accent/scrollbar preferences and screenshot format/thumbnail behavior.

Only explicit values present on the source Mac are saved as values. Unset keys are reset on restore, so their effective defaults can differ between macOS versions. Settings unsupported on another OS version or device may have no effect. Host-specific `ByHost` settings are not captured.

## App configurations and remaining exports

Yadm already tracks iTerm2 (`.config/iterm2/com.googlecode.iterm2.plist`), Karabiner (`.config/karabiner/karabiner.json`), and VS Code/Cursor settings. The current Karabiner gaming profile is preserved with this change. A tracked file alone does not prove that an application is currently loading it; verify the app uses that configuration on a new Mac. Terminal fonts, privacy/accessibility permissions, and app sign-ins may need setup on the destination.

Installed customization apps needing a separate review/export include **BetterTouchTool, Alfred, Bartender, Contexts, Rectangle, Magnet, and Ghostty**. Use each app's supported export/sync mechanism and review exports before adding them to yadm. They are not covered by this system snapshot. BetterTouchTool actions and Alfred workflows, for example, can live outside the usual preference plist.

Intentionally excluded: app licenses, credentials, browser profiles, recent-file lists, Dock pinned-app/folder bookmarks, Finder favorites and folder-specific layouts, wallpaper files, text replacements, display layouts, login items, and account/cloud state. Keep full-machine backups (such as Time Machine) as well. Some app preference domains contain license keys; do not publish entire `~/Library/Preferences` or `Application Support` folders into the public dotfiles repo.

The optional desktop Brewfile currently covers iTerm2, VS Code, Cursor, and Obsidian. It does not yet install every customization app above.

## Maintenance

The allowlist is in `.config/yadm/setup/mac-settings.py`. Expand it deliberately for additional portable keys. Run `python3 ~/.config/yadm/setup/test_mac_settings.py` for isolated regression checks. Read-only `mac-settings plan` checks whether saved keys differ from the current Mac.
