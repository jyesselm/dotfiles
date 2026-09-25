# Restore an encrypted Mac current-state backup

This archive contains private Alfred settings/workflows/snippets, Bartender preferences (including its stored license fields), Alfred activation files, Karabiner settings, the selected macOS preferences snapshot, and an app/Homebrew inventory. Never commit its decrypted contents or recovery key to public Git.

## Decrypt and inspect

Install GnuPG (`brew install gnupg`). Retrieve the recovery key from your password manager. Decrypt with the interactive password prompt, keeping the key out of command history:

```sh
umask 077
gpg --output mac-state.tar.gz --decrypt mac-state.tar.gz.gpg
mkdir restored-mac-state
tar -xzf mac-state.tar.gz -C restored-mac-state
```

Use `inventory.json` to see names, versions, bundle IDs, installed paths, and Homebrew packages. This is a record, not an instruction to install every app. App binaries, purchase receipts, App Store sign-ins, and app data are not included. Inventory scans /Applications, ~/Applications and /System/Applications, stopping at app bundles; apps elsewhere are not enumerated. The backup includes a manifest of file SHA-256 hashes.

## Alfred

1. Install Alfred and activate Powerpack with your purchased license.
2. Back up any destination Alfred configuration first. Quit Alfred before replacing settings.
3. Keep `alfred/active/Alfred.alfredpreferences` in a permanent folder. In Alfred Preferences → Advanced, select its parent as the preferences folder. If using the existing Dropbox sync folder, let it finish downloading and make the bundle available offline first. Do not overwrite a newer shared bundle with this older snapshot unintentionally.
4. The backup also has the separate original local bundle (`alfred/local/` when present), the original `prefs.json`, and local settings embedded in the active bundle. They are reference/rollback copies. Do not blindly overwrite `prefs.json` on a new machine: it contains source-machine paths. Preferences under `preferences/local/<machine-id>` may need to be recreated for the new Mac in Alfred's UI.
5. Check your main hotkey, selected theme, search scope, clipboard settings and snippet auto-expansion individually. Alfred intentionally does not sync these between Macs. Workflows can need separate dependencies, login/API tokens, permissions or application installs.

`alfred/activation/powerpack.*.dat` preserves existing activation data. These opaque files are NOT a recovered, portable original license key, and copying them may not activate a new Mac. Recover the actual license from the original “Alfred Powerpack” purchase email or Alfred support. Neither email nor Keychain is searched by this backup tool.

Alfred documentation: https://www.alfredapp.com/help/advanced/sync/ and https://www.alfredapp.com/help/powerpack/

## Bartender

1. Install a Bartender version compatible with the destination macOS and your license. Your captured version is recorded in inventory.json; no forced upgrade is part of this backup.
2. Quit Bartender. First back up the destination preferences:

```sh
defaults export com.surteesstudios.Bartender bartender-before-restore.plist
# With Bartender closed, restore the captured preferences:
defaults import com.surteesstudios.Bartender preferences/com.surteesstudios.Bartender.plist
```

Run those commands from the extracted archive root (adjust paths if needed). This replaces Bartender's complete preference domain. Its saved layouts, profiles, triggers and stored license fields are included, along with old machine/window metadata. Copy any archived `bartender/Application Support` files only after backing up destination files. Relaunch and re-grant macOS permissions if requested. Menu items/displays differ across Macs, so inspect layout and shortcuts rather than assuming exact placement. Activation may require entering the original license again. The stored license value is private; do not paste it in logs or chat.

License recovery: https://www.macbartender.com/Bartender5/support/

## Existing dotfiles

Use yadm to restore terminal configurations. The archive also includes a copy of current Karabiner configuration and the selected Mac system snapshot as an extra fallback; current yadm may be newer. `mac-settings plan` and `mac-settings restore` handle that system snapshot separately with a backup.

No applications are stopped, preferences imported, licensing changed, or workflows executed while making this backup. Clipboard/search history databases, Alfred Workflow Data, and full app caches are excluded. Configuration files can still contain private tokens, scripts, snippets and license information, which is why the whole archive is encrypted.

This is a point-in-time file snapshot, not a transactional full-machine backup. Avoid editing app configuration while capturing it; per-file changes during a read stop the backup. Keep Time Machine or another full backup for everything outside this scope.
