"""Small Radarr/Sonarr API client: find what an app manages at a path, unmonitor, search and grab releases."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

ARR = {
    "radarr": ("http://radarr:7878/api/v3", "movie", os.environ.get("HOMEPAGE_VAR_RADARR_KEY", "")),
    "sonarr": ("http://sonarr:8989/api/v3", "series", os.environ.get("HOMEPAGE_VAR_SONARR_KEY", "")),
}
RADARR_BASE, _, RADARR_KEY = ARR["radarr"]

SWAP_QUALITIES = {"Bluray-1080p", "WEBDL-1080p", "WEBRip-1080p"}
MIN_SEEDERS = 3
MAX_SWAP_FRACTION = 0.7  # a swap must be at least 30% smaller than what's on disk
MIN_BYTES_PER_HOUR = 1.0e9  # below ~1 GB/hour a 1080p movie is usually a visibly poor micro-encode
SWAP_OPTIONS = 6
# Rejections that only say "you already have a file"; anything else (language, hardcoded subs, seeders) disqualifies.
UPGRADE_ONLY_REJECTIONS = ("does not allow upgrades", "meets cutoff", "not an upgrade", "Not an upgrade")
FOREIGN_TITLE_RE = re.compile(r"[Ѐ-ӿ]|\b(ita|vff|truefrench|hin|rus|ukr|lat|castellano)\b", re.I)
HEVC_RE = re.compile(r"x265|hevc|h\.?265", re.I)


def request(url: str, key: str, body: dict | None = None, method: str | None = None) -> object:
    """Call an *arr API and return the decoded JSON.

    Args:
        url: Full endpoint URL.
        key: API key.
        body: JSON body; when given the default method is PUT.
        method: Override the HTTP method.

    Returns:
        Decoded JSON (list or dict).
    """
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("PUT" if body is not None else "GET"))
    req.add_header("X-Api-Key", key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read() or b"[]")


def find_by_path(app: str, path: Path) -> dict | None:
    """The movie/series an app stores at path, or None.

    Args:
        app: "radarr" or "sonarr".
        path: Absolute item path (identical inside every container).

    Returns:
        The app's record, or None.
    """
    base, kind, key = ARR[app]
    if not key:
        return None
    entries = request(f"{base}/{kind}", key)
    return next((e for e in entries if e.get("path") == str(path)), None)


def unmonitor(path: Path) -> str:
    """Unmonitor the Radarr movie or Sonarr series stored at path, so it isn't downloaded again.

    Args:
        path: Absolute item path.

    Returns:
        A short message, or "" when no app manages the path.
    """
    for app, (base, kind, key) in ARR.items():
        try:
            match = find_by_path(app, path)
            if match:
                request(f"{base}/{kind}/editor", key, {f"{kind}Ids": [match["id"]], "monitored": False})
                return f"moved; unmonitored in {app}"
        except OSError as err:
            return f"moved; {app} unreachable ({err})"
    return ""


def is_swap_candidate(release: dict, current_size: int, hours: float) -> bool:
    """True for an English 1080p release, well seeded, clearly smaller than the file on disk but not a micro-encode.

    Args:
        release: A Radarr /release entry.
        current_size: Bytes of the movie on disk now.
        hours: Runtime in hours.

    Returns:
        Whether to offer it.
    """
    languages = {lang["name"] for lang in release.get("languages", [])}
    upgrade_only = all(any(ok in r for ok in UPGRADE_ONLY_REJECTIONS) for r in release.get("rejections", []))
    return (
        release["quality"]["quality"]["name"] in SWAP_QUALITIES
        and (release.get("seeders") or 0) >= MIN_SEEDERS
        and languages <= {"English", "Unknown"}
        and not FOREIGN_TITLE_RE.search(release["title"])
        and MIN_BYTES_PER_HOUR * hours <= release["size"] <= current_size * MAX_SWAP_FRACTION
        and upgrade_only
    )


def swap_options(movie: dict, hours: float) -> list[dict]:
    """Search Radarr's indexers for smaller English 1080p releases of a movie (10-90 s, depending on the indexers).

    Args:
        movie: Radarr movie record with a movieFile.
        hours: Runtime in hours.

    Returns:
        Up to SWAP_OPTIONS releases, HEVC first, then most seeders.
    """
    current_size = movie["movieFile"]["size"]
    releases = request(f"{RADARR_BASE}/release?movieId={movie['id']}", RADARR_KEY)
    offered = [r for r in releases if is_swap_candidate(r, current_size, hours)]
    offered.sort(key=lambda r: (not HEVC_RE.search(r["title"]), -(r.get("seeders") or 0)))
    keep = ("guid", "indexerId", "title", "size", "seeders", "indexer")
    return [{**{k: r.get(k) for k in keep}, "quality": r["quality"]["quality"]["name"]} for r in offered[:SWAP_OPTIONS]]


def rescan_movie(movie_id: int, timeout_s: float = 90) -> None:
    """Have Radarr rescan a movie folder and wait until it has noticed the file is gone.

    Args:
        movie_id: Radarr movie id.
        timeout_s: Give up waiting after this long.
    """
    command = request(f"{RADARR_BASE}/command", RADARR_KEY, {"name": "RescanMovie", "movieId": movie_id}, "POST")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = request(f"{RADARR_BASE}/command/{command['id']}", RADARR_KEY)["status"]
        if status in ("completed", "failed"):
            return
        time.sleep(2)


def grab(guid: str, indexer_id: int) -> None:
    """Send a release from Radarr's recent search results to the download client.

    Args:
        guid: Release guid from swap_options.
        indexer_id: Release indexerId.
    """
    request(f"{RADARR_BASE}/release", RADARR_KEY, {"guid": guid, "indexerId": indexer_id}, "POST")
