#!/bin/bash
# Nightly backup of every app's settings and databases (not media, not cover art), and a weekly reminder to bring
# the backup drives up to date.
#
# Databases are copied with SQLite's .backup (consistent while the apps run) and RomM's MariaDB with mysqldump;
# everything else under each app's data folder is copied as-is, minus covers, logs and the apps' own backups, which
# re-download or regenerate. The result is one settings-YYYY-MM-DD.tar.gz in ~/backups/media-stack and, when the
# disk is mounted, in plex-media/_backups/settings. The newest KEEP in each place are kept.
#
# The reminder re-catalogs plex-media through the media-index container (launchd jobs can't read the disk) and
# shows a notification with how far each full backup drive is behind (media-index/drives.py status).
#
#   ./backup.sh            # back up settings now
#   ./backup.sh remind     # check the backup drives now
#   ./backup.sh install    # settings nightly at 04:00, reminder Sundays at 10:00, via launchd
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
APPS=(radarr sonarr lidarr prowlarr seerr qbittorrent uptime-kuma audiobookshelf romm gamarr media-index homepage)
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
    install_job "$LABEL-remind" \
        "<key>Weekday</key><integer>0</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer>" \
        "$HERE/backup.sh" remind
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

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
name="settings-$(date +%F)"
mkdir -p "$stage/$name"
cd "$stage/$name"

# App folders, minus regenerable data; live databases are copied separately below.
for app in "${APPS[@]}"; do
    [[ -d "$DATA_ROOT/$app" ]] || continue
    rsync -a --exclude MediaCover --exclude Backups --exclude logs --exclude 'logs.db*' --exclude ipc-socket \
        --exclude '*.db' --exclude '*.db-wal' --exclude '*.db-shm' --exclude '*.sqlite*' \
        --exclude 'romm/db' --exclude 'romm/redis' "$DATA_ROOT/$app" .
    find "$DATA_ROOT/$app" \( -name MediaCover -o -name Backups \) -prune -o \
        -type f \( -name '*.db' -o -name '*.sqlite' \) ! -name 'logs.db' -print | while read -r db; do
        out="./${db#"$DATA_ROOT"/}"
        mkdir -p "$(dirname "$out")"
        sqlite3 "$db" ".backup '$out'"
    done
done
docker exec romm-db sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction romm' >romm/romm.sql

# Plex: preferences and the two library databases (its artwork in Metadata/ and Media/ is rebuilt by a refresh).
mkdir -p plex/Databases
cp "$HOME/Library/Preferences/com.plexapp.plexmediaserver.plist" plex/
for db in com.plexapp.plugins.library.db com.plexapp.plugins.library.blobs.db; do
    "$PLEX_SQLITE" "$PLEX/Plug-in Support/Databases/$db" ".backup 'plex/Databases/$db'"
done
cp "$HERE/.env" "$HOME/.local/share/media-index/encode-skip.json" . 2>/dev/null || true

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
