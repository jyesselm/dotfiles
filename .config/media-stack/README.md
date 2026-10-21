# Media stack

Everything that finds, downloads and organizes media runs from `compose.yml` in this folder. Plex is the only
piece outside it while the server is a Mac, because Docker on macOS can't use Apple's hardware transcoding.

| Service | Port | Role |
|---|---|---|
| Plex (native on the Mac) | 32400 | Streaming |
| Seerr | 5055 | Requests from you and your wife |
| Radarr / Sonarr / Lidarr | 7878 / 8989 / 8687 | Movies / TV / music: find, grab, rename, file |
| spotDL | 8800 | Single songs: paste a Spotify link, saved to `music/` (built from `spotdl/` with current yt-dlp) |
| Sonobarr | 8688 | Music discovery: Last.fm artists similar to yours, one click adds them to Lidarr |
| Prowlarr | 9696 | Indexers, synced to Radarr, Sonarr and Lidarr |
| FlareSolverr | 8191 (internal only) | Cloudflare challenge helper for Prowlarr |
| gluetun + qBittorrent | 8080 | Torrents, only through NordVPN (no tunnel, no internet) |
| PairDrop | 3010 | Send files between devices in the browser (open it on both; Taildrop also works) |
| Homepage | 3000 | Dashboard |
| Uptime Kuma | 3001 | Up/down history and alerts |
| Gamarr | 5001 | Games: searches Prowlarr, downloads via qBittorrent, hardlinks ROMs into `Games/roms` for RomM |
| RomM (+ MariaDB) | 8090 | Retro game library, play in the browser (`Plex_Disk_4/Games`) |
| Media Index | 8686 | Disk use by title, Plex watch history, keep/delete/shrink review (`media-index/`) |

A request flows Seerr → Radarr/Sonarr → Prowlarr → qBittorrent → hardlinked into `Movies` / `TV Shows` → Plex. Music is the same
without Seerr: add artists in Lidarr (or pick them from Sonobarr's suggestions), which files albums into `music/` (Plex
Music library, Plexamp app). Lidarr only fetches whole albums, so for one song paste its Spotify link into spotDL instead;
if spotDL fails with YouTube 403/429 errors, `docker-compose build --pull spotdl && docker-compose up -d spotdl`.
Lidarr unmonitors tracks you delete, so trimming an album in Media Index doesn't re-download it.

## Files

- `compose.yml`, `homepage/`, `gluetun-auth.toml`: tracked in dotfiles, no secrets.
- `.env`: untracked, this machine's paths and keys. Template: `env.example`.
- `$DATA_ROOT/<app>/config` (and `$DATA_ROOT/uptime-kuma`): each app's settings and database. Not tracked; this is
  what you copy to move the stack.
- `app-config/`: tracked, secret-free JSON of each app's settings (Plex libraries and playlists, custom formats, quality profiles, naming, root
  folders, download clients, Prowlarr apps, Seerr settings). Refresh with `./export-config.sh` after changing
  settings, then commit. It's the reference for rebuilding an app by hand if `$DATA_ROOT` is lost; API keys,
  passwords and indexers are left out, so re-enter those.
- The media disk is always mounted at `/Volumes/Plex_Disk_4` inside containers, whatever its host path, so the
  paths stored in Radarr, Sonarr, qBittorrent and Plex stay valid on any machine. Downloads (`downloading/`) and
  the libraries share that one disk so imports are instant hardlinks.

## Everyday commands

```sh
cd ~/.config/media-stack
docker-compose up -d                 # start / apply changes
docker-compose pull && docker-compose up -d   # update all images
docker-compose logs -f gluetun       # watch one service
docker-compose ps                    # health at a glance (or the dashboard)
```

On the Mac, `docker-compose` comes from OrbStack (on PATH via `.zsh/tools.zsh`); OrbStack starts at login and needs
Removable Volumes access to reach the disk.

## NordVPN key (once)

gluetun needs your NordVPN WireGuard private key in `.env` as `NORDVPN_WIREGUARD_KEY`. Get an access token at
Nord Account → NordVPN → Set up NordVPN manually, then turn it into the key as described at
https://github.com/qdm12/gluetun-wiki/blob/main/setup/providers/nordvpn.md. Then `docker-compose up -d`
and check `docker-compose logs gluetun` shows the public IP of a Nord server.

## Media Index (cleanup)

`media-index/` indexes the disk daily (sizes, ffprobe video info, watch history from Plex's dated database backups) and
serves a review page on 8686. Mark each title Keep, Shrink (worth re-encoding to HEVC) or Delete. "Move to trash"
renames Delete items into `Plex_Disk_4/_trash/` and unmonitors them in Radarr/Sonarr; restore from the page. Nothing is
permanently deleted until you empty `_trash` yourself, e.g. `rm -rf /Volumes/Plex_Disk_4/_trash/*`. Music is reviewed per song:
pick ♪ Music in the type chips, press `p` (or ▶) to listen, and `1`/`3` keep or delete; while a song plays, moving or deciding plays
the next one. Plex's automatic scan drops trashed songs from the library. Items hardlinked with
a torrent in `downloading/` free space only once the torrent is removed in qBittorrent too. Its database is
`$DATA_ROOT/media-index/media-index.db`; don't open it from macOS while the container runs (use `docker exec`).

**Shrink** titles are re-encoded on the Mac itself by `media-index/shrink.py` (Docker can't reach the hardware encoder).
It reads `GET /api/shrink-queue`, encodes one file at a time with `hevc_videotoolbox` at quality 75 (scored VMAF ≥ 95,
i.e. looks the same, on Blu-ray and DVD-rip samples), copies audio/subtitles, and writes `.mkv`. A result replaces the
original only if its duration matches within 1 s and it is at least 20% smaller; the original moves to
`_trash/<same path>`. Old SD and low-bitrate rips usually don't get 20% smaller at that quality, so they're kept as-is.
After each title it asks Radarr/Sonarr to rescan and sets the title to Keep with a "shrunk" note. Torrent-hardlinked
files are skipped (`--include-hardlinked` to override). Files that failed or weren't worth it are remembered in
`~/.local/share/media-index/encode-skip.json` (delete a line to retry). Log: `~/.local/share/media-index/encode.log`.
Run from launchd, Homebrew's `ffmpeg`/`ffprobe` need macOS's Removable Volumes permission, which is tied to the exact
binary: allow both once at the Mac and keep them with `brew pin ffmpeg` (re-allow after any upgrade). Without it the
nightly run logs "ffprobe can't read" and stops. macOS won't let launchd's Python change the disk at all, so the
final swap (original to `_trash`, encode into place) is done by the container via `POST /api/shrink-finish`; the
media-index container must be up for a run to finish a file.

```sh
python3 media-index/shrink.py run --dry-run                 # what's queued
python3 media-index/shrink.py run --match "S02E05" --limit 1  # one file now
python3 media-index/shrink.py install                       # nightly at 01:00; no new file starts after 08:00
```

**Music upgrades** to 320 kbps go through Lidarr, run by `media-index/music_upgrade.py` (daily at 03:00). Lidarr only
grabs whole albums, so the script monitors up to 10 albums holding your lowest-bitrate songs under an "Upgrade to 320"
profile and searches them again each day. Once every song you had is at 320, it deletes the album's other tracks and
unmonitors it. Albums with no 320 release after 14 days are dropped. Replaced and removed files go to
`Plex_Disk_4/_trash/lidarr` (Lidarr's recycle bin, never emptied automatically). Songs Lidarr doesn't know (most
YouTube rips) are skipped; re-get those with spotDL.

```sh
python3 media-index/music_upgrade.py status
python3 media-index/music_upgrade.py run --dry-run          # what would start or finish
```

**Drive manifests** record what is on each media drive, so you can see which drive holds a title while it's
unplugged. `media-index/drives.py catalog` writes one row per file (path, size, mtime) to
`~/.local/share/media-index/drives/<drive>.tsv` and to `.media-manifest.tsv` on the drive itself. Re-run it
after changing a drive. A file counts as copied when another drive has the same name and size (or the same size for
files over 50 MB, which catches renames).

```sh
python3 media-index/drives.py catalog "/Volumes/Plex Disk 1"   # after plugging a drive in
python3 media-index/drives.py where supernatural               # which drives hold it
python3 media-index/drives.py missing "Plex Disk 1" Plex_Disk_4  # titles not yet copied
```

## Moving to Linux

1. **Disk format.** `Plex_Disk_4` is journaled HFS+. Linux mounts it read-only unless journaling is turned off, so
   plan to move the data to an ext4 disk (copy 5.8 TB off, reformat, copy back, or buy a new disk and copy across).
   Mount it somewhere fixed, e.g. `/mnt/plex`, via `/etc/fstab`.
2. **Install** Docker Engine with the compose plugin, clone the dotfiles (`yadm` linux class), and copy
   `env.example` to `.env`.
3. **Stop the Mac stack** (`docker-compose down`, quit Plex), then copy the app data across:
   `rsync -a ~/.local/share/{radarr,sonarr,lidarr,prowlarr,seerr,qbittorrent,uptime-kuma,audiobookshelf,romm,gamarr} newhost:~/.local/share/`.
4. **Edit `.env`**: `MEDIA_ROOT=/mnt/plex`, `DATA_ROOT=/home/<you>/.local/share`, `PUID`/`PGID` from `id`
   (usually 1000), `HOMEPAGE_ALLOWED_HOSTS` for the new address, keys unchanged.
   Seerr runs as uid 1000: `sudo chown -R 1000:1000 $DATA_ROOT/seerr/config`.
5. **Add Plex to `compose.yml`** (hardware transcoding needs an Intel/AMD GPU at `/dev/dri` and Plex Pass):
   ```yaml
   plex:
     image: lscr.io/linuxserver/plex:latest
     container_name: plex
     restart: unless-stopped
     network_mode: host
     devices: [/dev/dri:/dev/dri]
     environment: {PUID: "${PUID}", PGID: "${PGID}", TZ: "${TZ}", VERSION: docker}
     volumes:
       - ${DATA_ROOT}/plex/config:/config
       - ${MEDIA_ROOT}:/Volumes/Plex_Disk_4
   ```
   Move Plex's data per https://support.plex.tv/articles/201370363 : copy the Mac's
   `~/Library/Application Support/Plex Media Server/` to `$DATA_ROOT/plex/config/Library/Application Support/Plex Media Server/`.
   Library folders keep working because the disk is mounted at the same path.
6. **Repoint Plex** in the other apps: set `HOST_ADDR` to the Linux host's LAN IP (Plex uses host networking),
   and in Seerr → Settings → Plex use that IP too.
7. `docker-compose up -d`, open the dashboard, and check every tile is green. Request one movie to test the chain.

## Games (RomM)

RomM serves the game library at port 8090 and plays most pre-PS2 systems in the browser (EmulatorJS), with saves per
account. Put ROMs of games you own in `Plex_Disk_4/Games/roms/<platform>/` (slugs from docs.romm.app → Supported
Platforms; `nes snes n64 genesis gb gbc gba ps dos` exist) and firmware in `Games/bios/<platform>/`, then
Library → Scan in the web UI. The first visit creates the admin account; add other users under Administration.
Covers come from keyless sources (Hasheous, LaunchBox, Playmatch); for better matches set the IGDB and ScreenScraper
values in `.env` and `docker-compose up -d romm`. Its data and MariaDB database are in `$DATA_ROOT/romm/`. On a TV,
RetroArch on the Onn plays the same files with a controller.

Gamarr (port 5001) is the *arr for games: search a title, pick a result, and it downloads through qBittorrent
(category `games`) and hardlinks ROMs into `Games/roms/<platform>/` (PC games into `Games/pc/`). It is a small,
young project; check what a release contains before opening it, and never run `.exe` files from a ROM download.

## FlareSolverr

Prowlarr reaches FlareSolverr at `http://flaresolverr:8191` over the Compose network.
The API is internal only; no host port is published. In Prowlarr → Settings → Indexers →
Indexer Proxies, the FlareSolverr proxy uses the `flaresolverr` tag. The existing indexers carry this tag so the helper is available when needed. Assign the same tag
to new indexers that need it. Prowlarr uses the proxy when an applicable indexer encounters
Cloudflare protection. No persistent data directory is needed.
