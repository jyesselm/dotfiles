# Media stack

Everything that finds, downloads and organizes media runs from `compose.yml` in this folder. Plex is the only
piece outside it while the server is a Mac, because Docker on macOS can't use Apple's hardware transcoding.
The server is the Mac mini `plex-server` (`plex-server.tail2813f4.ts.net` on the tailnet, also the Tailscale exit
node); every port below is open on it. Agents: read `CLAUDE.md` first for the rules that are easy to break.

| Service | Port | Role |
|---|---|---|
| Plex (native on the Mac) | 32400 | Streaming |
| Seerr | 5055 | Requests from you and your wife |
| Audiobookshelf | 13378 | Audiobooks and podcasts (iPhone: ShelfPlayer, server `http://plex-server.tail2813f4.ts.net:13378`) |
| AudioBookRequest | 8000 | Audiobook requests: Audible search → Prowlarr → qBittorrent category `audiobooks` → `audiobooks/` |
| Suwayomi | 4567 | Manga: add a series, it downloads every new chapter as CBZ into `manga/` (Tachiyomi sources, no torrents) |
| Kavita | 5003 | Manga reader with reading progress (web, or Panels/Paperback over OPDS); see Manga |
| Radarr / Sonarr / Lidarr | 7878 / 8989 / 8687 | Movies / TV / music: find, grab, rename, file |
| spotDL | 8800 | Single songs: paste a Spotify link, saved to `music/` (built from `spotdl/` with current yt-dlp) |
| Sonobarr | 8688 | Music discovery: Last.fm artists similar to yours, one click adds them to Lidarr |
| PlexTraktSync | — | Plex ⇄ Trakt ratings and watched status every 6 h (see Movie recommendations) |
| Bazarr | 6767 | English subtitles for foreign-language titles (Radarr/Sonarr auto-tag them `foreign`), synced to the audio |
| Prowlarr | 9696 | Indexers, synced to Radarr, Sonarr and Lidarr |
| FlareSolverr | 8191 (internal only) | Cloudflare challenge helper for Prowlarr |
| gluetun + qBittorrent | 8080 | Torrents, only through NordVPN (no tunnel, no internet); 3 downloads / 2 uploads / 5 active, slow ones don't hold a slot, announces to all trackers; full speed only 2–6 am (see *The disk*) |
| Cleanuparr | 11011 | Removes downloads that stay stalled, blocklists the release and has Radarr/Sonarr search again |
| PairDrop | 3010 | Send files between devices in the browser (open it on both; Taildrop also works) |
| Dashboard | 3000 | Home page: recently added, now playing, requests, a Watch tab of what to stream elsewhere, downloads, storage review, machines, backups, service health (`dashboard/`, own code). Mac stats and Tailscale state come from `python3 dashboard/host-stats.py install` (launchd, every minute) |
| Uptime Kuma | 3001 | Up/down history and alerts |
| Gamarr | 5001 | Games: searches Prowlarr, downloads via qBittorrent, hardlinks ROMs into `games/roms` for RomM |
| RomM (+ MariaDB) | 8090 | Retro game library, play in the browser (`plex-media/games`) |
| Media Index | 8686 | Poster wall of every title, active or cold, with keep/shrink/delete and cold-storage moves; Storage tab (disk use, cold shelf, suggestions); posters from Radarr/Sonarr, Plex, cover images on disk or TMDB, cached in `~/.local/share/media-index/posters` so cold titles keep theirs (`media-index/`) |

**The disk.** `plex-media` is a Seagate ST8000DM004, a shingled (SMR) drive that slows badly after ~30 GB of writes in
one go, so both qBittorrents (`:8080` and the private one) use the speed scheduler: full speed 2–6 am, 300 KiB/s the
rest of the day; `media-index/downloads_cap.py` (every 30 min) also sets both queue limits to match: 10 downloads /
5 uploads / 15 active while the scheduler has the alternative limits off, 3 / 2 / 5 otherwise (`LIMITS`; it reads
the private instance at `gluetun:8081`, whitelisted via media-index's fixed 172.30.0.249) (Joe, 2026-11-10). Seeding is stopped for now;
start completed torrents again from the WebUI when wanted. Exception for something wanted now: click the speedometer
icon in qBittorrent's footer (alternative limits off until the schedule flips it back) or ask. Bulk jobs that write a
lot (webtoon re-cuts, re-encodes) also go in that window. If the whole volume "hangs" (every `ls` and open blocks,
Plex can't serve files, yet `stat`/`df` work and `iostat -d disk4` shows the disk idle), it is not the drive: a macOS
"… would like to access files on a removable volume" consent dialog is waiting on the mini's screen and every open()
queues behind tccd until it is clicked (proof: `sample <user tccd pid> 1 | grep CFUserNotificationReceiveResponse`).
Answer it over Screen Sharing; don't kill tccd.

**Plex** itself is the Mac app (`/Applications/Plex Media Server.app`, data in
`~/Library/Application Support/Plex Media Server/`). The launchd agent `local.plex.autostart` (hand-written,
untracked, saved in the nightly settings archive) opens it at login once `/Volumes/plex-media/movies` exists, so it
never starts against a missing disk. Containers reach it at `HOST_ADDR:32400`. Its libraries and playlists are
listed in `app-config/plex/`. The libraries stay plain: no Kometa, overlays or auto-collections (tried and reverted
2026-10-22).

**Private stack.** A second compose project, `private` (`~/.config/private-stack/`, own README), runs beside this
one and is kept out of the dashboard, Media Index and the backups here. It leans on this stack in three ways: its
Whisparr, Prowlarr, FlareSolverr and qBittorrent (`:8081`) run inside this stack's `gluetun` tunnel, its other
containers sit on this stack's network at fixed addresses (172.30.0.250–252), and its media is in
`plex-media/.private/`. So whenever `gluetun` is recreated here (an image update, a changed setting), rejoin them:
`docker-compose -f ~/.config/private-stack/compose.yml up -d --force-recreate whisparr prowlarr flaresolverr qbittorrent`.

A request flows Seerr → Radarr/Sonarr → Prowlarr → qBittorrent → hardlinked into `movies` / `tv` → Plex. Music is the same
without Seerr: add artists in Lidarr (or pick them from Sonobarr's suggestions), which files albums into `music/` (Plex
Music library, Plexamp app). Lidarr only fetches whole albums, so for one song paste its Spotify link into spotDL instead;
if spotDL fails with YouTube 403/429 errors, `docker-compose build --pull spotdl && docker-compose up -d spotdl`.
Lidarr unmonitors tracks you delete, so trimming an album in Media Index doesn't re-download it.

## Manga

Suwayomi (`:4567`) is Sonarr for manga, but it reads chapters from manga sites through Tachiyomi source extensions
instead of torrents, so nothing goes through Prowlarr or the VPN. The Keiyoushi extension store
(`https://github.com/keiyoushi/extensions/raw/repo/index.pb`, in Suwayomi's `server.conf`) and the MangaDex and
Weeb Central extensions are installed (2026-11-09); more sources go in under **Extensions** (MangaDex lists one source
per language — use *MangaDex (EN)*). `server.kcefEnabled = false` in `server.conf`: the embedded Chromium pushed the
4 GB OrbStack VM out of memory and the container crash-looped (`Killed` in its log) until it was turned off. **Settings → Downloads** shows *Download as CBZ* on (set by `compose.yml`) and *Automatically
download new chapters* on (set once with the call below). To follow a series: **Browse → Sources → MangaDex (EN)**,
search it, open it, **Add to library**; the whole backlog downloads with the ⤓ button on the series page, and every
new chapter after that is fetched on the 12-hourly library update. Chapters land in
`manga/mangas/<Source>/<Series>/<Chapter>.cbz` (Suwayomi fixes that layout). MangaDex drops titles that have an
English publisher (Solo Leveling, for one); those come from Weeb Central instead.

Kavita (`:5003`) is the reader (set up 2026-11-09, admin `jyesselm`, API key `KAVITA_API_KEY` in `.env`): one library
*Manga* over `/manga/paged/Weeb Central (EN)` and `/manga/mangas/Weeb Central (EN)` (add `/manga/mangas/MangaDex (EN)`
when something downloads from there), folder watching on so new Suwayomi chapters appear without a scan, metadata
from Mangabaka, exclude pattern `**/mangas/*/Solo Leveling/**` so a re-cut series (below) is read from `paged/` and
not twice. The default reading profile is paged left-to-right, automatic scaling, fit-split, tap or swipe to turn,
menu auto-closes, black background, webtoon auto-detection off. Everything reads left to right like a western book, Japanese manga
included (Joe, 2026-11-10; a right-to-left profile for them was tried and removed).
**iPad.** Kavita's automatic scaling fits the page to the *width* whenever the window is taller than wide, which
cuts off the bottom of a manga page on an iPad held upright (the screen is squarer than the page). So the iPad
(client device 4, "Safari on iOS", in `GET /api/device/client/devices`) has its own profile, *iPad (fit whole
page)*, with *fit to height*, bound to both libraries. How binding works (found by testing 0.9.1.4): a profile's
device list only narrows its library or series binding, a device-only profile does nothing; and when a series has
two profiles, the one with the lower id wins. The reader sends the browser's id as the `X-Device-Id` header; check
what a device gets with `GET /api/reading-profile/<libraryId>/<seriesId>?skipImplicit=false` and that header set to
the device's `uiFingerprint`. Each browser is its own device: a new iPad, another browser, or the Home Screen app
registers separately and must be added to the iPad profile (`POST /api/reading-profile/set-devices?profileId=6`
with the full id list). Phones keep automatic scaling (fit to width is right for them). On the phone or iPad, open
`http://plex-server.tail2813f4.ts.net:5003` in Safari and Share → *Add to Home Screen* for a full-screen app. If a series opens in the wrong mode, Kavita saved a
per-series *implicit* profile from an earlier read; clear it with `DELETE /api/reading-profile/series/<seriesId>`
(or the reader's settings → reset). `POST /api/library/update` needs `fileGroupTypes` as well as `libraryFileTypes`
or it 400s. OPDS is on: Kavita → user menu → *3rd Party Clients* has the OPDS link for Panels/Paperback (progress
syncs with the web reader). Suwayomi's own page reads too, without progress sync.

Webtoons one scene at a time: each Suwayomi file is one ~720×4000 strip, which paged readers show as a thin column
and Kavita's scroll mode shows as an endless strip; Joe wants one scene per page. `manga/webtoon_cut.py` stitches a
chapter and cuts it only at gutters (solid gaps ≥24 px), grouping neighbouring scenes while they fit a 720×1560 page
(iPhone shape) and giving a taller scene its own tall page, so no panel or bubble is ever sliced (a first version
that forced a cut every 1560 px did slice them; those copies are in `_trash/manga-paged-fixedcut`). Pages keep their
natural height, no padding: padding showed as a white block on the reader's black background. Copies live in
`manga/paged/<Source>/<Series>/` with the originals' names; Kavita reads those and excludes the original folder.
Solo Leveling is cut (201 chapters, chapter 50 with the padding-free script, the rest with the padded one; left as
is), and so is Solo Leveling: Ragnarok (10 chapters, 2026-11-10, page height 2037 because its strips are 940 wide:
scale 1560 by width/720). New chapters need the script run on the new files, and a newly cut series needs its own
exclude pattern (`**/mangas/*/<Series>/**`) in the Manga library. Better still for a page reader: real print editions.
`manga/volumes/<Series>/` holds digital volumes (`Solo Leveling v01-14 (Digital) (1r0n)`, the Yen Press re-layout of
the webtoon into 900×1291 pages; `Chainsaw Man v01-05 (Digital) (1r0n)` as a reader test), hardlinked from
`downloads/manga/`; Kavita reads that folder as its own **Volumes** library so they don't merge with the webtoon
series of the same name. To add volumes: pick the `(Digital) (1r0n)` release in Prowlarr, add its magnet to
qBittorrent with only the wanted files (`torrents/filePrio` priority 0 for the rest; force-start, the queue is
usually full of stalled torrents), hardlink the CBZs in, then `POST /api/library/scan?libraryId=2&force=true`.
For Panels, copy
`manga/paged/Weeb Central (EN)/Solo Leveling` to the phone over File Sharing and import it.

Turn auto-download on once (idempotent; the setting lives in Suwayomi's database):
```sh
curl -s http://plex-server.tail2813f4.ts.net:4567/api/graphql -H 'content-type: application/json' \
  -d '{"query":"mutation { setSettings(input:{settings:{autoDownloadNewChapters:true, autoDownloadNewChaptersLimit:0}}) { settings { autoDownloadNewChapters } } }"}'
```

## Anime and subtitles

Anime lives in `anime/` (its own Sonarr root folder and Plex library; Seerr sends anime requests there). The rule
(Joe, 2026-11-10): Japanese audio with English subtitles.

- **Fetching.** Anime series use Sonarr's quality profile **Anime 1080p** (HD-1080p plus four custom formats scored
  −10000, so a matching release is rejected): *no Japanese audio* (dub-only), *other-language audio* (French,
  German, Spanish, Italian, Portuguese, Russian), *other-language release tag* (`MULTi`, `VOSTFR`, `FRENCH`,
  `GERMAN`… in the name, which Sonarr doesn't read as a language) and *raw (no subtitles)* (`-Raws` groups except
  Erai-raws, Moozzi2, ReinForce, VCB-Studio). Dual audio (English + Japanese) is fine. Seerr's anime profile points
  at it; a series added by hand in Sonarr needs the profile picked. Test a release name with
  `GET /api/v3/parse?title=<name>` (shows the formats it matches). Within one custom format, conditions of the
  same type are OR and different types are AND, which is why language and name tags are separate formats.
- **Subtitles.** Sonarr and Radarr auto-tag anything whose original language isn't English `foreign`; Bazarr's
  profile *English (foreign titles)* is tied to that tag (`serie_tag_enabled` / `movie_tag_enabled`, the tag-based profile switches under Settings → Languages; they
  were off until 2026-11-10, so newer titles had no profile). Untagged embedded
  subtitle tracks count as English. Bazarr's providers are weak for anime: `animetosho_xyz` is enabled but does
  nothing until an AniDB API client name and version are entered in Bazarr's settings (register one in your
  anidb.net account, under API clients), and OpenSubtitles.com needs an account.
- **State on 2026-11-10** (445 files probed with `ffprobe`): every Japanese-audio file has English subtitles
  inside it except Frieren (28 episodes, French release), Parasyte (24, French release), Kaiju No. 8 (12, no
  subtitles at all) and one Madoka Magica extra. Bazarr lists them under Wanted and retries every 6 h. `anime/FBI`
  is a Spanish-audio live-action show filed in the wrong folder.

## Movie recommendations (Trakt)

Rate movies in Plex (stars). PlexTraktSync (container `plextraktsync`, every 6 h) copies ratings and watched
status both ways between Plex and Trakt; Trakt's own Plex Sync handles library and history but drops ratings in both
directions (October 2026). Trakt turns ratings into picks at trakt.tv/movies/recommended. Add the ones you want to
your Trakt watchlist; Radarr's import list "Trakt Watchlist" (Trakt User → Watchlist, HD-1080p, `movies/`) adds
and searches them on its next list sync. PlexTraktSync also mirrors the Plex watchlist to Trakt, so a movie
watchlisted in Plex is downloaded too. Clean Library Level stays Disabled, so watching a movie (Trakt then drops it
from the watchlist) never deletes it.

**Quality: 1080p unless asked.** Seerr, the Trakt list and Sonarr all use the HD-1080p profile (anime: Anime 1080p, the same qualities), which allows only
1080p HDTV/WEB/Blu-ray encodes (no remuxes, no 4K). For a 4K copy, request it in Seerr and open **Advanced** →
Quality Profile → **Ultra-HD** (or switch the movie's profile in Radarr and search). Ultra-HD takes Bluray-2160p
and never upgrades past it.

Shows and movies you'll stream on another service go on a Trakt list instead (trakt.tv → profile → Lists):
**non-plex-watchlist** for yourself, **non-plex-watchlist-together** for things to watch together. Nothing
imports them, so nothing downloads. The dashboard's Watch tab (`:3000/#watch`) shows either list (a switch at the top)
with each title labelled In Plex (checked against the library by TMDB, IMDb or TVDB id) and the US services that
stream it (TMDB data via Seerr): your subscriptions are `MINE` in `dashboard/server.py`. Clicking a poster opens its
details. On the Onn, the Watch TV app (`tv-app/`; `./gradlew assembleDebug`, then `adb install` the debug APK; a new Mac
needs `openjdk@21` and `android-commandlinetools` from the Brewfile, `sdkmanager "platforms;android-36" "build-tools;36.0.0"`
and `tv-app/local.properties` with `sdk.dir=/opt/homebrew/share/android-commandlinetools`) loads
`?tv=1`, the 10-foot layout: OK opens the details, Watch opens Plex directly or Google TV search for the title (one
press to the service), and Trailer plays in YouTube. `?tv=1` works in any browser for testing.

Sign-ins live in `$DATA_ROOT/plextraktsync/` (`.env`, `.pytrakt.json`, `servers.yml`) and Radarr's database, so a
moved or restored stack keeps them. Only a fresh install needs them again:
- PlexTraktSync: a Trakt API app (app.trakt.tv → Your API Apps, Development, redirect `http://localhost`), then
  `docker-compose run --rm --no-deps plextraktsync login` and answer the prompts (Plex sign-in, server
  `plex-server`, the app's Client ID, then the trakt.tv/activate code). Run it over SSH from the computer showing the
  Client ID; `trakt-login` redoes only the Trakt half.
- Radarr: open the list in Radarr → Settings → Import Lists and press Start OAuth, in Chrome or Safari (the sign-in
  popup hands its token back to the form, which Claude's browser pane can't do).

## Files

- Everything in this folder except `.env` is tracked in dotfiles (yadm) and holds no secrets: `compose.yml`,
  `gluetun-auth.toml` (lets the dashboard read the VPN's public IP), own code in `dashboard/`, `media-index/`,
  `manga/`, `menubar/`, `tv-app/`, image tweaks in `spotdl/` and `plextraktsync/`, the scripts `backup.sh` and
  `export-config.sh`, and the travel kit (`travel-onn.md`, `onn-setup.sh`). `CLAUDE.md` is the short rule list for agents.
- `.env`: untracked, this machine's paths and keys. Template: `env.example`.
- `$DATA_ROOT/<app>/config` (and `$DATA_ROOT/uptime-kuma`): each app's settings and database. Not tracked; this is
  what you copy to move the stack.
- `app-config/`: tracked, secret-free JSON of each app's settings (Plex libraries and playlists, custom formats, quality profiles, naming, root
  folders, download clients, Prowlarr apps, Seerr settings). Refresh with `./export-config.sh` after changing
  settings, then commit. It's the reference for rebuilding an app by hand if `$DATA_ROOT` is lost; API keys,
  passwords and indexers are left out, so re-enter those.
- The media disk is always mounted at `/Volumes/plex-media` inside containers, whatever its host path, so the
  paths stored in Radarr, Sonarr, qBittorrent and Plex stay valid on any machine. Downloads (`downloads/`) and
  the libraries share that one disk so imports are instant hardlinks. Top-level folders are lowercase, one per
  type (`movies tv anime manga music audiobooks podcasts youtube games other downloads`); folders starting with `_`
  (`_trash`, `_backups`, `_meta`) are bookkeeping, not media, and Media Index skips them.

## Menu-bar icon (Mac)

`menubar/` is a 60-line Swift app that puts a ▶ icon in the menu bar: click opens the dashboard, right-click lists
Plex, Seerr, Audiobookshelf, Media Index and qBittorrent. `menubar/install.sh` compiles it into
`~/Applications/Media Menu.app` and loads `~/Library/LaunchAgents/com.yesselman.media-menu.plist` (tracked; declared
in `setup/declared/agents.txt` for the `server` class). Edit the `pages` list in `MediaMenu.swift` and re-run the script.

## Everyday commands

```sh
cd ~/.config/media-stack
docker-compose up -d                 # start / apply changes
docker-compose pull && docker-compose up -d   # update all images
docker-compose logs -f gluetun       # watch one service
docker-compose ps                    # health at a glance (or the dashboard)
cd media-index && uv run --with pytest pytest -q   # tests for the own code
```

An update that recreates `gluetun` needs the private stack rejoined (see *Private stack* above). `dashboard`,
`media-index` and `spotdl` are built here: after editing their code, `docker-compose up -d --build <service>`.

On the Mac, `docker-compose` comes from OrbStack (on PATH via `.zsh/tools.zsh`); OrbStack starts at login and needs
Removable Volumes access to reach the disk.

## Scheduled jobs (launchd)

All are user agents in `~/Library/LaunchAgents/`, written by the install command shown (re-run it to change one).
macOS doesn't let a launchd job read or write `plex-media`, so the ones that touch the disk do it through the
`media-index` container, which must be up.

| Agent | When | Runs | Install | Log |
|---|---|---|---|---|
| `local.plex.autostart` | login | opens Plex once the disk is mounted | by hand | — |
| `com.yesselman.media-menu` | login, kept alive | menu-bar icon | `menubar/install.sh` | — |
| `com.yesselman.dashboard-host` | every minute | `dashboard/host-stats.py` | `host-stats.py install` | — |
| `com.yesselman.cold-moves` | every 10 min and on drive plug-in | `drives.py watch` | `drives.py install` | `cold-moves.log` |
| `com.yesselman.downloads-cap` | every 30 min | `downloads_cap.py run` (in the container) | `downloads_cap.py install` | `downloads-cap.log` |
| `com.yesselman.media-shrink` | 01:00, no new file after 08:00 | `shrink.py run --until 8` | `shrink.py install` | `encode.log` |
| `com.yesselman.music-upgrade` | 03:00 | `music_upgrade.py run` | `music_upgrade.py install` | `music-upgrade.log` |
| `com.yesselman.media-backup` | 04:00 | `backup.sh` (settings archive) | `backup.sh install` | `backup.log` |
| `com.yesselman.media-backup-cloud` | Saturday 01:00 | `backup.sh cloud` (media to Google Drive) | `backup.sh install` | `cloud.log` |
| `com.yesselman.media-backup-remind` | Sunday 10:00 | `backup.sh remind` | `backup.sh install` | `backup.log` |

Python scripts are under `media-index/` unless a folder is given; their logs are in `~/.local/share/media-index/`,
the backup logs in `~/backups/media-stack/`. Inside the stack, PlexTraktSync syncs every 6 h, Suwayomi checks for
chapters every 12 h, Cleanuparr's queue cleaner runs every 30 min and Media Index re-indexes the disk daily.

## Troubleshooting

- **Every `ls`/open on `plex-media` hangs, disk idle:** an unanswered macOS consent dialog; see *The disk*.
- **Plex apps stop listing the server though it runs:** plex.tv's record went stale (seen 2026-10-22). Check
  `curl -H "X-Plex-Token: $HOMEPAGE_VAR_PLEX_TOKEN" -H "X-Plex-Client-Identifier: check" -H "Accept: application/json" https://plex.tv/api/v2/resources`:
  the Plex Media Server entry should have `provides: "server"`, not `"sync"`. Re-register without a restart:
  `PUT http://127.0.0.1:32400/:/prefs?PublishServerOnPlexOnlineKey=0` (with the token), wait a few seconds, then `=1`.
- **A container shows old files after its host folder was renamed:** OrbStack keeps serving the renamed folder at
  the old path through container recreates and `orb restart docker`. Only `orb stop && orb start` clears it (all
  containers down ~1 min; Plex is unaffected). To reset an app's data, move the files out and keep the folder.
- **spotDL fails with YouTube 403/429:** rebuild it, `docker-compose build --pull spotdl && docker-compose up -d spotdl`.
- **Private stack's downloads or Whisparr unreachable after an update here:** `gluetun` was recreated; see *Private stack*.
- **Nightly shrink logs "ffprobe can't read":** Homebrew's `ffmpeg` was upgraded and lost its Removable Volumes
  permission; see *Media Index*.

## NordVPN key (once)

gluetun needs your NordVPN WireGuard private key in `.env` as `NORDVPN_WIREGUARD_KEY`. Get an access token at
Nord Account → NordVPN → Set up NordVPN manually, then turn it into the key as described at
https://github.com/qdm12/gluetun-wiki/blob/main/setup/providers/nordvpn.md. Then `docker-compose up -d`
and check `docker-compose logs gluetun` shows the public IP of a Nord server.

## Media Index (cleanup)

`media-index/` indexes the disk daily (sizes, ffprobe video info, watch history from Plex's dated database backups) and
serves a review page on 8686: a poster wall (like Plex) where every title is either **☀ active** on `plex-media` or
**❄ cold** on a cold drive (the drive is a chip on the card); **🧳 travel** marks what goes on the travel stick: anything in a Plex
collection called Travel, or held by the drive `plex-travel` once the stick is named that and catalogued. Posters come from
Radarr/Sonarr, then Plex, then a cover image in the title's own folder (audiobooks, podcasts, album art), then TMDB
(`TMDB_API_KEY`); a title with none shows a tinted tile with its name. A title's sheet has two switches under "Where it
lives", ❄ Cold storage and 🧳 Travel stick (the travel one adds or removes it in the Plex Travel collection); the hover
buttons and the Select bar ("Mark as" / "Undo") do the same for many at once, and `t` toggles travel from the keyboard. Hover a poster for ❄ Cold / Keep (☀ Bring back on a cold one),
click it for the title sheet (size, plays, where every copy lives, files, Keep / Shrink / Delete, Find smaller 1080p),
or press **Select** to mark many at once. The **Storage** tab shows the disk by folder, the cold shelf (both drives as one
pool, with where the next move goes), queued moves, and shelves of suggestions: never watched and big, not watched in
3+ years, 4K you could shrink instead, on the shelf to bring back. Mark each title Keep, Shrink (worth re-encoding to HEVC) or Delete. "Move to trash"
renames Delete items into `plex-media/_trash/` and unmonitors them in Radarr/Sonarr; restore from the page. Nothing is
permanently deleted until you empty `_trash` yourself, e.g. `rm -rf /Volumes/plex-media/_trash/*`. Music is reviewed per song:
pick ♪ Music in the type chips, press `p` (or ▶) to listen, and `1`/`3` keep or delete; while a song plays, moving or deciding plays
the next one. Plex's automatic scan drops trashed songs from the library. Items hardlinked with
a torrent in `downloads/` free space only once the torrent is removed in qBittorrent too. Its database is
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

**Download folder cap**: `media-index/downloads_cap.py` (launchd, every 30 min, run inside the media-index container since launchd's own
Python can't touch the disk) keeps `downloads/radarr` under
150 GB and `downloads/sonarr` under 100 GB (`CAP_GB`). Finished torrents are hardlinked into the library and cost
nothing; what grows the folders is downloads in progress (allocated in full up front) and leftovers, folders no
torrent owns after Radarr/Sonarr dropped a stuck grab. Leftovers untouched for a day go to `_trash/downloads/`
(empty `_trash` by hand). When the
folder's own bytes plus what the active torrents still have to fetch would pass the cap, the torrents with the
most left are stopped and tagged `capped` in qBittorrent, and started again once there is room. Log:
`~/.local/share/media-index/downloads-cap.log`; `python3 media-index/downloads_cap.py run --dry-run` shows a check.

**Music upgrades** to 320 kbps go through Lidarr, run by `media-index/music_upgrade.py` (daily at 03:00). Lidarr only
grabs whole albums, so the script monitors up to 10 albums holding your lowest-bitrate songs under an "Upgrade to 320"
profile and searches them again each day. Once every song you had is at 320, it deletes the album's other tracks and
unmonitors it. Albums with no 320 release after 14 days are dropped. Replaced and removed files go to
`plex-media/_trash/lidarr` (Lidarr's recycle bin, never emptied automatically). Songs Lidarr doesn't know (most
YouTube rips) are skipped; re-get those with spotDL.

```sh
python3 media-index/music_upgrade.py status
python3 media-index/music_upgrade.py run --dry-run          # what would start or finish
```

**Drive manifests** record what is on each media drive, so you can see which drive holds a title while it's
unplugged. `media-index/drives.py catalog` writes one row per file (path, size, mtime) to
`~/.local/share/media-index/drives/<drive>.tsv` and to `.media-manifest.tsv` on the drive itself. Re-run it
after changing a drive. A file counts as copied when another drive has the same name and size (or the same size for
files over 50 MB, which catches renames). `catalog` also records the drive's size and free space
(`<drive>.usage.json`), which is how the page picks the roomiest cold drive. The Storage tab shows the same manifests,
and a title's sheet lists every drive holding a copy.

```sh
python3 media-index/drives.py catalog /Volumes/plex-backup-1      # after plugging a drive in
python3 media-index/drives.py where supernatural               # which drives hold it
python3 media-index/drives.py missing plex-backup-1 plex-media  # titles not yet copied
python3 media-index/drives.py cold plex-cold-1 "tv/Fargo" "movies/First Man (2018)"   # move titles to cold storage
python3 media-index/drives.py cold plex-cold-1 --csv picks.csv --dry-run             # from a move_candidates CSV
```

`cold` copies each title to the same folder on the cold drive, checks file count and bytes, removes it from
Radarr/Sonarr (files kept, import-list exclusion so it isn't grabbed again), moves the original to
`plex-media/_trash`, re-catalogs the drive and has Plex refresh the library. The cold drive then holds the only
copy once the regular backup drives are next synced.

**Click instead.** In Media Index, ❄ on a `plex-media` title marks it for the cold drive with the most room (the
sheet lets you pick one), and ☀ Bring back marks a cold title to copy home. Keep titles, i.e. the repeat list and
watchlist, are refused; the marks show on the cards and in the Storage tab's queue with their progress. The launchd agent
`com.yesselman.cold-moves` (`python3 media-index/drives.py install`) runs `drives.py watch` every 10 minutes and whenever a drive is
plugged in: for each plugged-in cold drive with marks it runs `drives.py queue <drive>` in a one-off media-index
container (launchd can't write the media disk), which does the moves the same way as `cold`. Bringing one back copies
it to `plex-media`, lifts the exclusion and re-adds it to Radarr/Sonarr (1080p profile, monitored, no search); the
cold copy stays as a backup. Marks waiting for an unplugged drive get one reminder a day. Log:
`~/.local/share/media-index/cold-moves.log`.

## Backups

`backup.sh` (launchd, nightly at 04:00) archives every app's settings and databases, Plex's library database and
`.env` into `settings-YYYY-MM-DD.tar.gz` (~400 MB) in `~/backups/media-stack/` and `plex-media/_backups/settings/`,
keeping 7 in each, and uploads an encrypted copy to Google Drive (`media-stack-backups/`, newest 4) through the
rclone remote `gcrypt`. The apps covered are `APPS` in `backup.sh`; add a new service there when it has settings
worth keeping. Cover art and Plex artwork are left out; they re-download. To restore an app, stop it and
copy its folder from the archive back to `$DATA_ROOT` (Plex: its two `.db` files into `Plug-in Support/Databases/`;
Suwayomi: its library is `suwayomi/library.tachibk`, restored in its web UI under Settings → Backup).
Database copies are made from a container inside OrbStack's VM: never open a running app's SQLite database from
macOS (with `sqlite3` or a GUI), which breaks its locking and can corrupt it.

The Drive copy can only be decrypted with `gcrypt`'s passwords, so keep the output of `rclone config show gcrypt`
in a password manager. On a new machine: `rclone config create gdrive drive scope=drive.file`, paste that
`[gcrypt]` block into `~/.config/rclone/rclone.conf`, then `rclone copy gcrypt:settings-<date>.tar.gz .`. If
uploads fail (a notification says so), run `rclone config reconnect gdrive:`.

The media that can't be re-downloaded (`CLOUD_FOLDERS` in `backup.sh`: `other anime youtube music podcasts
audiobooks`) is also mirrored to Google Drive every Saturday at 01:00 by `backup.sh cloud`, encrypted with file
names hidden, through the rclone remote `gmedia` (`gmedia:current`). A replaced or deleted file moves to
`gmedia:deleted/<date>/` and is dropped after 30 days. The upload runs in a container named `media-cloud-upload`
(a second run won't start while one is going), is held to 5 MB/s between 08:00 and 23:00, and logs to
`~/backups/media-stack/cloud.log`.

Everything except `downloads/` and `games/` is mirrored on three backup drives (`BACKUPS` in
`media-index/drives.py`), and each also gets a copy of the settings archives:

| Drive | Holds |
|---|---|
| `plex-movie-backups` (3 TB) | `movies` |
| `plex-tv-backups` (3 TB) | `tv` shows starting 0–9 or A–S, `audiobooks` |
| `plex-misc-backups` (2 TB) | `tv` shows starting T–Z, `anime`, `other`, `youtube`, `music`, `podcasts`; also `MaP2D_Data` (lab data; the other copy is on `plex-cold-2`) |
| `plex-cold-1`, `plex-cold-2` (3 TB each; were `plex-offsite-1/-2`) | `other`, `anime`, `youtube`, `music`, `podcasts`, `audiobooks` (what can't be re-downloaded; also on Google Drive), plus cold storage: titles moved off `plex-media` with `drives.py cold` (not in Plex, Radarr or Sonarr; Media Index's Storage tab or `drives.py where` says which drive holds one). `plex-cold-2` also keeps a copy of `MaP2D_Data` (lab data; not on `plex-media`, so sync leaves it alone) and `_trash/Movies` (old pre-Radarr library, 1.3 TB) |

Every Sunday at 10:00 `backup.sh remind` re-catalogs `plex-media` and shows a notification with how much each
drive is behind. Plug the drive in and run `sync`; it mirrors deletions too and re-catalogs the drive:

```sh
python3 media-index/drives.py sync plex-tv-backups   # or plex-movie-backups / plex-misc-backups / plex-cold-1 / -2
python3 media-index/drives.py status                 # what the reminder checks
./backup.sh install                                  # (re)install both launchd jobs
```

`Plex Disk 1` and `Plex Disk 3` hold older partial copies and are only catalogued.

## Moving to Linux

1. **Disk format.** `plex-media` is journaled HFS+. Linux mounts it read-only unless journaling is turned off, so
   plan to move the data to an ext4 disk (copy 5.8 TB off, reformat, copy back, or buy a new disk and copy across).
   Mount it somewhere fixed, e.g. `/mnt/plex`, via `/etc/fstab`.
2. **Install** Docker Engine with the compose plugin, clone the dotfiles (`yadm` linux class), and copy
   `env.example` to `.env`.
3. **Stop the Mac stack** (`docker-compose down`, quit Plex), then copy the app data across:
   `rsync -a ~/.local/share/{radarr,sonarr,bazarr,lidarr,sonobarr,spotdl,prowlarr,seerr,plextraktsync,qbittorrent,cleanuparr,uptime-kuma,audiobookshelf,audiobookrequest,suwayomi,kavita,romm,gamarr,media-index,dashboard} newhost:~/.local/share/`.
4. **Edit `.env`**: `MEDIA_ROOT=/mnt/plex`, `DATA_ROOT=/home/<you>/.local/share`, `PUID`/`PGID` from `id`
   (usually 1000), keys unchanged.
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
       - ${MEDIA_ROOT}:/Volumes/plex-media
   ```
   Move Plex's data per https://support.plex.tv/articles/201370363 : copy the Mac's
   `~/Library/Application Support/Plex Media Server/` to `$DATA_ROOT/plex/config/Library/Application Support/Plex Media Server/`.
   Library folders keep working because the disk is mounted at the same path.
6. **Repoint Plex** in the other apps: set `HOST_ADDR` to the Linux host's LAN IP (Plex uses host networking),
   and in Seerr → Settings → Plex use that IP too.
7. `docker-compose up -d`, open the dashboard, and check every tile is green. Request one movie to test the chain.

## Games (RomM)

RomM serves the game library at port 8090 and plays most pre-PS2 systems in the browser (EmulatorJS), with saves per
account. Put ROMs of games you own in `plex-media/games/roms/<platform>/` (slugs from docs.romm.app → Supported
Platforms; `nes snes n64 genesis gb gbc gba ps dos` exist) and firmware in `games/bios/<platform>/`, then
Library → Scan in the web UI. The first visit creates the admin account; add other users under Administration.
Covers come from keyless sources (Hasheous, LaunchBox, Playmatch); for better matches set the IGDB and ScreenScraper
values in `.env` and `docker-compose up -d romm`. Its data and MariaDB database are in `$DATA_ROOT/romm/`. On a TV,
RetroArch on the Onn plays the same files with a controller.

Gamarr (port 5001) is the *arr for games: search a title, pick a result, and it downloads through qBittorrent
(category `games`) and hardlinks ROMs into `games/roms/<platform>/` (PC games into `games/pc/`). It is a small,
young project; check what a release contains before opening it, and never run `.exe` files from a ROM download.

## FlareSolverr

Prowlarr reaches FlareSolverr at `http://flaresolverr:8191` over the Compose network.
The API is internal only; no host port is published. In Prowlarr → Settings → Indexers →
Indexer Proxies, the FlareSolverr proxy uses the `flaresolverr` tag. The existing indexers carry this tag so the helper is available when needed. Assign the same tag
to new indexers that need it. Prowlarr uses the proxy when an applicable indexer encounters
Cloudflare protection. No persistent data directory is needed.
