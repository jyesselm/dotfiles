"""Scan the media disk into a SQLite index: one row per file, grouped into reviewable items.

An item is a title-sized unit: the folder (or loose file) one level under a top-level folder,
e.g. "Movies/Heat (1995)" or "TV Shows/The Wire". Music is reviewed song by song, so each file under
"music/" is its own item. Decisions are made per item.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/Volumes/Plex_Disk_4"))
DB_PATH = Path(os.environ.get("INDEX_DB", "/data/media-index.db"))
PLEX_DB_DIR = Path(os.environ.get("PLEX_DB_DIR", "/plex-db"))
TRASH_NAME = "_trash"
MUSIC_CATEGORY = "music"

VIDEO_EXTS = {"mkv", "mp4", "avi", "m4v", "mpg", "mpeg", "mov", "wmv", "ts", "webm", "flv"}
AUDIO_EXTS = {"mp3", "m4b", "m4a", "flac", "aac", "ogg", "wav", "opus"}
PROBE_WORKERS = 4
PROBE_TIMEOUT_S = 60

SCHEMA = """
create table if not exists files (
    path text primary key,      -- relative to MEDIA_ROOT
    item text not null,
    category text not null,
    kind text not null,         -- video | audio | other
    size integer not null,
    mtime real not null,
    nlink integer not null,     -- >1 means hardlinked (usually shared with downloading/)
    duration_s real,
    height integer,
    codec text,
    probed integer not null default 0,
    view_count integer not null default 0,
    last_viewed real
);
create index if not exists files_item on files(item);
create table if not exists decisions (
    item text primary key,
    decision text not null,     -- keep | delete
    note text not null default '',
    decided_at real not null,
    trashed_at real,
    size integer                -- bytes, recorded when moved to _trash
);
create table if not exists swaps (      -- movies replaced by a smaller release; original kept in _trash
    item text primary key,
    original text not null,
    original_size integer not null,
    release text not null,
    release_size integer not null,
    swapped_at real not null
);
create table if not exists state (key text primary key, value text not null);
"""


@dataclass
class FileStat:
    """One file found on disk."""

    path: str
    item: str
    category: str
    kind: str
    size: int
    mtime: float
    nlink: int


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the index database, creating the schema if needed.

    Args:
        db_path: Location of the SQLite file.

    Returns:
        A connection with row access by column name.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Rollback journal, not WAL: WAL shared memory is unsafe on bind mounts across the OrbStack VM boundary.
    conn.execute("pragma journal_mode=delete")
    conn.executescript(SCHEMA)
    return conn


def set_state(conn: sqlite3.Connection, key: str, value: object) -> None:
    """Store a JSON value in the state table.

    Args:
        conn: Index connection.
        key: State name.
        value: Any JSON-serializable value.
    """
    conn.execute("insert or replace into state values (?, ?)", (key, json.dumps(value)))
    conn.commit()


def get_state(conn: sqlite3.Connection, key: str, default: object = None) -> object:
    """Read a JSON value from the state table.

    Args:
        conn: Index connection.
        key: State name.
        default: Returned when the key is missing.

    Returns:
        The stored value or default.
    """
    row = conn.execute("select value from state where key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def item_for(rel_path: str) -> tuple[str, str]:
    """Return (item, category) for a path relative to the media root.

    Args:
        rel_path: e.g. "Movies/Heat (1995)/Heat.mkv".

    Returns:
        ("Movies/Heat (1995)", "Movies"); loose files at the root are their own item in "(root)",
        and each music file is its own item.
    """
    parts = rel_path.split("/")
    if len(parts) == 1:
        return rel_path, "(root)"
    if parts[0] == MUSIC_CATEGORY:
        return rel_path, parts[0]
    return "/".join(parts[:2]), parts[0]


def kind_for(name: str) -> str:
    """Classify a file name as video, audio or other by extension.

    Args:
        name: File name.

    Returns:
        "video", "audio" or "other".
    """
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return "other"


def is_skipped(name: str) -> bool:
    """True for hidden/system entries and the review trash, which are not indexed.

    Args:
        name: A file or folder name.

    Returns:
        Whether to skip it.
    """
    # "Icon\r" is Finder's custom folder icon; the \r also breaks TSV manifests.
    return name.startswith(".") or name in {TRASH_NAME, "$RECYCLE.BIN", "System Volume Information", "Icon\r"}


def walk(root: Path = MEDIA_ROOT) -> Iterator[FileStat]:
    """Yield every indexable file under root.

    Args:
        root: Media root.

    Yields:
        One FileStat per file.
    """
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _err: None):
        dirnames[:] = [d for d in dirnames if not is_skipped(d)]
        for name in filenames:
            if is_skipped(name):
                continue
            yield _stat(root, Path(dirpath) / name)


def _stat(root: Path, full: Path) -> FileStat:
    st = full.stat()
    rel = full.relative_to(root).as_posix()
    item, category = item_for(rel)
    return FileStat(rel, item, category, kind_for(full.name), st.st_size, st.st_mtime, st.st_nlink)


def probe(full: Path) -> dict[str, object]:
    """Read duration, height and codec of a video with ffprobe.

    Args:
        full: Absolute file path.

    Returns:
        Dict with duration_s, height, codec (values may be None when unreadable).
    """
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration:stream=codec_name,height",
        "-of", "json", str(full),
    ]  # fmt: skip
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=PROBE_TIMEOUT_S, check=False).stdout
        data = json.loads(out or b"{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"duration_s": None, "height": None, "codec": None}
    stream = (data.get("streams") or [{}])[0]
    duration = data.get("format", {}).get("duration")
    return {
        "duration_s": float(duration) if duration else None,
        "height": stream.get("height"),
        "codec": stream.get("codec_name"),
    }


def scan(conn: sqlite3.Connection, root: Path = MEDIA_ROOT) -> None:
    """Bring the index up to date: add/refresh changed files, drop missing ones, probe new videos.

    Unchanged files (same size and mtime) keep their probe results, so reruns are fast.

    Args:
        conn: Index connection.
        root: Media root.
    """
    set_state(conn, "scan", {"phase": "walking", "started": time.time()})
    seen = _upsert_walk(conn, root)
    _drop_missing(conn, seen)
    _apply_plex_views(conn)
    _probe_pending(conn, root)
    set_state(conn, "scan", {"phase": "done", "finished": time.time(), "files": len(seen)})


def _upsert_walk(conn: sqlite3.Connection, root: Path) -> set[str]:
    known = {r["path"]: (r["size"], r["mtime"]) for r in conn.execute("select path, size, mtime from files")}
    seen: set[str] = set()
    for f in walk(root):
        seen.add(f.path)
        if known.get(f.path) == (f.size, f.mtime):
            # item/category too, so a change to how items are grouped applies without re-probing.
            conn.execute(
                "update files set nlink = ?, item = ?, category = ? where path = ?",
                (f.nlink, f.item, f.category, f.path),
            )
            continue
        conn.execute(
            "insert or replace into files (path, item, category, kind, size, mtime, nlink, probed)"
            " values (?, ?, ?, ?, ?, ?, ?, 0)",
            (f.path, f.item, f.category, f.kind, f.size, f.mtime, f.nlink),
        )
        if len(seen) % 500 == 0:
            conn.commit()
            set_state(conn, "scan", {"phase": "walking", "files": len(seen)})
    conn.commit()
    return seen


def _drop_missing(conn: sqlite3.Connection, seen: set[str]) -> None:
    stale = [r["path"] for r in conn.execute("select path from files") if r["path"] not in seen]
    conn.executemany("delete from files where path = ?", [(p,) for p in stale])
    conn.commit()


def _probe_pending(conn: sqlite3.Connection, root: Path) -> None:
    pending = [r["path"] for r in conn.execute("select path from files where kind = 'video' and probed = 0")]
    with ThreadPoolExecutor(PROBE_WORKERS) as pool:
        results = pool.map(lambda p: (p, probe(root / p)), pending)
        for done, (path, info) in enumerate(results, start=1):
            conn.execute(
                "update files set duration_s = ?, height = ?, codec = ?, probed = 1 where path = ?",
                (info["duration_s"], info["height"], info["codec"], path),
            )
            if done % 50 == 0:
                conn.commit()
                set_state(conn, "scan", {"phase": "probing", "done": done, "total": len(pending)})
    conn.commit()


def latest_plex_backup(plex_dir: Path = PLEX_DB_DIR) -> Path | None:
    """Find Plex's newest dated library backup (written every few days; safe to read while Plex runs).

    Args:
        plex_dir: Plex's Databases folder.

    Returns:
        Path to the newest backup, or None.
    """
    backups = sorted(plex_dir.glob("com.plexapp.plugins.library.db-20*"))
    return backups[-1] if backups else None


PLEX_VIEWS_SQL = """
select p.file as file, max(s.view_count) as views, max(s.last_viewed_at) as last_viewed
from media_parts p
join media_items m on m.id = p.media_item_id
join metadata_items md on md.id = m.metadata_item_id
join metadata_item_settings s on s.guid = md.guid
where s.view_count > 0
group by p.file
"""


def _apply_plex_views(conn: sqlite3.Connection) -> None:
    backup = latest_plex_backup()
    if backup is None:
        return
    plex = sqlite3.connect(f"file:{backup}?mode=ro&immutable=1", uri=True)
    prefix = str(MEDIA_ROOT) + "/"
    rows = [(views, last, file.removeprefix(prefix)) for file, views, last in plex.execute(PLEX_VIEWS_SQL)]
    library_folders = [root.removeprefix(prefix) for (root,) in plex.execute("select root_path from section_locations")]
    plex.close()
    conn.execute("update files set view_count = 0, last_viewed = null")
    conn.executemany("update files set view_count = ?, last_viewed = ? where path = ?", rows)
    conn.commit()
    set_state(conn, "plex_backup", backup.name)
    set_state(conn, "plex_folders", library_folders)


TAG_RE = re.compile(r"[\[(].*?[\])]|\b(19|20)\d{2}\b|\b(1080p|720p|2160p|4k|bluray|web-?dl|x26[45]|hevc)\b.*", re.I)


def title_key(item: str) -> str:
    """Normalize an item name for duplicate matching: drop year, brackets, quality tags, punctuation.

    Args:
        item: e.g. "Movies/Heat (1995) [1080p]".

    Returns:
        e.g. "heat".
    """
    name = item.split("/", 1)[-1]
    name = re.sub(r"\.(mkv|mp4|avi|m4v)$", "", name, flags=re.I)
    name = TAG_RE.sub(" ", name.replace(".", " ").replace("_", " "))
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


if __name__ == "__main__":
    scan(connect())
