# Media stack: notes for agents

`README.md` is the documentation: services and ports, how each piece works, scheduled jobs, backups, troubleshooting.
Read the section you need before changing anything, and update it in the same change. This file only holds the
rules that are easy to break.

## Where things are

- This folder (`~/.config/media-stack`) is tracked in the yadm dotfiles repo, except `.env` (keys and paths).
  Commit with `yadm`, not `git`.
- App settings and databases: `~/.local/share/<app>/` (`DATA_ROOT`). Media: `/Volumes/plex-media` (`MEDIA_ROOT`).
- Plex runs natively on the Mac (port 32400), everything else in OrbStack from `compose.yml` (project `media-stack`).
- A second compose project, `private` (`~/.config/private-stack/`), shares this stack's gluetun tunnel, network and
  disk. It has its own README; leave it alone unless asked, and see README → *Private stack* before touching gluetun.
- Host name on the tailnet: `plex-server.tail2813f4.ts.net`. API keys: `.env` (`HOMEPAGE_VAR_*_KEY`, Plex token
  `HOMEPAGE_VAR_PLEX_TOKEN`). Never print their values.

## Rules

1. **Never open a running app's SQLite database from macOS** (`sqlite3`, Python, a GUI): it breaks locking across
   the OrbStack boundary and can corrupt it. Use the app's API or `docker exec`.
2. **Nothing is deleted, only moved to `plex-media/_trash/`.** Joe empties `_trash` himself. Follow that pattern in
   new code and by hand.
3. **launchd jobs can't read or write `plex-media`** (macOS privacy). Anything scheduled that touches the disk runs
   through `docker exec media-index …` or a one-off container; copy that pattern (README → *Scheduled jobs*).
4. **The disk is slow for big writes** (SMR). Bulk writes go in the 2–6 am window; don't lift qBittorrent's limits
   unasked (README → *The disk*).
5. **Recreating `gluetun` cuts off the private stack** until it is recreated too (README → *Private stack*).
   `docker-compose pull` / `up -d` on everything can do this.
6. **Privacy and security prompts are Joe's call**: don't kill `tccd`, run `tccutil`, or change permissions.
7. **Keep titles stay on `plex-media`**: anything marked Keep in Media Index (repeat list, watchlist) is never
   cold-moved or deleted. Shrinking is fine.
8. **No Kometa, overlays or auto-collections in Plex.** Joe tried and reverted them; the libraries stay plain.
9. After changing an app's settings in its web UI, run `./export-config.sh` so `app-config/` matches.
10. Host scripts run by launchd use `/usr/bin/python3` (3.9) and the standard library only; keep them compatible.

## Checking your work

```sh
docker-compose ps                                        # or the dashboard, :3000
cd media-index && uv run --with pytest pytest -q         # 17 tests
uvx ruff check media-index dashboard                     # config: ruff.toml in each; 23 findings already there on 2026-11-10
```
