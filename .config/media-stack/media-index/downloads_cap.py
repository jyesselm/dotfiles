"""Keep downloads/radarr and downloads/sonarr under a size cap. launchd runs it in the media-index container every
CHECK_MINUTES (macOS doesn't let launchd's own python touch the media disk).

What fills these folders: finished torrents (hardlinked into the library, so they cost nothing extra), downloads in
progress (qBittorrent allocates the whole file up front), and leftovers: folders no torrent owns any more, after
Radarr or Sonarr dropped a stuck download. Each run, per category:
(1) leftovers untouched for ORPHAN_AGE_DAYS are moved to _trash/downloads (nothing is deleted, empty _trash by hand);
(2) when the folder's own bytes (files not hardlinked into the library) plus what the active torrents still have
    to fetch would exceed CAP_GB, the torrents with the most left are stopped and tagged "capped", largest first,
    until the rest fits;
(3) when there is room again, capped torrents are started again, smallest first.

    python3 downloads_cap.py run [--dry-run]
    python3 downloads_cap.py install   # launchd agent, every CHECK_MINUTES

`install` runs on the host's /usr/bin/python3 (3.9).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from drives import notify
from shrink import MEDIA_ROOT, STATE_DIR, install_agent

CAP_GB = {"radarr": 150, "sonarr": 100}
ORPHAN_AGE_DAYS = 1
CHECK_MINUTES = 30
QB = os.environ.get("QB_URL", "http://localhost:8080/api/v2")  # env: in the media-index container
TAG = "capped"
LABEL = "com.yesselman.downloads-cap"
LOG = STATE_DIR / "downloads-cap.log"
DOWNLOADING = {"downloading", "queuedDL", "stalledDL", "metaDL", "forcedDL", "checkingDL", "allocating"}
STOPPED = {"stoppedDL", "pausedDL"}

log = logging.getLogger("downloads-cap")


def qb(path: str, params: dict | None = None, post: bool = False) -> object:
    """Call qBittorrent's web API (localhost is exempt from its login)."""
    data = urllib.parse.urlencode(params or {})
    url = f"{QB}/{path}" + ("" if post or not data else f"?{data}")
    with urllib.request.urlopen(url, data=data.encode() if post else None, timeout=60) as resp:
        body = resp.read()
    return json.loads(body) if body.startswith(b"[") or body.startswith(b"{") else body.decode()


def measure(path: Path) -> tuple[int, float]:
    """(bytes only here, i.e. files not hardlinked elsewhere; newest mtime) of a download entry."""
    files = [path] if path.is_file() else [Path(d) / f for d, _, fs in os.walk(path) for f in fs]
    stats = [f.lstat() for f in files]
    newest = max((s.st_mtime for s in stats), default=path.stat().st_mtime)
    return sum(s.st_size for s in stats if s.st_nlink == 1), newest


def trash(rel: str) -> str:
    """Move downloads/<category>/<name> into _trash (same disk, instant, reversible)."""
    dest = MEDIA_ROOT / "_trash" / rel
    if dest.exists():
        return "already in _trash, left in place"
    dest.parent.mkdir(parents=True, exist_ok=True)
    (MEDIA_ROOT / rel).rename(dest)
    return "moved to _trash"


def check(category: str, cap_gb: int, dry_run: bool) -> None:
    """One category: trash leftovers, then stop or restart torrents so the folder stays under the cap."""
    folder = MEDIA_ROOT / "downloads" / category
    if not folder.is_dir():
        return
    torrents = qb("torrents/info", {"category": category})
    owned = {Path(t["content_path"]).name for t in torrents if t["content_path"]}
    on_disk: dict[str, int] = {}
    for entry in sorted(folder.iterdir()):
        if entry.name.startswith("."):
            continue
        size, newest = measure(entry)
        if entry.name not in owned and time.time() - newest > ORPHAN_AGE_DAYS * 86400:
            log.info(f"{category}: leftover {gb(size)}  {entry.name} -> _trash/downloads/{category}")
            if not dry_run:
                log.info(f"   {trash(f'downloads/{category}/{entry.name}')}")
            continue
        on_disk[entry.name] = size

    def still_needs(t: dict) -> int:
        return max(0, t["total_size"] - on_disk.get(Path(t["content_path"]).name, 0)) if t["content_path"] else 0

    active = [t for t in torrents if t["state"] in DOWNLOADING]
    capped = [t for t in torrents if t["state"] in STOPPED and TAG in t["tags"].split(", ")]
    used, cap = sum(on_disk.values()), cap_gb * 1e9
    projected = used + sum(still_needs(t) for t in active)
    log.info(
        f"{category}: {gb(used)} on disk, {gb(projected)} once {len(active)} active downloads finish, cap {cap_gb} GB"
    )
    if projected > cap:
        stop = []
        for t in sorted(active, key=still_needs, reverse=True):
            if projected <= cap or not still_needs(t):
                break
            stop.append(t)
            projected -= still_needs(t)
        if stop:
            names = ", ".join(t["name"] for t in stop)
            log.info(f"{category}: over the cap, stopping {len(stop)}: {names}")
            if not dry_run:
                hashes = "|".join(t["hash"] for t in stop)
                qb("torrents/stop", {"hashes": hashes}, post=True)
                qb("torrents/addTags", {"hashes": hashes, "tags": TAG}, post=True)
                notify(f"downloads/{category} is over {cap_gb} GB", f"stopped {len(stop)} download(s): {names}")
        if projected > cap:
            log.info(f"{category}: still {gb(projected - cap)} over the cap with nothing left to stop")
        return
    for t in sorted(capped, key=still_needs):
        if projected + still_needs(t) > cap:
            break
        projected += still_needs(t)
        log.info(f"{category}: room again, starting {t['name']}")
        if not dry_run:
            qb("torrents/start", {"hashes": t["hash"]}, post=True)
            qb("torrents/removeTags", {"hashes": t["hash"], "tags": TAG}, post=True)


def gb(size: float) -> str:
    return f"{size / 1e9:.1f} GB"


def install() -> None:
    """Write and load the launchd agent: every CHECK_MINUTES."""
    # In the media-index container: launchd's own python may not change the disk.
    docker = "/Applications/OrbStack.app/Contents/MacOS/xbin/docker"
    args = [docker, "exec", "media-index", "python", "-u", "downloads_cap.py", "run"]
    plist = install_agent(LABEL, args, {"StartInterval": CHECK_MINUTES * 60}, LOG)
    print(f"installed {plist}: every {CHECK_MINUTES} min, log {LOG}")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="install the launchd agent")
    r = sub.add_parser("run", help="check every category once")
    r.add_argument("--dry-run", action="store_true", help="show what would happen")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)  # launchd writes LOG
    if args.command == "install":
        install()
    else:
        for category, cap_gb in CAP_GB.items():
            check(category, cap_gb, args.dry_run)


if __name__ == "__main__":
    main()
