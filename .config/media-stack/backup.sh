#!/bin/bash
# Nightly backup of every app's settings and databases (not media, not cover art), and a weekly reminder to bring
# the backup drives up to date.
#
# Databases are copied with SQLite's backup API (consistent while the apps run) and RomM's MariaDB with mysqldump;
# everything else under each app's data folder is copied as-is, minus covers, logs and the apps' own backups, which
# re-download or regenerate. The archive also holds .env, rclone.conf and the launchd plists. The result is one
# settings-YYYY-MM-DD.tar.gz in ~/backups/media-stack and, when the disk is mounted, in plex-media/_backups/settings
# (newest KEEP in each), plus an encrypted copy in Google Drive through the rclone remote gcrypt (newest CLOUD_KEEP).
# Restoring from Drive needs gcrypt's passwords, saved outside this machine (README → Backups).
#
# The reminder re-catalogs plex-media through the media-index container (launchd jobs can't read the disk) and
# shows a notification with how far each full backup drive is behind (media-index/drives.py status).
#
#   ./backup.sh            # back up settings now
#   ./backup.sh remind     # check the backup drives now
#   ./backup.sh cloud      # mirror CLOUD_FOLDERS to Google Drive now
#   ./backup.sh install    # settings nightly 04:00, cloud Saturdays 01:00, reminder Sundays 10:00, via launchd
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL=com.yesselman.media-backup
KEEP=7
DATA_ROOT="$(sed -n 's/^DATA_ROOT=//p' "$HERE/.env")"
MEDIA_ROOT="$(sed -n 's/^MEDIA_ROOT=//p' "$HERE/.env")"
PLEX="$HOME/Library/Application Support/Plex Media Server"
PLEX_SQLITE="/Applications/Plex Media Server.app/Contents/MacOS/Plex SQLite"
LOCAL_DEST="$HOME/backups/media-stack"
DISK_DEST="$MEDIA_ROOT/_backups/settings"
CLOUD_DEST="gcrypt:"  # rclone crypt remote over gdrive:media-stack-backups
CLOUD_KEEP=4
CLOUD_FOLDERS=(other anime youtube music podcasts audiobooks)  # mirrored to Drive (tv and movies re-download)
CLOUD_GRACE_DAYS=30
APPS=(radarr sonarr bazarr lidarr prowlarr seerr plextraktsync audiobookrequest qbittorrent cleanuparr uptime-kuma audiobookshelf romm gamarr media-index)
export PATH="/Applications/OrbStack.app/Contents/MacOS/xbin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# install_job <label> <StartCalendarInterval keys> <program args...>: write a LaunchAgent and (re)load it.
install_job() {
    local label=$1 when=$2 plist="$HOME/Library/LaunchAgents/$1.plist" args=""
    shift 2
    for arg in "$@"; do args+="<string>$arg</string>"; done
    cat >"$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key><string>$label</string>
	<key>ProgramArguments</key><array>$args</array>
	<key>StartCalendarInterval</key><dict>$when</dict>
	<key>StandardOutPath</key><string>$LOCAL_DEST/backup.log</string>
	<key>StandardErrorPath</key><string>$LOCAL_DEST/backup.log</string>
</dict>
</plist>
PLIST
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    echo "installed $plist"
}

case "${1:-}" in
install)
    mkdir -p "$LOCAL_DEST"
    install_job "$LABEL" "<key>Hour</key><integer>4</integer><key>Minute</key><integer>0</integer>" "$HERE/backup.sh"
    install_job "$LABEL-cloud" \
        "<key>Weekday</key><integer>6</integer><key>Hour</key><integer>1</integer><key>Minute</key><integer>0</integer>" \
        "$HERE/backup.sh" cloud
    install_job "$LABEL-remind" \
        "<key>Weekday</key><integer>0</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer>" \
        "$HERE/backup.sh" remind
    exit 0
    ;;
cloud)
    # Mirror the hard-to-replace folders to Google Drive, encrypted with file names hidden (rclone remote gmedia).
    # Replaced or deleted files move to deleted/<date>/ and are dropped after CLOUD_GRACE_DAYS. Runs in a container
    # because launchd jobs can't read the media disk; the fixed container name stops two runs overlapping.
    rclone_run() {
        docker run --rm --name media-cloud-upload -v "$HOME/.config/rclone:/config/rclone" \
            -v "$MEDIA_ROOT:/media:ro" -v "$LOCAL_DEST:/logs" rclone/rclone:1.71 "$@"
    }
    filters=(--filter "- ._*" --filter "- .DS_Store")  # first match wins, so excludes go first
    for folder in "${CLOUD_FOLDERS[@]}"; do filters+=(--filter "+ /$folder/**"); done
    if rclone_run sync /media gmedia:current "${filters[@]}" --filter "- *" \
        --backup-dir "gmedia:deleted/$(date +%F)" --drive-stop-on-upload-limit --transfers 4 --bwlimit "08:00,5M 23:00,off" \
        --log-file /logs/cloud.log --log-level NOTICE --stats 10m --stats-log-level NOTICE; then
        cutoff="$(date -v-"${CLOUD_GRACE_DAYS}"d +%F)"
        for day in $(rclone_run lsf --dirs-only gmedia:deleted 2>/dev/null | tr -d /); do
            if [[ "$day" < "$cutoff" ]]; then rclone_run purge "gmedia:deleted/$day"; fi
        done
        echo "$(date '+%F %T') cloud sync done"
    else
        echo "$(date '+%F %T') cloud sync failed, see $LOCAL_DEST/cloud.log"
        osascript -e 'display notification "Media upload to Google Drive failed: see ~/backups/media-stack/cloud.log" with title "Media stack backup"'
    fi
    exit 0
    ;;
remind)
    docker exec media-index python drives.py catalog "$MEDIA_ROOT" --name plex-media
    /usr/bin/python3 "$HERE/media-index/drives.py" status --notify
    newest="$(ls -1t "$LOCAL_DEST"/settings-*.tar.gz 2>/dev/null | head -1 || true)"
    if [[ -z "$newest" ]] || (($(date +%s) - $(stat -f %m "$newest") > 2 * 86400)); then
        osascript -e 'display notification "No settings backup in 2 days: see ~/backups/media-stack/backup.log" with title "Media stack backup"'
    fi
    exit 0
    ;;
esac

# Staged under $LOCAL_DEST (not $TMPDIR) so the database container below can mount it.
mkdir -p "$LOCAL_DEST"
stage="$(mktemp -d "$LOCAL_DEST/.stage.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
name="settings-$(date +%F)"
mkdir -p "$stage/$name"
cd "$stage/$name"

# App folders, minus regenerable data; live databases are copied separately below.
for app in "${APPS[@]}"; do
    [[ -d "$DATA_ROOT/$app" ]] || continue
    rsync -a --exclude MediaCover --exclude Backups --exclude logs --exclude 'logs.db*' --exclude ipc-socket \
        --exclude '*.db' --exclude '*.db-*' --exclude '*.sqlite*' --exclude 'corrupt-*' --exclude 'config.bak-*' \
        --exclude 'romm/db' --exclude 'romm/redis' "$DATA_ROOT/$app" .
done
# The apps' SQLite databases are copied with SQLite's backup API from a throwaway container: the apps run inside
# OrbStack's VM, and opening a live database from macOS breaks its shared-memory locking across the VM boundary
# (the apps then fail with "disk I/O error" or corrupt the database). The media-index image has Python's sqlite3.
docker run --rm -v "$DATA_ROOT:/d" -v "$stage/$name:/out" --entrypoint python media-stack-media-index -c '
import pathlib, sqlite3, sys
skip = {"MediaCover", "Backups", "logs"}
for app in sys.argv[1:]:
    for src in sorted(pathlib.Path("/d", app).rglob("*")):
        rel = src.relative_to("/d")
        if src.suffix not in {".db", ".sqlite", ".sqlite3"} or src.name == "logs.db" or not src.is_file():
            continue
        if skip & set(rel.parts) or any(p.startswith(("corrupt-", "config.bak-")) for p in rel.parts):
            continue
        out = pathlib.Path("/out", rel)
        out.parent.mkdir(parents=True, exist_ok=True)
        db, copy = sqlite3.connect(src), sqlite3.connect(out)
        db.backup(copy)
        db.close(), copy.close()
        print("db", rel)
' "${APPS[@]}" | wc -l | xargs echo "databases copied:"
docker exec romm-db sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction romm' >romm/romm.sql

# Plex: preferences and the two library databases (its artwork in Metadata/ and Media/ is rebuilt by a refresh).
mkdir -p plex/Databases
cp "$HOME/Library/Preferences/com.plexapp.plexmediaserver.plist" plex/
for db in com.plexapp.plugins.library.db com.plexapp.plugins.library.blobs.db; do
    "$PLEX_SQLITE" "$PLEX/Plug-in Support/Databases/$db" ".backup 'plex/Databases/$db'"
done
cp "$HERE/.env" "$HOME/.local/share/media-index/encode-skip.json" "$HOME/.config/rclone/rclone.conf" . 2>/dev/null || true
# launchd jobs: Plex autostart (hand-edited, untracked) and the jobs the install commands write.
mkdir -p launchagents
cp "$HOME"/Library/LaunchAgents/{com.yesselman.*,local.plex.*}.plist launchagents/

cd "$stage"
tar --no-xattrs --no-mac-metadata -czf "$name.tar.gz" "$name"
# Script that keeps the newest KEEP archives in folder $1; a string so it runs both here and in the container.
rotate='ls -1t "$1"/settings-*.tar.gz | tail -n +'$((KEEP + 1))' | while read -r old; do rm -f "$old"; done'

mkdir -p "$LOCAL_DEST"
cp "$name.tar.gz" "$LOCAL_DEST/"
sh -c "$rotate" _ "$LOCAL_DEST"
echo "$(date '+%F %T') $LOCAL_DEST/$name.tar.gz $(du -h "$name.tar.gz" | cut -f1)"

# macOS won't let a launchd job write to the media disk, so the media-index container (same mount path) does it.
if docker exec -i media-index sh -c "mkdir -p '$DISK_DEST' && cat >'$DISK_DEST/$name.tar.gz' && $rotate" _ "$DISK_DEST" \
    <"$name.tar.gz"; then
    echo "$(date '+%F %T') $DISK_DEST/$name.tar.gz"
else
    echo "$(date '+%F %T') couldn't copy to $DISK_DEST (disk unplugged or media-index down)"
fi

# Offsite, encrypted. A failure is shown as a notification, since nothing else would notice it.
if rclone copy --quiet "$name.tar.gz" "$CLOUD_DEST" &&
    rclone lsf --quiet --include 'settings-*.tar.gz' "$CLOUD_DEST" | sort -r | tail -n +$((CLOUD_KEEP + 1)) |
    while read -r old; do rclone deletefile --quiet "$CLOUD_DEST$old"; done; then
    echo "$(date '+%F %T') $CLOUD_DEST$name.tar.gz"
else
    echo "$(date '+%F %T') couldn't upload to $CLOUD_DEST"
    osascript -e 'display notification "Upload to Google Drive failed; run: rclone config reconnect gdrive:" with title "Media stack backup"'
fi
