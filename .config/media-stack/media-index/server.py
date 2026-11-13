"""Review server: browse the index, record keep/delete/shrink decisions, move deletions to _trash.

Nothing is deleted here. "Move to trash" renames items into MEDIA_ROOT/_trash (same disk, instant,
reversible) and unmonitors them in Radarr/Sonarr so they aren't downloaded again. "Swap for 1080p"
moves a movie's file to _trash and has Radarr grab a smaller release. Emptying the trash is done by hand.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import unicodedata
import urllib.request
from collections import defaultdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

import arr
import drives
import index
import shrink

PORT = int(os.environ.get("PORT", "8686"))
RESCAN_EVERY_S = 24 * 3600
STATIC = Path(__file__).parent / "static"
TRASH = index.MEDIA_ROOT / index.TRASH_NAME
DECISIONS = {"keep", "delete", "shrink"}

# Bitrate a modern HEVC encode needs for good quality, by vertical resolution (bits/s).
# Rough rule-of-thumb targets; used only to estimate savings, never to encode.
HEVC_TARGET_BPS = [(2000, 15_000_000), (1000, 4_000_000), (700, 2_500_000), (0, 1_200_000)]
EFFICIENT_CODECS = ("hevc", "h265", "av1", "vp9")
MIN_SHRINK_SAVING = 0.3  # only suggest re-encoding when it saves at least 30%

conn = index.connect()
db_lock = threading.Lock()


def hevc_size_estimate(duration_s: float | None, height: int | None) -> float | None:
    """Estimated bytes for this video re-encoded to HEVC at good quality.

    Args:
        duration_s: Video length.
        height: Vertical resolution in pixels.

    Returns:
        Estimated size in bytes, or None when the file couldn't be probed.
    """
    if not duration_s or not height:
        return None
    target_bps = next(bps for min_height, bps in HEVC_TARGET_BPS if height >= min_height)
    return duration_s * target_bps / 8


def shrink_saving(row: dict) -> int:
    """Bytes saved by re-encoding one file, or 0 if it's already efficient or the gain is small.

    Args:
        row: A files row as a dict.

    Returns:
        Estimated bytes saved.
    """
    if row["kind"] != "video" or (row["codec"] or "").startswith(EFFICIENT_CODECS):
        return 0
    estimate = hevc_size_estimate(row["duration_s"], row["height"])
    if estimate is None or estimate > row["size"] * (1 - MIN_SHRINK_SAVING):
        return 0
    return int(row["size"] - estimate)


ITEMS_SQL = """
select f.item, f.category, sum(f.size) as size, count(*) as files,
       sum(case when f.nlink = 1 then f.size else 0 end) as freeable,
       sum(f.duration_s) as duration_s, max(f.height) as height,
       group_concat(distinct f.codec) as codecs, max(f.mtime) as mtime,
       max(f.last_viewed) as last_viewed, sum(f.view_count > 0) as watched_files,
       sum(f.kind = 'video') as video_files, sum(f.kind = 'audio') as audio_files, sum(f.view_count) as plays,
       d.decision, d.note, d.trashed_at
from files f left join decisions d on d.item = f.item
group by f.item
"""


def load_items() -> list[dict]:
    """Aggregate files into items with shrink estimates and duplicate flags.

    Returns:
        One dict per item, biggest first.
    """
    with db_lock:
        items = {r["item"]: dict(r) for r in conn.execute(ITEMS_SQL)}
        files = [dict(r) for r in conn.execute("select item, kind, size, codec, duration_s, height from files")]
        trashed = [dict(r) for r in conn.execute("select * from decisions where trashed_at is not null")]
        swaps = {r["item"]: dict(r) for r in conn.execute("select * from swaps")}
        # _trash is emptied by hand; once a trashed item's files are gone, forget it.
        gone = [t["item"] for t in trashed if not (TRASH / t["item"]).exists()]
        if gone:
            conn.executemany("delete from decisions where item = ?", [(g,) for g in gone])
            conn.commit()
            trashed = [t for t in trashed if t["item"] not in gone]
    for name, item in items.items():
        item["shrink_saving"] = 0
        item["swap"] = swaps.get(name)
    for f in files:
        items[f["item"]]["shrink_saving"] += shrink_saving(f)
    _flag_duplicates(items)
    rows = sorted(items.values(), key=lambda i: i["size"], reverse=True)
    return rows + [_trashed_item(t) for t in trashed if t["item"] not in items]


def library() -> list[dict]:
    """Everything on plex-media plus the titles that live only on a cold drive, each with the drives holding a copy.

    Returns:
        load_items() rows with "drives" and "cold" added, then one row per cold-only title (size from its catalog).
    """
    items = load_items()
    held = {r["item"]: r for r in _drive_data()["items"]}
    on_main = {i["item"] for i in items}
    for it in items:
        it["drives"] = held.get(it["item"], {}).get("drives", {})
        it["cold"] = False
    for r in held.values():
        on_cold = any(d in drives.COLD_DRIVES for d in r["drives"])
        if r["item"] in on_main or not on_cold or r["category"] not in drives.PLEX_SECTIONS:
            continue
        items.append({
            "item": r["item"], "category": r["category"], "size": r["size"], "files": 0, "freeable": 0,
            "video_files": 1, "drives": r["drives"], "cold": True, "shrink_saving": 0,
        })
    travel = _plex_index()["travel"]
    for it in items:
        it["travel"] = drives.TRAVEL_DRIVE in it["drives"] or _plex_key(it["item"]) in travel
    return items


def pick_cold_drive() -> str:
    """The cold drive with the most room: by free space when its catalog recorded it, else the one holding least."""
    info = {d["drive"]: d for d in _drive_data()["drives"]}
    return max(drives.COLD_DRIVES, key=lambda d: (info.get(d, {}).get("free") or 0, -info.get(d, {}).get("size", 0)))


def _flag_duplicates(items: dict[str, dict]) -> None:
    by_title: dict[str, list[str]] = {}
    for name, item in items.items():
        if item["video_files"]:
            by_title.setdefault(index.title_key(name), []).append(name)
        elif item["audio_files"] and item["category"] == index.MUSIC_CATEGORY:
            # Same artist and song in any album: music/<Artist>/<Album>/<Song>.mp3
            parts = name.split("/")
            by_title.setdefault("♪" + index.title_key(f"{parts[1]} {Path(parts[-1]).stem}"), []).append(name)
    for title, names in by_title.items():
        for name in names:
            items[name]["duplicates"] = [n for n in names if n != name] if title else []


def _trashed_item(decision: dict) -> dict:
    """Items in _trash are no longer indexed; show them from the decisions table."""
    return {
        **decision,
        "category": decision["item"].split("/")[0],
        "size": decision["size"] or 0,
        "files": 0,
        "shrink_saving": 0,
    }


# Torrents in downloads/ are hardlinked into the libraries, so count those files only once (in the library).
CATEGORIES_SQL = """
select category, sum(case when category = 'downloads' and nlink > 1 then 0 else size end) as size
from files group by category order by size desc
"""


def summary() -> dict:
    """Totals for the header: disk use, per-category sizes, decision totals, scan state.

    Returns:
        JSON-ready dict.
    """
    items = load_items()
    disk = shutil.disk_usage(index.MEDIA_ROOT)
    with db_lock:
        categories = [tuple(r) for r in conn.execute(CATEGORIES_SQL)]
        scan_state = index.get_state(conn, "scan", {})
        plex_backup = index.get_state(conn, "plex_backup")
        plex_folders = index.get_state(conn, "plex_folders", [])
    return {
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "categories": categories,
        "decided": _decision_totals(items),
        "shrinkable": sum(i["shrink_saving"] for i in items if not i.get("trashed_at")),
        "trash": _dir_size(TRASH),
        "scan": scan_state,
        "plex_backup": plex_backup,
        "plex_folders": plex_folders,
    }


SHRINK_QUEUE_SQL = """
select d.item, d.note, f.path, f.kind, f.size, f.nlink, f.codec, f.duration_s, f.height
from decisions d join files f on f.item = d.item
where d.decision = 'shrink' and d.trashed_at is null
order by d.item, f.path
"""


def shrink_queue() -> list[dict]:
    """Titles marked shrink with the files worth re-encoding, for the host-side encoder (shrink.py).

    Returns:
        One dict per title: item, note, files (path, size, nlink, codec, duration_s, height, saving).
    """
    with db_lock:
        rows = [dict(r) for r in conn.execute(SHRINK_QUEUE_SQL)]
    titles: dict[str, dict] = {}
    for row in rows:
        saving = shrink_saving(row)
        if saving > 0:
            title = titles.setdefault(row["item"], {"item": row["item"], "note": row["note"], "files": []})
            keep = ("path", "size", "nlink", "codec", "duration_s", "height")
            title["files"].append({**{k: row[k] for k in keep}, "saving": saving})
    return list(titles.values())


def _decision_totals(items: list[dict]) -> dict:
    totals = {d: {"items": 0, "size": 0} for d in (*DECISIONS, "undecided", "trashed")}
    for item in items:
        key = "trashed" if item.get("trashed_at") else item.get("decision") or "undecided"
        totals[key]["items"] += 1
        totals[key]["size"] += item["shrink_saving"] if key == "shrink" else item["size"]
    return totals


def _dir_size(path: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        total += sum((Path(dirpath) / f).stat().st_size for f in files)
    return total


def set_decision(item: str, decision: str | None, note: str = "") -> None:
    """Record or clear a decision for an item.

    Args:
        item: Item key.
        decision: keep | delete | shrink, or None to clear.
        note: Free-text note.

    Raises:
        ValueError: On an unknown decision.
    """
    if decision is not None and decision not in DECISIONS:
        raise ValueError(f"Unknown decision: {decision}")
    with db_lock:
        if decision is None:
            conn.execute("delete from decisions where item = ? and trashed_at is null", (item,))
        else:
            conn.execute(
                "insert into decisions (item, decision, note, decided_at) values (?, ?, ?, ?)"
                " on conflict(item) do update set decision = excluded.decision, note = excluded.note,"
                " decided_at = excluded.decided_at",
                (item, decision, note, time.time()),
            )
        conn.commit()


def move_to_trash() -> list[dict]:
    """Move every item marked delete into _trash and unmonitor it in Radarr/Sonarr.

    Returns:
        One result dict per item: item, ok, message.
    """
    with db_lock:
        pending = [
            r["item"]
            for r in conn.execute("select item from decisions where decision = 'delete' and trashed_at is null")
        ]
    results = [_trash_one(item) for item in pending]
    threading.Thread(target=run_scan, daemon=True).start()
    return results


def _trash_one(item: str) -> dict:
    src = index.MEDIA_ROOT / item
    if not src.exists():
        return {"item": item, "ok": False, "message": "not found on disk"}
    size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) if src.is_dir() else src.stat().st_size
    unmonitored = arr.unmonitor(src)
    dest = TRASH / item
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    with db_lock:
        conn.execute("update decisions set trashed_at = ?, size = ? where item = ?", (time.time(), size, item))
        conn.commit()
    return {"item": item, "ok": True, "message": unmonitored or "moved"}


def restore(item: str) -> dict:
    """Move an item back from _trash to where it was. Monitoring in Radarr/Sonarr is not turned back on.

    Args:
        item: Item key.

    Returns:
        Result dict: item, ok, message.
    """
    src, dest = TRASH / item, index.MEDIA_ROOT / item
    if not src.exists() or dest.exists():
        return {"item": item, "ok": False, "message": "not in trash, or something is already at the original path"}
    src.rename(dest)
    with db_lock:
        conn.execute("delete from decisions where item = ?", (item,))
        conn.commit()
    threading.Thread(target=run_scan, daemon=True).start()
    return {"item": item, "ok": True, "message": "restored (re-monitor it in Radarr/Sonarr if you want upgrades)"}


def cold_moves() -> list[dict]:
    """Titles marked to move to or from a cold drive, newest first; done ones drop off the list after a week."""
    sql = "select * from cold_moves where status != 'done' or updated_at > ? order by updated_at desc"
    with db_lock:
        return [dict(r) for r in conn.execute(sql, (time.time() - 7 * 86400,))]


def mark_cold_move(item: str, drive: str, direction: str | None) -> dict:
    """Mark a title to move out to a cold drive or back from one (drives.py queue does it), or unmark it.

    Args:
        item: Item key, e.g. "movies/Aquaman (2018)".
        drive: One of drives.COLD_DRIVES, or "" to pick: the roomiest for "out", the one holding the title for "back".
        direction: out | back, or None to unmark (not while it's running).

    Returns:
        {"ok", "message", "drive"}.
    """
    if direction is None:
        with db_lock:
            conn.execute("delete from cold_moves where item = ? and status != 'running'", (item,))
            conn.commit()
        return {"ok": True, "message": "unmarked"}
    held = next((r["drives"] for r in _drive_data()["items"] if r["item"] == item), {})
    if not drive:
        drive = pick_cold_drive() if direction == "out" else next((d for d in drives.COLD_DRIVES if d in held), "")
    if drive not in drives.COLD_DRIVES or direction not in ("out", "back") or ".." in Path(item).parts:
        return {"ok": False, "message": "unknown drive or direction"}
    on_main = (index.MEDIA_ROOT / item).exists()
    if direction == "out":
        with db_lock:
            # fetchall, not fetchone: an unfinished read keeps a lock that makes the insert below fail during a scan
            rows = conn.execute("select decision, note from decisions where item = ?", (item,)).fetchall()
            decision = rows[0] if rows else None
        if not on_main:
            return {"ok": False, "message": "not on plex-media"}
        if decision and decision["decision"] == "keep":
            return {"ok": False, "message": f"marked Keep ({decision['note'] or 'no note'}); clear that first"}
    elif on_main:
        return {"ok": False, "message": "already on plex-media"}
    elif drive not in held:
        return {"ok": False, "message": f"not in {drive}'s catalog"}
    with db_lock:
        conn.execute(
            "insert or replace into cold_moves values (?, ?, ?, 'queued', '', ?)", (item, drive, direction, time.time())
        )
        conn.commit()
    return {"ok": True, "message": f"queued; moves when {drive} is plugged in", "drive": drive}


def cold_move_status(item: str, status: str, message: str) -> dict:
    """Progress from drives.py queue. A finished move changes plex-media, so rescan it."""
    with db_lock:
        conn.execute(
            "update cold_moves set status = ?, message = ?, updated_at = ? where item = ?",
            (status, message, time.time(), item),
        )
        conn.commit()
    if status == "done":
        threading.Thread(target=run_scan, daemon=True).start()
    return {"ok": True}


def shrink_finish(rel: str, replace: bool) -> dict:
    """Finish a host re-encode for shrink.py, which macOS doesn't let change the disk under launchd.

    Args:
        rel: The original file, relative to MEDIA_ROOT.
        replace: Original to _trash and encode into its place; otherwise delete the encode.

    Returns:
        {"ok", "message"}.
    """
    src = (index.MEDIA_ROOT / rel).resolve()
    if index.MEDIA_ROOT not in src.parents or TRASH in src.parents:
        return {"ok": False, "message": "path outside the library"}
    return shrink.swap_in_encode(index.MEDIA_ROOT, rel, replace)


def swap_options(item: str) -> dict:
    """Smaller English 1080p releases Radarr can find for a movie.

    Args:
        item: Item key, e.g. "movies/First Man (2018)".

    Returns:
        {"ok", "message", "current_size", "options"}.
    """
    movie = arr.find_by_path("radarr", index.MEDIA_ROOT / item)
    if not movie or not movie.get("movieFile"):
        return {"ok": False, "message": "Radarr doesn't manage a file for this title", "options": []}
    with db_lock:
        duration_s = conn.execute("select sum(duration_s) from files where item = ?", (item,)).fetchone()[0]
    hours = (duration_s or movie.get("runtime", 0) * 60) / 3600
    options = arr.swap_options(movie, hours)
    message = "" if options else "No smaller English 1080p release with enough seeders right now"
    return {"ok": True, "message": message, "current_size": movie["movieFile"]["size"], "options": options}


def swap(item: str, release: dict) -> dict:
    """Move a movie's file to _trash, let Radarr notice it's missing, then grab the chosen release.

    Args:
        item: Item key.
        release: One entry from swap_options (guid, indexerId, title, size).

    Returns:
        Result dict: ok, message.
    """
    movie = arr.find_by_path("radarr", index.MEDIA_ROOT / item)
    if not movie or not movie.get("movieFile"):
        return {"ok": False, "message": "Radarr doesn't manage a file for this title"}
    original = index.MEDIA_ROOT / item / movie["movieFile"]["relativePath"]
    shared = original.stat().st_nlink > 1
    dest = TRASH / item / original.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    original.rename(dest)
    arr.rescan_movie(movie["id"])
    arr.grab(release["guid"], release["indexerId"])
    _record_swap(item, dest, release)
    threading.Thread(target=run_scan, daemon=True).start()
    note = " The old file is still seeding in qBittorrent; remove that torrent to free its space." if shared else ""
    return {"ok": True, "message": f"Original moved to _trash; Radarr is downloading {release['title']}.{note}"}


def _record_swap(item: str, original: Path, release: dict) -> None:
    with db_lock:
        conn.execute(
            "insert or replace into swaps values (?, ?, ?, ?, ?, ?)",
            (item, str(original), original.stat().st_size, release["title"], release["size"], time.time()),
        )
        conn.commit()


# Posters for the grid view, cached by item so titles moved to a cold drive (and dropped from Radarr/Sonarr) keep
# theirs. Sources, in order: Radarr/Sonarr, Plex artwork, Kavita's series cover (manga), a cover image in the
# title's own folder or inside its first audio file (audiobooks, podcasts, YouTube, music albums), TMDB by title and
# year. warm_posters fetches every one at startup and daily.
POSTERS = index.DB_PATH.parent / "posters"
POSTER_W, POSTER_H = 250, 375
PLEX = os.environ.get("PLEX_URL", "http://localhost:32400")
KAVITA = os.environ.get("KAVITA_URL", "http://localhost:5003")
_kavita_cache: dict = {"at": 0.0, "series": {}}
TMDB_IMAGES = "https://image.tmdb.org/t/p/w342"
COVER_NAMES = ("cover", "folder", "poster", "show", "front", "album")
COVER_TYPES = ("*.jpg", "*.jpeg", "*.png")
MISS_RETRY_S = 6 * 3600
_arr_paths: dict = {"at": 0.0, "paths": {}}
_plex_cache: dict = {"at": 0.0, "by_item": {}, "by_key": {}, "travel": set(), "sections": {}, "travel_coll": {}}
PLEX_TYPE = {"movie": 1, "show": 2}  # Plex metadata type codes, for creating a collection
_misses: dict[str, float] = {}


def nfc(text: str) -> str:
    """Unicode-composed form: macOS names files decomposed ("Déjà" as e + ́), Radarr and Plex keep them composed."""
    return unicodedata.normalize("NFC", text)


def _poster_file(item: str) -> Path:
    return POSTERS / (hashlib.sha1(item.encode()).hexdigest() + ".jpg")


def _plex_key(item: str) -> tuple[str, str]:
    """(category, normalized title) — how a Plex entry without a file path is matched to a library folder."""
    return item.split("/")[0], index.title_key(item)


def _arr_index() -> dict[str, tuple[str, str, int]]:
    """Library path (NFC) -> (API base, key, id) for everything Radarr and Sonarr manage; refreshed every 10 minutes."""
    if time.time() - _arr_paths["at"] > 600:
        paths = {}
        for base, kind, key in arr.ARR.values():
            for entry in arr.request(f"{base}/{kind}", key):
                paths[nfc(entry["path"])] = (base, key, entry["id"])
        _arr_paths.update(at=time.time(), paths=paths)
    return _arr_paths["paths"]


def _plex_get(path: str) -> dict:
    """A Plex API answer as JSON; {} when Plex is down or the token is missing."""
    token = shrink.read_env().get("HOMEPAGE_VAR_PLEX_TOKEN", "")
    if not token:
        return {}
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"{PLEX}{path}{sep}X-Plex-Token={token}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()).get("MediaContainer", {})
    except (OSError, ValueError):
        return {}


def _plex_index() -> dict:
    """Plex artwork and Travel-collection membership for every title, refreshed every 10 minutes.

    Returns:
        {"by_item": item -> {"thumb", "rk"} (movies, matched by file path), "by_key": _plex_key -> the same (shows,
        artists: matched by title), "travel": set of _plex_keys in a collection called Travel,
        "sections": folder -> {"key", "type"}, "travel_coll": folder -> that section's Travel collection ratingKey}.
    """
    if time.time() - _plex_cache["at"] < 600:
        return _plex_cache
    found: dict = {"by_item": {}, "by_key": {}, "travel": set(), "sections": {}, "travel_coll": {}}
    root = str(index.MEDIA_ROOT) + "/"
    for section in _plex_get("/library/sections").get("Directory", []):
        paths = [loc["path"] for loc in section.get("Location", []) if loc["path"].startswith(root)]
        folder = paths[0][len(root):] if paths else ""
        if folder:
            found["sections"][folder] = {"key": section["key"], "type": PLEX_TYPE.get(section["type"], 1)}
            _plex_section(section["key"], folder, root, found)
    if found["by_key"] or _plex_cache["at"] == 0:  # keep the old index while Plex is down
        _plex_cache.update(at=time.time(), **found)
    return _plex_cache


def _plex_section(key: str, folder: str, root: str, found: dict) -> None:
    """One library section's artwork and rating keys into found, plus its Travel collection and that one's titles."""
    for entry in _plex_get(f"/library/sections/{key}/all").get("Metadata", []):
        thumb = entry.get("thumb")
        if not thumb:
            continue
        hit = {"thumb": thumb, "rk": entry["ratingKey"]}
        found["by_key"].setdefault((folder, index.title_key(entry["title"])), hit)
        files = (part.get("file", "") for media in entry.get("Media", []) for part in media.get("Part", []))
        for file in files:
            if file.startswith(root):
                found["by_item"].setdefault(nfc(index.item_for(file[len(root):])[0]), hit)
    for coll in _plex_get(f"/library/sections/{key}/collections").get("Metadata", []):
        if coll["title"].lower() == "travel":
            found["travel_coll"][folder] = coll["ratingKey"]
            for entry in _plex_get(f"/library/collections/{coll['ratingKey']}/children").get("Metadata", []):
                found["travel"].add((folder, index.title_key(entry["title"])))


def _plex_entry(item: str) -> dict | None:
    plex = _plex_index()
    return plex["by_item"].get(nfc(item)) or plex["by_key"].get(_plex_key(item))


def _plex_call(path: str, method: str) -> None:
    """A Plex write (PUT/POST/DELETE); OSError when it fails."""
    token = shrink.read_env().get("HOMEPAGE_VAR_PLEX_TOKEN", "")
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"{PLEX}{path}{sep}X-Plex-Token={token}", method=method)
    with urllib.request.urlopen(req, timeout=60):
        pass


def set_travel(item: str, on: bool) -> dict:
    """Put a title into (or take it out of) its library's Plex collection "Travel": the 🧳 mark, and the list that
    gets copied to the stick."""
    entry, folder = _plex_entry(item), item.split("/")[0]
    plex = _plex_index()
    section, coll = plex["sections"].get(folder), plex["travel_coll"].get(folder)
    if not entry or not section:
        return {"ok": False, "message": "not in Plex right now (a cold title has to come back first)"}
    machine = _plex_get("/identity").get("machineIdentifier", "")
    uri = quote(f"server://{machine}/com.plexapp.plugins.library/library/metadata/{entry['rk']}", safe="")
    try:
        if on and coll:
            _plex_call(f"/library/collections/{coll}/items?uri={uri}", "PUT")
        elif on:
            query = f"type={section['type']}&title=Travel&smart=0&sectionId={section['key']}&uri={uri}"
            _plex_call(f"/library/collections?{query}", "POST")
        elif coll:
            _plex_call(f"/library/collections/{coll}/children/{entry['rk']}?excludeAllLeaves=1", "DELETE")
    except OSError as err:
        return {"ok": False, "message": f"Plex refused: {err}"}
    _plex_cache["at"] = 0  # the next items load re-reads the collections
    return {"ok": True, "message": "on the travel list" if on else "off the travel list"}


def _fetch(url: str, headers: dict | None = None, body: bytes | None = None) -> bytes | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, headers or {}), timeout=30) as resp:
            return resp.read()
    except OSError:
        return None


def _poster_from_arr(item: str) -> bytes | None:
    found = _arr_index().get(nfc(str(index.MEDIA_ROOT / item)))
    if not found:
        return None
    base, key, arr_id = found
    return _fetch(f"{base}/mediacover/{arr_id}/poster-250.jpg", {"X-Api-Key": key})


def _poster_from_plex(item: str) -> bytes | None:
    hit = _plex_entry(item)
    if not hit:
        return None
    thumb = hit["thumb"]
    token = shrink.read_env().get("HOMEPAGE_VAR_PLEX_TOKEN", "")
    return _fetch(f"{PLEX}/photo/:/transcode?width={POSTER_W}&height={POSTER_H}&minSize=1&upscale=1"
                  f"&url={quote(thumb)}&X-Plex-Token={token}")


def _cover_on_disk(item: str) -> bytes | None:
    """A cover image kept next to the files (cover.jpg, folder.jpg, show.jpg, any image up to three levels down), else
    the art embedded in the first audio file, scaled to poster width with ffmpeg. For a song, its album's cover."""
    path = index.MEDIA_ROOT / item
    if not path.exists():  # not on this disk (cold): never fall back to the parent, or every cold show would share one
        return None
    if path.is_file() and not item.startswith(index.MUSIC_CATEGORY + "/"):  # a loose book: only its own embedded art
        return _scaled(path, _poster_file("art:" + item))
    folder = path if path.is_dir() else path.parent  # a song: its album folder
    cached = _poster_file("dir:" + str(folder.relative_to(index.MEDIA_ROOT)))
    if cached.exists():
        return cached.read_bytes()
    found = [p for depth in ("", "*/", "*/*/", "*/*/*/") for pat in COVER_TYPES for p in folder.glob(depth + pat)]
    rank = {name: i for i, name in enumerate(COVER_NAMES)}
    if found:
        return _scaled(min(found, key=lambda p: (rank.get(p.stem.lower(), len(rank)), len(p.parts), p.name)), cached)
    audio = sorted(p for p in folder.rglob("*") if index.kind_for(p.name) == "audio")
    return _scaled(audio[0], cached) if audio else None


def _scaled(source: Path, dest: Path) -> bytes | None:
    """An image, or the cover art inside an audio file, as a poster-width JPEG at dest; None when there is none."""
    POSTERS.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-an", "-frames:v", "1", "-vf", f"scale={POSTER_W}:-2",
           "-q:v", "4", "-f", "mjpeg", str(dest)]
    done = subprocess.run(cmd, capture_output=True)
    return dest.read_bytes() if done.returncode == 0 and dest.exists() and dest.stat().st_size else None


def _kavita_series() -> dict[str, int]:
    """Kavita's series ids by normalized name, refreshed every 10 minutes; {} without KAVITA_API_KEY or when down."""
    key = shrink.read_env().get("KAVITA_API_KEY", "")
    if key and time.time() - _kavita_cache["at"] > 600:
        try:
            login = arr.request(f"{KAVITA}/api/Plugin/authenticate?apiKey={key}&pluginName=media-index", "", {}, "POST")
            everything = json.dumps({"statements": [], "combination": 1, "limitTo": 0}).encode()
            headers = {"Authorization": f"Bearer {login['token']}", "Content-Type": "application/json"}
            found = json.loads(_fetch(f"{KAVITA}/api/series/all-v2", headers, everything) or b"[]")
        except (OSError, ValueError, KeyError):
            found = []
        _kavita_cache.update(at=time.time(), series={index.title_key(row["name"]): row["id"] for row in found})
    return _kavita_cache["series"]


def _poster_from_kavita(item: str) -> bytes | None:
    """A manga series' cover from Kavita (the one its reader shows), matched by the series folder's name."""
    if not item.startswith("manga/"):
        return None
    series_id = _kavita_series().get(index.title_key(item.rsplit("/", 1)[-1]))
    if series_id is None:
        return None
    key = shrink.read_env().get("KAVITA_API_KEY", "")
    return _fetch(f"{KAVITA}/api/image/series-cover?seriesId={series_id}&apiKey={key}")


def _poster_from_tmdb(item: str) -> bytes | None:
    """TMDB's poster for a movie or show folder, by title and year; needs TMDB_API_KEY in the environment."""
    key = shrink.read_env().get("TMDB_API_KEY", "")
    category, name = item.split("/", 1) if "/" in item else (item, item)
    if not key or category not in drives.PLEX_SECTIONS:
        return None
    year = re.search(r"\b(19|20)\d{2}\b", name)
    title = re.split(r"[\[(]|\b(19|20)\d{2}\b|\b\d{3,4}p\b", name)[0].replace(".", " ").strip(" -_")
    kind, year_param = ("movie", "year") if category == "movies" else ("tv", "first_air_date_year")
    query = urlencode({"api_key": key, "query": title, **({year_param: year.group()} if year else {})})
    raw = _fetch(f"https://api.themoviedb.org/3/search/{kind}?{query}")
    results = json.loads(raw).get("results", []) if raw else []
    path = next((r["poster_path"] for r in results if r.get("poster_path")), None)
    return _fetch(TMDB_IMAGES + path) if path else None


def poster(item: str) -> bytes | None:
    """A title's poster (250 px wide JPEG) from the cache or the first source that has one, else None.

    A miss is remembered for six hours so a wall of unposterable titles doesn't ask Plex and TMDB on every scroll.
    """
    cached = _poster_file(item)
    try:
        return cached.read_bytes()
    except FileNotFoundError:
        pass
    if time.time() - _misses.get(item, 0) < MISS_RETRY_S:
        return None
    for source in (_poster_from_arr, _poster_from_plex, _poster_from_kavita, _cover_on_disk, _poster_from_tmdb):
        data = source(item)
        if data:
            POSTERS.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(data)
            return data
    _misses[item] = time.time()
    return None


def warm_posters() -> None:
    """Cache the poster of every title Radarr/Sonarr manage, so it survives a later move to cold storage."""
    root = str(index.MEDIA_ROOT) + "/"
    for path in list(_arr_index()):
        if path.startswith(root) and not _poster_file(path[len(root):]).exists():
            poster(path[len(root):])
    _poster_cold_titles()


def _poster_cold_titles() -> None:
    """Posters for titles moved to cold storage before they were cached: find each in the import-list exclusion
    drives.py added when it dropped the title, and save the poster Radarr/Sonarr's lookup links to."""
    sonarr = ("sonarr", "importlistexclusion", "title", "tvdb")
    apps = {"movies": ("radarr", "exclusions", "movieTitle", "tmdb"), "tv": sonarr, "anime": sonarr}
    for category, (app, endpoint, title_field, id_kind) in apps.items():
        base, kind, key = arr.ARR[app]
        wanted = {
            index.title_key(r["item"]): r["item"] for r in _drive_data()["items"]
            if r["category"] == category and drives.MAIN_DRIVE not in r["drives"]
            and not _poster_file(r["item"]).exists()
        }
        for exclusion in arr.request(f"{base}/{endpoint}", key) if wanted else []:
            item = wanted.get(index.title_key(exclusion[title_field]))
            if not item:
                continue
            found = arr.request(f"{base}/{kind}/lookup?term={id_kind}:{exclusion[id_kind + 'Id']}", key)
            url = next((f.get("remotePoster") for f in found if f.get("remotePoster")), None)
            if url:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    POSTERS.mkdir(parents=True, exist_ok=True)
                    _poster_file(item).write_bytes(resp.read())


scan_lock = threading.Lock()

# Drive manifests (drives.py catalogs) merged into title -> {drive: bytes}; rebuilt when any manifest changes.
DRIVE_ITEMS_MAX = 400
_drive_cache: dict = {"key": None, "items": [], "drives": []}
drive_lock = threading.Lock()


def _drive_data() -> dict:
    """Catalogued drives and every title they hold, from the manifests on disk (cached by their mtimes)."""
    names = drives.drives()
    key = tuple((d, drives.catalog_path(d).stat().st_mtime) for d in names)
    with drive_lock:
        if _drive_cache["key"] == key:
            return _drive_cache
        held: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        summary = []
        for d in names:
            entries = drives.load(d)
            folders: dict[str, int] = defaultdict(int)
            for e in entries:
                held[e.item][d] += e.size
                folders[e.path.split("/", 1)[0]] += e.size
            summary.append({
                "drive": d, "files": len(entries), "size": sum(e.size for e in entries),
                "catalogued": drives.catalog_path(d).stat().st_mtime, "main": d == drives.MAIN_DRIVE,
                "cold": d in drives.COLD_DRIVES, "travel": d == drives.TRAVEL_DRIVE, **drives.usage(d),
                "scopes": drives.BACKUPS.get(d, []), "folders": sorted(folders.items(), key=lambda kv: -kv[1]),
            })
        items = [
            {"item": item, "category": index.item_for(item)[1], "drives": dict(by), "size": max(by.values())}
            for item, by in held.items()
        ]
        items.sort(key=lambda r: -r["size"])
        _drive_cache.update(key=key, items=items, drives=summary)
        return _drive_cache


def drive_items(q: str, drive: str, only: bool) -> dict:
    """Titles across all catalogued drives matching a search.

    Args:
        q: Case-insensitive text the title must contain ("" for all).
        drive: Only titles present on this drive ("" for any).
        only: Only titles held by a single drive (nothing else has a copy).

    Returns:
        {"total", "total_size", "items": first DRIVE_ITEMS_MAX rows, largest first}.
    """
    needle = q.lower()
    rows = [
        r for r in _drive_data()["items"]
        if (not needle or needle in r["item"].lower()) and (not drive or drive in r["drives"])
        and (not only or len(r["drives"]) == 1)
    ]
    return {"total": len(rows), "total_size": sum(r["size"] for r in rows), "items": rows[:DRIVE_ITEMS_MAX]}


def run_scan() -> None:
    """Run one scan unless another is already running."""
    if not scan_lock.acquire(blocking=False):
        return
    try:
        index.scan(index.connect())
    finally:
        scan_lock.release()


def scan_forever() -> None:
    """Scan and cache posters at startup and then daily."""
    while True:
        run_scan()
        try:
            warm_posters()
        except OSError as err:  # Radarr/Sonarr down: try again tomorrow, posters also load on demand
            print(f"poster cache: {err}")
        time.sleep(RESCAN_EVERY_S)


class Handler(BaseHTTPRequestHandler):
    """JSON API plus the single static page."""

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        url = urlparse(self.path)
        if url.path == "/":
            self._send(HTTPStatus.OK, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/summary":
            self._json(summary())
        elif url.path == "/api/items":
            self._json(library())
        elif url.path == "/api/files":
            self._json(_files(parse_qs(url.query).get("item", [""])[0]))
        elif url.path == "/api/swap-options":
            self._json(swap_options(parse_qs(url.query).get("item", [""])[0]))
        elif url.path == "/api/shrink-queue":
            self._json(shrink_queue())
        elif url.path == "/api/audio":
            self._audio(parse_qs(url.query).get("item", [""])[0])
        elif url.path == "/api/drives":
            self._json(_drive_data()["drives"])
        elif url.path == "/api/poster":
            image = poster(parse_qs(url.query).get("item", [""])[0])
            if image:
                self._send(HTTPStatus.OK, image, "image/jpeg", cache=True)
            else:
                self._send(HTTPStatus.NOT_FOUND, b"no poster", "text/plain")
        elif url.path == "/api/cold-moves":
            self._json(cold_moves())
        elif url.path == "/api/drive-items":
            qs = parse_qs(url.query)
            self._json(drive_items(qs.get("q", [""])[0], qs.get("drive", [""])[0], qs.get("only", ["0"])[0] == "1"))
        else:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        path = urlparse(self.path).path
        if path == "/api/decision":
            set_decision(body["item"], body.get("decision"), body.get("note", ""))
            self._json({"ok": True})
        elif path == "/api/trash":
            self._json(move_to_trash())
        elif path == "/api/restore":
            self._json(restore(body["item"]))
        elif path == "/api/swap":
            self._json(swap(body["item"], body["release"]))
        elif path == "/api/shrink-finish":
            self._json(shrink_finish(body["path"], bool(body.get("replace"))))
        elif path == "/api/cold-move":
            self._json(mark_cold_move(body["item"], body.get("drive", ""), body.get("direction")))
        elif path == "/api/travel":
            self._json(set_travel(body["item"], bool(body.get("on"))))
        elif path == "/api/cold-moves/status":
            self._json(cold_move_status(body["item"], body["status"], body.get("message", "")))
        elif path == "/api/scan":
            threading.Thread(target=run_scan, daemon=True).start()
            self._json({"ok": True})
        else:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

    def _audio(self, item: str) -> None:
        """Stream a song for the page's preview player, with Range support so the browser can seek."""
        path = (index.MEDIA_ROOT / item).resolve()
        if not item or index.kind_for(path.name) != "audio" or index.MEDIA_ROOT.resolve() not in path.parents:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        ranged = (self.headers.get("Range") or "").removeprefix("bytes=")
        if ranged:
            first, _, last = ranged.partition("-")
            start, end = int(first or 0), min(int(last or end), end)
        self.send_response(HTTPStatus.PARTIAL_CONTENT if ranged else HTTPStatus.OK)
        self.send_header("Content-Type", "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/" + path.suffix[1:])
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if ranged:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))

    def _json(self, value: object) -> None:
        self._send(HTTPStatus.OK, json.dumps(value).encode(), "application/json")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str, cache: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if cache:
            self.send_header("Cache-Control", "max-age=86400")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        """Quiet: the container log is for scan errors, not every request."""


def _files(item: str) -> list[dict]:
    with db_lock:
        rows = [dict(r) for r in conn.execute("select * from files where item = ? order by path", (item,))]
    for r in rows:
        r["shrink_saving"] = shrink_saving(r)
    return rows


if __name__ == "__main__":
    threading.Thread(target=scan_forever, daemon=True).start()
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
