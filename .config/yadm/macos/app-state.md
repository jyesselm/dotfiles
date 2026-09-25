# Alfred, Bartender and the current Mac state

Use `~/.local/bin/mac-state save` to create a verified encrypted snapshot. Requires macOS, Python 3.9+, and GnuPG (`brew install gnupg`). It captures:

- Active Alfred preferences (currently in Dropbox), workflows, snippets, keyboard shortcuts and local preference copies.
- Alfred activation files, preserving existing data without claiming they are a portable original license key.
- Bartender preferences including layouts, triggers and stored license fields.
- Current Karabiner and saved macOS system-preference snapshot as fallbacks.
- Installed app names, versions, bundle IDs and locations; Homebrew formula/cask inventory.

`mac-state save` saves the already captured macOS snapshot; first run `mac-settings save` if you also want to refresh those system preferences.

The backup is AES-256 encrypted through GnuPG with a randomly generated recovery key. After encryption the script decrypts it in a private temporary directory and verifies both the complete archive and every manifest file checksum. Temporary plaintext is then removed. No live preferences are changed and no application is stopped.

Each backup and a separate `RECOVERY-KEY.txt` are stored in a timestamped folder under `~/.local/state/dotfiles/mac-state/`. Move the key into a password manager such as 1Password. Keep it separately from the encrypted archive: losing both this Mac and the key makes the backup unrecoverable. The key is never printed by this tool or included in the archive. Local key and archive files are private (0600); anyone with access to both can decrypt the backup.

A metadata-only app inventory is refreshed in `~/.config/yadm/macos/applications.json`. Review and commit this file to yadm when you want to sync the latest installed-app list. It contains no app preference contents, license fields, local paths, or clipboard/history data. The backup script itself and restore instructions are tracked in yadm; encrypted archives and recovery keys are not.

To explicitly copy a future encrypted snapshot to a private sync folder:

```sh
mac-settings save
mac-state save --destination "$HOME/Library/CloudStorage/Dropbox/Mac-state-backups"
```

Only the encrypted archive and its SHA-256 file are copied. **The recovery key stays local until you save it in your password manager.** This command does not verify the cloud client's upload status. The folder must be private; do not share keys or decrypted archives publicly.

The app inventory records what was present, not what to reinstall automatically. Old versions may no longer be downloadable. No license-key search through email or Keychain is performed, and unrelated apps' licenses are not backed up. Alfred's original purchase code may need recovery via its purchase email/support; Bartender activation may also need the original code on another Mac.

See `~/.config/yadm/setup/mac-state-restore.md` (also included inside the encrypted backup) for restore instructions and coverage limitations. Alfred's per-Mac settings and macOS privacy permissions may need manual adjustment. This complements a full-machine backup.

Run `python3 ~/.config/yadm/setup/test_mac_state.py` for isolated tests; these do not read real app settings or license data.
