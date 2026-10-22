"""Review server: browse the index, record keep/delete/shrink decisions, move deletions to _trash.

Nothing is deleted here. "Move to trash" renames items into MEDIA_ROOT/_trash (same disk, instant,
reversible) and unmonitors them in Radarr/Sonarr so they aren't downloaded again. "Swap for 1080p"
moves a movie's file to _trash and has Radarr grab a smaller release. Emptying the trash is done by hand.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import arr
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
    for name, item in items.items():
        item["shrink_saving"] = 0
        item["swap"] = swaps.get(name)
    for f in files:
        items[f["item"]]["shrink_saving"] += shrink_saving(f)
    _flag_duplicates(items)
    rows = sorted(items.values(), key=lambda i: i["size"], reverse=True)
    return rows + [_trashed_item(t) for t in trashed if t["item"] not in items]


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


scan_lock = threading.Lock()


def run_scan() -> None:
    """Run one scan unless another is already running."""
    if not scan_lock.acquire(blocking=False):
        return
    try:
        index.scan(index.connect())
    finally:
        scan_lock.release()


def scan_forever() -> None:
    """Scan at startup and then daily."""
    while True:
        run_scan()
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
            self._json(load_items())
        elif url.path == "/api/files":
            self._json(_files(parse_qs(url.query).get("item", [""])[0]))
        elif url.path == "/api/swap-options":
            self._json(swap_options(parse_qs(url.query).get("item", [""])[0]))
        elif url.path == "/api/shrink-queue":
            self._json(shrink_queue())
        elif url.path == "/api/audio":
            self._audio(parse_qs(url.query).get("item", [""])[0])
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

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
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
