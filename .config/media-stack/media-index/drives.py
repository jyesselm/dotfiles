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
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import index  # only its walk and item_for are used; its container paths are never touched here

CATALOG_DIR = Path(os.environ.get("DRIVE_CATALOG_DIR", Path.home() / ".local/share/media-index/drives"))
ON_DRIVE_NAME = ".media-manifest.tsv"  # hidden, so index.walk never lists it
RENAMED_MIN_BYTES = 50_000_000  # below this, equal sizes are too common to mean "same file"
FIELDS = ["path", "size", "mtime"]
MAIN_DRIVE = "plex-media"
BACKUPS = {"plex-movie-backups": ["movies"]}  # drive -> folders of MAIN_DRIVE it mirrors in full


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
    for drive, folders in BACKUPS.items():
        if not catalog_path(drive).exists():
            continue
        target = load(drive)
        stamp = catalog_path(drive).stat().st_mtime
        for folder in folders:
            scoped = [e for e in source if e.path.startswith(f"{folder}/")]
            rows.append((drive, folder, sum(missing(scoped, target).values()), stamp))
    return rows


def print_status(show_notification: bool) -> None:
    """Print how far each backup is behind, with the command that catches it up."""
    lines = []
    for drive, folder, behind, stamp in backup_status():
        days = (time.time() - stamp) / 86400
        lines.append(f"{drive}/{folder}: {gb(behind).strip()} not copied, last catalogued {days:.0f} days ago")
        print(lines[-1])
        print(f"   rsync -a --delete /Volumes/{MAIN_DRIVE}/{folder}/ /Volumes/{drive}/{folder}/")
        print(f"   python3 drives.py catalog /Volumes/{drive}")
    if show_notification and lines:
        notify("Back up the media drives", "; ".join(lines))


def notify(title: str, message: str) -> None:
    """Show a macOS notification."""
    script = f"display notification {applescript_str(message)} with title {applescript_str(title)}"
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
    else:
        for item, size in missing(load(args.source), load(args.target)).items():
            print(f"{gb(size)}  {item}")


if __name__ == "__main__":
    main()
