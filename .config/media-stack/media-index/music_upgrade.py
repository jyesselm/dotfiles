"""Upgrade low-bitrate songs to 320 kbps through Lidarr, keeping only the songs you already had. Runs on the macOS host.

Lidarr only grabs whole albums, so each run: (1) finishes albums started earlier: once every song you had is at
320 kbps, the album's other tracks are deleted and the album is unmonitored again; (2) starts a few more: picks the
albums holding your lowest-bitrate songs, gives the artist the "Upgrade to 320" profile, monitors the album and
searches.
Lidarr replaces the old files itself. Everything removed goes to Lidarr's recycle bin, Plex_Disk_4/_trash/lidarr, which
is never emptied automatically. Albums with no 320 release after GIVE_UP_DAYS are unmonitored and not tried again.
Songs Lidarr doesn't know (most YouTube rips) can't be upgraded this way.

    python3 music_upgrade.py run [--albums N] [--dry-run]
    python3 music_upgrade.py status
    python3 music_upgrade.py install    # launchd agent: daily at 03:00

Written for /usr/bin/python3 (3.9), which launchd runs.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import plistlib
import subprocess
import sys
import time
from functools import cache
from pathlib import Path

import arr
from shrink import STATE_DIR, read_env

API = "http://localhost:8687/api/v1"
STATE = STATE_DIR / "music-upgrade.json"  # {"pending": {albumId: {...}}, "done": [albumId], "gave_up": [albumId]}
LOG = STATE_DIR / "music-upgrade.log"
LABEL = "com.yesselman.music-upgrade"
RUN_HOUR = 3

PROFILE_NAME = "Upgrade to 320"
TARGET_GROUP = "High Quality Lossy"  # Lidarr's group holding MP3-320, AAC-320 and MP3 V0
LOW_GROUPS = ("Trash Quality Lossy", "Poor Quality Lossy", "Low Quality Lossy")  # up to 224 kbps, worst first
RECYCLE_BIN = "/Volumes/Plex_Disk_4/_trash/lidarr"
ALBUMS_PER_RUN = 10
GIVE_UP_DAYS = 14

log = logging.getLogger("music-upgrade")


def lidarr(path: str, body: object = None, method: str | None = None) -> object:
    """Call the Lidarr API on the host port."""
    return arr.request(API + path, _key(), body, method)


@cache
def _key() -> str:
    return read_env()["HOMEPAGE_VAR_LIDARR_KEY"]


def quality_groups() -> dict[int, str]:
    """Lidarr quality id -> group name, e.g. MP3-128's id -> "Poor Quality Lossy"."""
    schema = lidarr("/qualityprofile/schema")
    return {q["quality"]["id"]: group["name"] for group in schema["items"] for q in group.get("items", [])}


def ensure_setup() -> int:
    """Create the upgrade profile and point the recycle bin at _trash, once.

    Returns:
        The upgrade profile's id.
    """
    config = lidarr("/config/mediamanagement")
    if config["recycleBin"] != RECYCLE_BIN:
        Path(RECYCLE_BIN).mkdir(parents=True, exist_ok=True)
        lidarr(
            f"/config/mediamanagement/{config['id']}", {**config, "recycleBin": RECYCLE_BIN, "recycleBinCleanupDays": 0}
        )
        log.info("recycle bin set to %s (never cleaned automatically)", RECYCLE_BIN)
    existing = next((p for p in lidarr("/qualityprofile") if p["name"] == PROFILE_NAME), None)
    if existing:
        return existing["id"]
    schema = lidarr("/qualityprofile/schema")
    for item in schema["items"]:
        item["allowed"] = item.get("name") == TARGET_GROUP
    target = next(i for i in schema["items"] if i.get("name") == TARGET_GROUP)
    profile = {**schema, "name": PROFILE_NAME, "upgradeAllowed": True, "cutoff": target["id"]}
    log.info("created quality profile %r", PROFILE_NAME)
    return lidarr("/qualityprofile", profile, "POST")["id"]


def low_albums(groups: dict[int, str], skip: set[str]) -> list[dict]:
    """Albums holding songs at or below 224 kbps, worst first.

    Returns:
        One dict per album: albumId, artistId, worst (index into LOW_GROUPS), count of low songs.
    """
    albums: dict[str, dict] = {}
    for artist in lidarr("/artist"):
        for f in lidarr(f"/trackfile?artistId={artist['id']}"):
            group = groups.get(f["quality"]["quality"]["id"])
            album = str(f["albumId"])
            if group not in LOW_GROUPS or album in skip:
                continue
            entry = albums.setdefault(album, {"albumId": album, "artistId": artist["id"], "worst": 9, "low": 0})
            entry["worst"] = min(entry["worst"], LOW_GROUPS.index(group))
            entry["low"] += 1
    return sorted(albums.values(), key=lambda a: (a["worst"], -a["low"]))


def album_files(album: str) -> tuple[list[dict], dict[int, dict]]:
    """An album's tracks, and its track files by id."""
    return lidarr(f"/track?albumId={album}"), {f["id"]: f for f in lidarr(f"/trackfile?albumId={album}")}


def finish(state: dict, groups: dict[int, str], dry_run: bool) -> None:
    """Close out started albums whose songs are all at 320 now (or that waited too long)."""
    for album, info in list(state["pending"].items()):
        tracks, files = album_files(album)
        had = set(info["had"])
        kept = [files.get(t["trackFileId"]) for t in tracks if t["id"] in had]
        upgraded = all(f and groups.get(f["quality"]["quality"]["id"]) == TARGET_GROUP for f in kept)
        expired = time.time() - info["started"] > GIVE_UP_DAYS * 86400
        if not (upgraded or expired):
            if not dry_run:  # search again daily: indexers rate-limit, and new releases appear
                lidarr("/command", {"name": "AlbumSearch", "albumIds": [int(album)]}, "POST")
            continue
        extra = [t["trackFileId"] for t in tracks if t["id"] not in had and t["trackFileId"] in files]
        log.info("%s: %s, removing %d extra tracks", info["title"], "upgraded" if upgraded else "gave up", len(extra))
        if dry_run:
            continue
        if extra:
            lidarr("/trackfile/bulk", {"trackFileIds": extra}, "DELETE")
        lidarr("/album/monitor", {"albumIds": [int(album)], "monitored": False})
        state["done" if upgraded else "gave_up"].append(album)
        del state["pending"][album]


def start(state: dict, groups: dict[int, str], profile: int, limit: int, dry_run: bool) -> None:
    """Monitor and search the next albums with low-bitrate songs."""
    skip = set(state["pending"]) | set(state["done"]) | set(state["gave_up"])
    for entry in low_albums(groups, skip)[: max(0, limit - len(state["pending"]))]:
        album = lidarr(f"/album/{entry['albumId']}")
        tracks, _ = album_files(entry["albumId"])
        title = f"{album['artist']['artistName']} - {album['title']}"
        log.info("%s: %d low-bitrate songs (%s), searching", title, entry["low"], LOW_GROUPS[entry["worst"]])
        if dry_run:
            continue
        artist = lidarr(f"/artist/{entry['artistId']}")
        if artist["qualityProfileId"] != profile:
            lidarr(f"/artist/{artist['id']}", {**artist, "qualityProfileId": profile})
        lidarr("/album/monitor", {"albumIds": [album["id"]], "monitored": True})
        lidarr("/command", {"name": "AlbumSearch", "albumIds": [album["id"]]}, "POST")
        had = [t["id"] for t in tracks if t["hasFile"]]
        state["pending"][entry["albumId"]] = {"title": title, "started": time.time(), "had": had}


def load_state() -> dict:
    """Progress kept between runs."""
    return json.loads(STATE.read_text()) if STATE.exists() else {"pending": {}, "done": [], "gave_up": []}


def run(args: argparse.Namespace) -> None:
    """Finish what's ready, then start more albums up to --albums in flight."""
    state = load_state()
    groups = quality_groups()
    profile = ensure_setup() if not args.dry_run else 0
    finish(state, groups, args.dry_run)
    start(state, groups, profile, args.albums, args.dry_run)
    if not args.dry_run:
        STATE.write_text(json.dumps(state, indent=1))


def status() -> None:
    """Print progress."""
    state = load_state()
    print(
        f"in progress {len(state['pending'])} · upgraded {len(state['done'])} · no 320 release {len(state['gave_up'])}"
    )
    for info in state["pending"].values():
        print(f"  {info['title']} (started {time.strftime('%Y-%m-%d', time.localtime(info['started']))})")


def install() -> None:
    """Write and load the launchd agent: daily at RUN_HOUR."""
    plist = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    data = {
        "Label": LABEL,
        "ProgramArguments": ["/usr/bin/python3", str(Path(__file__).resolve()), "run"],
        "StartCalendarInterval": {"Hour": RUN_HOUR, "Minute": 0},
        "StandardOutPath": str(LOG),
        "StandardErrorPath": str(LOG),
    }
    plist.write_bytes(plistlib.dumps(data))
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True, check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True)
    print(f"installed {plist}: daily at {RUN_HOUR:02d}:00, log {LOG}")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="install the daily launchd agent")
    sub.add_parser("status", help="show progress")
    r = sub.add_parser("run", help="finish ready albums, start new ones")
    r.add_argument("--albums", type=int, default=ALBUMS_PER_RUN, help="albums in flight at once")
    r.add_argument("--dry-run", action="store_true", help="show what would happen")
    args = parser.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(LOG)] + ([logging.StreamHandler()] if sys.stderr.isatty() else [])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=handlers)
    {"install": install, "status": status, "run": lambda: run(args)}[args.command]()


if __name__ == "__main__":
    main()
