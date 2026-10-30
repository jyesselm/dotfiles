"""Keep a manifest of every media drive, so you can tell which drive holds what while most are unplugged.

`catalog` walks a mounted drive (same skips as the index: hidden entries and _trash) and writes one TSV row per
file: path, size, mtime. The manifest is saved on the Mac under ~/.local/share/media-index/drives/<drive>.tsv and
on the drive itself as .media-manifest.tsv, so a drive still describes itself if the Mac's copy is lost.

A file counts as backed up on another drive when a file there has the same name and size, or (for files over
RENAMED_MIN_BYTES) just the same size, which catches renames such as Radarr's "Title (Year)" folders.

    python3 drives.py catalog "/Volumes/Plex Disk 1"       # name defaults to the volume name
    python3 drives.py list                                  # drives catalogued, size, date
    python3 drives.py where supernatural                    # which drives hold matching titles
    python3 drives.py missing plex-backup-1 plex-media       # titles on the first drive with no copy on the second
    python3 drives.py status --notify                       # how far behind each full backup is (weekly reminder)
    python3 drives.py sync plex-tv-backups                  # bring one backup up to date, then re-catalog it
    python3 drives.py cold plex-cold-1 "tv/The Office (US)" # move titles off plex-media onto a cold drive
    python3 drives.py cold plex-cold-2 --csv picks.csv --dry-run

`cold` copies each title to the same folder on the cold drive, checks the copy (file count and bytes), drops it from
Radarr/Sonarr with an import-list exclusion so it isn't grabbed again, moves the original into plex-media/_trash,
then re-catalogs the drive and has Plex refresh the library. The cold drive then holds the only copy: the next
`sync` of the regular backup drives removes the title there too.

Or click instead: Media Index's "Cold" button marks a title to move out, and the Drives tab's "Bring back" marks one
to copy home (re-added to Radarr/Sonarr, no search; the cold copy stays as a backup). `watch` runs from launchd
every WATCH_MINUTES and whenever a drive is plugged in; for each plugged-in drive with marked titles it runs
`queue <drive>` in a one-off media-index container (launchd itself can't write the media disk), which does the
moves and reports each back to the page.

    python3 drives.py install                               # launchd agent for watch
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import arr
import index  # only its walk and item_for are used; its container paths are never touched here
import shrink  # host-side Radarr/Sonarr table and .env reader

CATALOG_DIR = Path(os.environ.get("DRIVE_CATALOG_DIR", Path.home() / ".local/share/media-index/drives"))
ON_DRIVE_NAME = ".media-manifest.tsv"  # hidden, so index.walk never lists it
RENAMED_MIN_BYTES = 50_000_000  # below this, equal sizes are too common to mean "same file"
FIELDS = ["path", "size", "mtime"]
MAIN_DRIVE = "plex-media"
# Drive -> what of MAIN_DRIVE it mirrors: a whole top-level folder, or "folder/<glob>" for the entries in it whose
# name matches (rsync filter syntax). tv is split by first letter so it fits on two drives.
TV_FIRST_HALF = "0-9A-Sa-s"  # first letters of the tv shows on plex-tv-backups
BACKUPS = {
    "plex-movie-backups": ["movies"],
    "plex-tv-backups": [f"tv/[{TV_FIRST_HALF}]*", "audiobooks"],
    "plex-misc-backups": [f"tv/[!{TV_FIRST_HALF}]*", "anime", "other", "youtube", "music", "podcasts"],
}
# Second copy of what can't be re-downloaded (backup.sh's CLOUD_FOLDERS). The same two drives also hold cold storage
# (plex-cold-1/tv: shows moved off plex-media, copied back when wanted); sync never touches those folders, and the
# drives stay unplugged and ejectable: nothing on the Mac or in a container depends on them.
OFFSITE = ["other", "anime", "youtube", "music", "podcasts", "audiobooks"]
BACKUPS |= {"plex-cold-1": OFFSITE, "plex-cold-2": OFFSITE}
SETTINGS_DIR = "_backups/settings"  # backup.sh's nightly archives; every backup drive gets a copy when synced
PLEX = os.environ.get("PLEX_URL", "http://localhost:32400")
PLEX_SECTIONS = {"movies": 1, "tv": 2, "anime": 4}  # library id per top-level folder, for refreshes after `cold`
QUALITY_PROFILE = 4  # HD-1080p in both Radarr and Sonarr, for titles brought back from cold storage
COLD_DRIVES = ["plex-cold-1", "plex-cold-2"]
COMPOSE = "/Applications/OrbStack.app/Contents/MacOS/xbin/docker-compose"
WATCH_LABEL = "com.yesselman.cold-moves"
WATCH_MINUTES = 10
REMINDED = shrink.STATE_DIR / "cold-moves-reminded"


@dataclass(frozen=True)
class Entry:
    """One file in a drive manifest."""

    path: str
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1].lower()

    @property
    def item(self) -> str:
        return index.item_for(self.path)[0]


def catalog(mount: Path, drive: str) -> list[Entry]:
    """Walk a mounted drive and save its manifest on the Mac and on the drive.

    Args:
        mount: Where the drive is mounted, e.g. /Volumes/plex-media.
        drive: Name to store it under.

    Returns:
        The entries written.
    """
    entries = [Entry(f.path, f.size, f.mtime) for f in index.walk(mount)]
    saved = catalog_path(drive)
    save(entries, saved)
    try:
        shutil.copyfile(saved, mount / ON_DRIVE_NAME)
    except OSError as err:  # read-only drive: the Mac copy is enough
        print(f"couldn't write {mount / ON_DRIVE_NAME}: {err}")
    return entries


def catalog_path(drive: str) -> Path:
    """Where a drive's manifest lives on the Mac."""
    return CATALOG_DIR / f"{drive}.tsv"


def save(entries: list[Entry], path: Path) -> None:
    """Write entries as a TSV manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(FIELDS)
        for e in entries:
            writer.writerow([e.path, e.size, f"{e.mtime:.0f}"])


def load(drive: str) -> list[Entry]:
    """Read a drive's manifest from the Mac."""
    with catalog_path(drive).open(newline="") as fh:
        rows = csv.DictReader(fh, delimiter="\t")
        return [Entry(r["path"], int(r["size"]), float(r["mtime"])) for r in rows]


def drives() -> list[str]:
    """Names of all catalogued drives."""
    return sorted(p.stem for p in CATALOG_DIR.glob("*.tsv"))


def missing(source: list[Entry], target: list[Entry]) -> dict[str, int]:
    """Titles with files in source that have no copy in target.

    Args:
        source: Manifest of the drive being checked.
        target: Manifest of the drive that should hold the copies.

    Returns:
        Item -> bytes of its files with no copy, largest first.
    """
    names_sizes = {(e.name, e.size) for e in target}
    sizes = {e.size for e in target if e.size > RENAMED_MIN_BYTES}
    uncopied: dict[str, int] = defaultdict(int)
    for e in source:
        if not has_copy(e, names_sizes, sizes):
            uncopied[e.item] += e.size
    return dict(sorted(uncopied.items(), key=lambda kv: -kv[1]))


def has_copy(entry: Entry, names_sizes: set[tuple[str, int]], sizes: set[int]) -> bool:
    """True when the target holds this file under its own name, or renamed with the same large size."""
    is_large = entry.size > RENAMED_MIN_BYTES
    return (entry.name, entry.size) in names_sizes or (is_large and entry.size in sizes)


def where(text: str) -> dict[str, dict[str, int]]:
    """Which drives hold titles whose path contains text (case-insensitive).

    Returns:
        Item -> {drive: bytes}.
    """
    needle = text.lower()
    found: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for drive in drives():
        for e in load(drive):
            if needle in e.path.lower():
                found[e.item][drive] += e.size
    return dict(sorted(found.items()))


def backup_status(main: str = MAIN_DRIVE) -> list[tuple[str, str, int, float]]:
    """How far each full backup (BACKUPS) is behind the main drive.

    Args:
        main: The drive the backups copy.

    Returns:
        (drive, folder, bytes of main's files in that folder with no copy there, when it was catalogued).
    """
    source = load(main)
    rows = []
    for drive, scopes in BACKUPS.items():
        if not catalog_path(drive).exists():
            continue
        target = load(drive)
        stamp = catalog_path(drive).stat().st_mtime
        for scope in scopes:
            scoped = [e for e in source if in_scope(e.path, scope)]
            rows.append((drive, scope, sum(missing(scoped, target).values()), stamp))
    return rows


def in_scope(path: str, scope: str) -> bool:
    """True when a path relative to the drive falls under a BACKUPS scope ("tv" or "tv/[0-9A-Sa-s]*")."""
    folder, _, pattern = scope.partition("/")
    top, _, rest = path.partition("/")
    return top == folder and (not pattern or fnmatch.fnmatchcase(rest.split("/", 1)[0], pattern))


def sync_commands(drive: str) -> list[list[str]]:
    """The rsync runs that make a drive match its BACKUPS scopes, plus a copy of the settings archives.

    --delete removes what was deleted from MAIN_DRIVE; with a name filter it only touches matching entries.
    """
    commands = []
    for scope in BACKUPS[drive]:
        folder, _, pattern = scope.partition("/")
        filters = ["--include", f"/{pattern}", "--exclude", "/*"] if pattern else []
        commands.append(rsync_command(drive, folder, filters))
    commands.append(rsync_command(drive, SETTINGS_DIR, []))
    return commands


def rsync_command(drive: str, folder: str, filters: list[str]) -> list[str]:
    """rsync that mirrors MAIN_DRIVE's folder onto the same folder of drive."""
    return ["rsync", "-a", "--delete", *filters, f"/Volumes/{MAIN_DRIVE}/{folder}/", f"/Volumes/{drive}/{folder}/"]


def sync(drive: str) -> None:
    """Run sync_commands for a mounted drive, then re-catalog it."""
    mount = Path("/Volumes") / drive
    if not mount.is_dir():
        raise SystemExit(f"{mount} is not mounted")
    for command in sync_commands(drive):
        print(" ".join(command))
        Path(command[-1]).mkdir(parents=True, exist_ok=True)
        subprocess.run(command, check=True)
    entries = catalog(mount, drive)
    print(f"{len(entries)} files, {gb(sum(e.size for e in entries)).strip()} on {drive}")


def cold(drive: str, items: list[str], dry_run: bool) -> None:
    """Move titles off MAIN_DRIVE onto a cold drive: copy, verify, drop from Radarr/Sonarr, original to _trash.

    Args:
        drive: Mounted cold drive, e.g. plex-cold-1.
        items: Titles relative to the media root, e.g. "tv/The Office (US)".
        dry_run: Only print what would move.
    """
    mount = mounted(drive)
    moved: list[str] = []
    for item in items:
        src = Path("/Volumes") / MAIN_DRIVE / item
        if dry_run:
            files, size = measure(src) if src.exists() else (0, 0)
            print(f"{gb(size)}  {files:5} files  {item}")
            continue
        try:
            print(f"{item}: {move_out(mount, item)}")
            moved.append(item)
        except MoveError as err:
            print(f"skip {item}: {err}")
    if moved:
        finish(drive, moved)


class MoveError(Exception):
    """A title that can't be moved; the message says why, and nothing was changed."""


def mounted(drive: str) -> Path:
    mount = Path("/Volumes") / drive
    if not mount.is_dir():
        raise SystemExit(f"{mount} is not mounted")
    return mount


def move_out(mount: Path, item: str) -> str:
    """Copy one title to the cold drive, verify it, drop it from Radarr/Sonarr and move the original to _trash.

    Returns:
        What happened, for the log or the page.

    Raises:
        MoveError: When the title isn't there, already moved, or the copy doesn't match.
    """
    main = Path("/Volumes") / MAIN_DRIVE
    src, dst, trash = main / item, mount / item, main / "_trash" / item
    if not src.exists():
        raise MoveError(f"not on {MAIN_DRIVE}")
    if trash.exists() or (dst.exists() and measure(dst) != measure(src)):
        raise MoveError(f"already in _trash, or a different copy is on {mount.name}")
    copy(src, dst)
    dropped = drop_from_arr(src) or "not in Radarr/Sonarr"
    trash.parent.mkdir(parents=True, exist_ok=True)
    src.rename(trash)
    return f"{gb(measure(dst)[1]).strip()} copied; {dropped}; original in _trash"


def move_back(mount: Path, item: str) -> str:
    """Copy one title from a cold drive back onto MAIN_DRIVE and re-add it to Radarr/Sonarr (no search).

    The cold copy stays where it is, as a backup.

    Raises:
        MoveError: When the title isn't on the drive, is already on MAIN_DRIVE, or the copy doesn't match.
    """
    src, dst = mount / item, Path("/Volumes") / MAIN_DRIVE / item
    if not src.exists():
        raise MoveError(f"not on {mount.name}")
    if dst.exists():
        raise MoveError(f"already on {MAIN_DRIVE}")
    copy(src, dst)
    return f"{gb(measure(dst)[1]).strip()} copied back; {add_to_arr(dst)}"


def copy(src: Path, dst: Path) -> None:
    """rsync a title (folder or single file) and check file count and bytes match."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = f"{src}/" if src.is_dir() else str(src)
    subprocess.run(["rsync", "-a", source, str(dst) + ("/" if src.is_dir() else "")], check=True)
    if measure(dst) != measure(src):
        raise MoveError(f"copy at {dst} doesn't match, original left in place")


def finish(drive: str, items: list[str]) -> None:
    """After moves: re-catalog both drives and have Plex pick up the change in each library touched."""
    for name in (drive, MAIN_DRIVE):
        entries = catalog(Path("/Volumes") / name, name)
        print(f"{len(entries)} files, {gb(sum(e.size for e in entries)).strip()} on {name}")
    for category in {item.split("/")[0] for item in items}:
        plex_refresh(category)


def measure(path: Path) -> tuple[int, int]:
    """(file count, bytes) of a title, skipping the same hidden entries the index does."""
    if path.is_file():
        return 1, path.stat().st_size
    stats = list(index.walk(path))
    return len(stats), sum(f.size for f in stats)


def drop_from_arr(path: Path) -> str:
    """Remove the Radarr movie / Sonarr series at path, keeping files, and exclude it from import lists.

    Returns:
        A short message, or "" when neither app manages the path.
    """
    category = path.relative_to(Path("/Volumes") / MAIN_DRIVE).parts[0]
    if category not in shrink.ARR:
        return ""
    base, kind, env_key, _ = shrink.ARR[category]
    key = shrink.read_env().get(env_key, "")
    match = next((e for e in arr.request(f"{base}/{kind}", key) if e.get("path") == str(path)), None)
    if not match:
        return ""
    exclusion = "addImportExclusion" if kind == "movie" else "addImportListExclusion"
    arr.request(f"{base}/{kind}/{match['id']}?deleteFiles=false&{exclusion}=true", key, method="DELETE")
    return f"removed from {'Radarr' if kind == 'movie' else 'Sonarr'} (files kept, import-list exclusion added)"


def add_to_arr(path: Path) -> str:
    """Re-add a title copied back to MAIN_DRIVE to Radarr/Sonarr: lift the exclusion drop_from_arr added, then add it
    at its path, monitored, with no search (the files are already there; Radarr/Sonarr scan them on add).

    Returns:
        A short message.
    """
    category = path.relative_to(Path("/Volumes") / MAIN_DRIVE).parts[0]
    if category not in shrink.ARR:
        return "not a Radarr/Sonarr folder"
    base, kind, env_key, _ = shrink.ARR[category]
    key = shrink.read_env().get(env_key, "")
    app = "Radarr" if kind == "movie" else "Sonarr"
    wanted = index.title_key(path.name)
    if kind == "movie":
        exclusions, id_field, title_field = arr.request(f"{base}/exclusions", key), "tmdbId", "movieTitle"
    else:
        exclusions, id_field, title_field = arr.request(f"{base}/importlistexclusion", key), "tvdbId", "title"
    exclusion = next((e for e in exclusions if index.title_key(e[title_field]) == wanted), None)
    if exclusion:
        arr.request(f"{base}/{'exclusions' if kind == 'movie' else 'importlistexclusion'}/{exclusion['id']}", key,
                    method="DELETE")
        term = f"{'tmdb' if kind == 'movie' else 'tvdb'}:{exclusion[id_field]}"
    else:
        term = path.name
    found = arr.request(f"{base}/{kind}/lookup?term={urllib.parse.quote(term)}", key)
    match = next((f for f in found if exclusion or index.title_key(f"{f['title']} ({f.get('year')})") == wanted), None)
    if not match:
        return f"not found in {app}'s lookup; add it there by hand"
    if match.get("id"):
        return f"already in {app}"
    search = {"searchForMovie": False} if kind == "movie" else {"searchForMissingEpisodes": False, "monitor": "all"}
    body = {**match, "path": str(path), "rootFolderPath": str(path.parent), "qualityProfileId": QUALITY_PROFILE,
            "monitored": True, "addOptions": search}
    if kind == "series":
        body["seasonFolder"] = True
    arr.request(f"{base}/{kind}", key, body, "POST")
    return f"added back to {app}" + (" (exclusion lifted)" if exclusion else "")


def plex_refresh(category: str) -> None:
    """Have Plex rescan the library for a top-level folder and empty its trash, so moved titles disappear."""
    section = PLEX_SECTIONS.get(category)
    token = shrink.read_env().get("HOMEPAGE_VAR_PLEX_TOKEN", "")
    if not section or not token:
        return
    plex(f"/library/sections/{section}/refresh?X-Plex-Token={token}")
    for _ in range(60):  # a refresh is asynchronous; wait for it before emptying the trash
        time.sleep(5)
        library = re.search(rf'<Directory[^>]*\bkey="{section}"[^>]*>', plex(f"/library/sections?X-Plex-Token={token}"))
        if library and 'refreshing="1"' not in library.group():
            break
    plex(f"/library/sections/{section}/emptyTrash?X-Plex-Token={token}", "PUT")
    print(f"Plex library {section} refreshed, trash emptied")


def plex(path: str, method: str = "GET") -> str:
    """Call the local Plex server and return the response body."""
    with urllib.request.urlopen(urllib.request.Request(PLEX + path, method=method), timeout=60) as resp:
        return resp.read().decode(errors="replace")


def run_queue(drive: str) -> None:
    """Do the moves marked in Media Index for one mounted cold drive, reporting each back to the page.

    Runs in a one-off media-index container (`watch` starts it), which can write the media disk, unlike launchd.
    """
    mount = mounted(drive)
    jobs = [j for j in arr.request(f"{shrink.API}/cold-moves", "") if j["drive"] == drive and j["status"] == "queued"]
    done = []
    for job in jobs:
        report(job, "running", "copying")
        try:
            message = (move_out if job["direction"] == "out" else move_back)(mount, job["item"])
        except (MoveError, OSError, subprocess.CalledProcessError, urllib.error.URLError) as err:
            report(job, "failed", str(err))
            continue
        report(job, "done", message)
        done.append(job["item"])
    if done:
        finish(drive, done)


def report(job: dict, status: str, message: str) -> None:
    print(f"{status}: {job['direction']} {job['item']}: {message}", flush=True)
    body = {"item": job["item"], "status": status, "message": message}
    arr.request(f"{shrink.API}/cold-moves/status", "", body, "POST")


def watch() -> None:
    """Host side, from launchd: when a drive with queued moves is plugged in, run the queue for it in a container.

    The container mounts the drive only while it runs, so the drive stays ejectable. Queued moves whose drive isn't
    plugged in get one reminder a day.
    """
    jobs = [j for j in arr.request(f"{shrink.API}/cold-moves", "") if j["status"] == "queued"]
    needed = sorted({j["drive"] for j in jobs})
    mounts = subprocess.run(["/sbin/mount"], capture_output=True, text=True, check=True).stdout
    plugged = [d for d in needed if f" on /Volumes/{d} (" in mounts]
    for drive in plugged:
        volume = f"/Volumes/{drive}:/Volumes/{drive}"
        command = [COMPOSE, "run", "--rm", "-T", "-v", volume, "media-index", "python", "-u", "drives.py", "queue"]
        command.append(drive)
        print(time.strftime("%F %T"), " ".join(command), flush=True)
        subprocess.run(command, cwd=Path(__file__).resolve().parents[1], check=False)
    waiting = [d for d in needed if d not in plugged]
    reminded_recently = REMINDED.exists() and time.time() - REMINDED.stat().st_mtime < 86400
    if waiting and not reminded_recently:
        counts = ", ".join(f"{sum(j['drive'] == d for j in jobs)} for {d}" for d in waiting)
        notify("Plug in a cold drive", f"Moves waiting in Media Index: {counts}")
        REMINDED.touch()


def csv_items(path: Path) -> list[str]:
    """Titles from a move_candidates CSV (folder + show, or folder) as paths relative to the media root."""
    root = Path("/Volumes") / MAIN_DRIVE
    items = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            full = Path(row["folder"]) / row["show"] if row.get("show") else Path(row["folder"])
            rel = full.relative_to(root).as_posix()
            if not full.exists():  # Plex titles don't always match folder names ("American Dad!" vs "American Dad")
                category = rel.split("/")[0]
                folders = {index.title_key(d.name): d.name for d in (root / category).iterdir() if d.is_dir()}
                found = folders.get(index.title_key(full.name))
                rel = f"{category}/{found}" if found else rel
            items.append(rel)
    return items


def print_status(show_notification: bool) -> None:
    """Print how far each backup is behind, with the command that catches it up."""
    lines = []
    for drive, scope, behind, stamp in backup_status():
        days = (time.time() - stamp) / 86400
        lines.append(f"{drive} {scope}: {gb(behind).strip()} not copied, last synced {days:.0f} days ago")
        print(lines[-1])
    if lines:
        print("plug a drive in and run: python3 media-index/drives.py sync <drive>")
    if show_notification and lines:
        notify("Back up the media drives", "; ".join(lines))


def notify(title: str, message: str) -> None:
    """Show a macOS notification (inside a container there is no osascript; the caller's log has the message)."""
    script = f"display notification {applescript_str(message)} with title {applescript_str(title)}"
    if shutil.which("osascript"):
        subprocess.run(["osascript", "-e", script], check=False)


def applescript_str(text: str) -> str:
    """Quote text as an AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def gb(size: int) -> str:
    return f"{size / 1e9:7.1f} GB"


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("catalog", help="walk a mounted drive and save its manifest")
    c.add_argument("mount", type=Path)
    c.add_argument("--name", help="drive name (default: the volume name)")
    sub.add_parser("list", help="catalogued drives")
    w = sub.add_parser("where", help="which drives hold matching titles")
    w.add_argument("text")
    m = sub.add_parser("missing", help="titles on SOURCE with no copy on TARGET")
    m.add_argument("source")
    m.add_argument("target")
    s = sub.add_parser("status", help=f"how far each full backup is behind {MAIN_DRIVE}")
    s.add_argument("--notify", action="store_true", help="also show a macOS notification")
    y = sub.add_parser("sync", help="bring a backup drive up to date and re-catalog it")
    y.add_argument("drive", choices=sorted(BACKUPS))
    k = sub.add_parser("cold", help=f"move titles off {MAIN_DRIVE} onto a cold drive (originals go to _trash)")
    k.add_argument("drive")
    k.add_argument("items", nargs="*", help='titles relative to the media root, e.g. "tv/The Office (US)"')
    k.add_argument("--csv", type=Path, help="a move_candidates CSV (folder + show, or folder columns)")
    k.add_argument("--dry-run", action="store_true", help="only list what would move")
    q = sub.add_parser("queue", help="do the moves marked in Media Index for a mounted cold drive (in the container)")
    q.add_argument("drive", choices=COLD_DRIVES)
    sub.add_parser("watch", help="run the queue for any plugged-in cold drive (launchd, every WATCH_MINUTES)")
    sub.add_parser("install", help="install the launchd agent that runs watch")
    args = parser.parse_args()

    if args.command == "catalog":
        drive = args.name or args.mount.name
        entries = catalog(args.mount, drive)
        print(f"{len(entries)} files, {gb(sum(e.size for e in entries)).strip()} → {catalog_path(drive)}")
    elif args.command == "list":
        for drive in drives():
            entries = load(drive)
            stamp = time.strftime("%Y-%m-%d", time.localtime(catalog_path(drive).stat().st_mtime))
            print(f"{gb(sum(e.size for e in entries))}  {len(entries):6} files  catalogued {stamp}  {drive}")
    elif args.command == "where":
        for item, by_drive in where(args.text).items():
            print(item)
            for drive, size in by_drive.items():
                print(f"   {gb(size)}  {drive}")
    elif args.command == "status":
        print_status(args.notify)
    elif args.command == "sync":
        sync(args.drive)
    elif args.command == "queue":
        run_queue(args.drive)
    elif args.command == "watch":
        watch()
    elif args.command == "install":
        args = ["/usr/bin/python3", str(Path(__file__).resolve()), "watch"]
        log = shrink.STATE_DIR / "cold-moves.log"
        plist = shrink.install_agent(WATCH_LABEL, args, {"StartInterval": WATCH_MINUTES * 60}, log,
                                     {"WatchPaths": ["/Volumes"]})
        print(f"installed {plist}; log {log}")
    elif args.command == "cold":
        cold(args.drive, args.items + (csv_items(args.csv) if args.csv else []), args.dry_run)
    else:
        for item, size in missing(load(args.source), load(args.target)).items():
            print(f"{gb(size)}  {item}")


if __name__ == "__main__":
    main()
