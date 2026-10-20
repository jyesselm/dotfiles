"""Review server: browse the index, record keep/delete/shrink decisions, move deletions to _trash.

Nothing is deleted here. "Move to trash" renames items into MEDIA_ROOT/_trash (same disk, instant,
reversible) and unmonitors them in Radarr/Sonarr so they aren't downloaded again. Emptying the
trash is done by hand.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import index

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

ARR = {
    "radarr": ("http://radarr:7878/api/v3", "movie", os.environ.get("RADARR_KEY", "")),
    "sonarr": ("http://sonarr:8989/api/v3", "series", os.environ.get("SONARR_KEY", "")),
}

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
       sum(f.kind = 'video') as video_files,
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
    for item in items.values():
        item["shrink_saving"] = 0
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


# Torrents in downloading/ are hardlinked into the libraries, so count those files only once (in the library).
CATEGORIES_SQL = """
select category, sum(case when category = 'downloading' and nlink > 1 then 0 else size end) as size
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
    unmonitored = unmonitor(src)
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


def unmonitor(path: Path) -> str:
    """Unmonitor the Radarr movie or Sonarr series stored at path, so it isn't downloaded again.

    Args:
        path: Absolute item path (the same inside every container).

    Returns:
        A short message, or "" when no app manages the path.
    """
    for app, (base, kind, key) in ARR.items():
        if not key:
            continue
        try:
            entries = _arr(f"{base}/{kind}", key)
            match = next((e for e in entries if e.get("path") == str(path)), None)
            if match:
                _arr(f"{base}/{kind}/editor", key, {f"{kind}Ids": [match["id"]], "monitored": False})
                return f"moved; unmonitored in {app}"
        except OSError as err:
            return f"moved; {app} unreachable ({err})"
    return ""


def _arr(url: str, key: str, body: dict | None = None) -> list[dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="PUT" if body else "GET")
    req.add_header("X-Api-Key", key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read() or b"[]")


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
        elif path == "/api/scan":
            threading.Thread(target=run_scan, daemon=True).start()
            self._json({"ok": True})
        else:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

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
