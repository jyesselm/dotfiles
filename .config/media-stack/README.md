# Media stack

Everything that finds, downloads and organizes media runs from `compose.yml` in this folder. Plex is the only
piece outside it while the server is a Mac, because Docker on macOS can't use Apple's hardware transcoding.

| Service | Port | Role |
|---|---|---|
| Plex (native on the Mac) | 32400 | Streaming |
| Seerr | 5055 | Requests from you and your wife |
| Radarr / Sonarr | 7878 / 8989 | Movies / TV: find, grab, rename, file |
| Prowlarr | 9696 | Indexers, synced to Radarr and Sonarr |
| gluetun + qBittorrent | 8080 | Torrents, only through NordVPN (no tunnel, no internet) |
| Homepage | 3000 | Dashboard |
| Uptime Kuma | 3001 | Up/down history and alerts |

A request flows Seerr → Radarr/Sonarr → Prowlarr → qBittorrent → hardlinked into `Movies` / `TV Shows` → Plex.

## Files

- `compose.yml`, `homepage/`, `gluetun-auth.toml`: tracked in dotfiles, no secrets.
- `.env`: untracked, this machine's paths and keys. Template: `env.example`.
- `$DATA_ROOT/<app>/config` (and `$DATA_ROOT/uptime-kuma`): each app's settings and database. Not tracked; this is
  what you copy to move the stack.
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

## Moving to Linux

1. **Disk format.** `Plex_Disk_4` is journaled HFS+. Linux mounts it read-only unless journaling is turned off, so
   plan to move the data to an ext4 disk (copy 5.8 TB off, reformat, copy back, or buy a new disk and copy across).
   Mount it somewhere fixed, e.g. `/mnt/plex`, via `/etc/fstab`.
2. **Install** Docker Engine with the compose plugin, clone the dotfiles (`yadm` linux class), and copy
   `env.example` to `.env`.
3. **Stop the Mac stack** (`docker-compose down`, quit Plex), then copy the app data across:
   `rsync -a ~/.local/share/{radarr,sonarr,prowlarr,seerr,qbittorrent,uptime-kuma} newhost:~/.local/share/`.
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
