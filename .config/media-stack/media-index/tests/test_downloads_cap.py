"""The download cap never leaves a category with nothing running (stopped torrents keep their allocated space)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import downloads_cap as dc  # noqa: E402

GB = 10**9


def run(monkeypatch, tmp_path, torrents, sizes, cap_gb=100):
    """One check() over fake torrents; sizes are the GB each entry already holds on disk. Returns the API calls."""
    folder = tmp_path / "downloads" / "sonarr"
    folder.mkdir(parents=True)
    for name in sizes:
        (folder / name).mkdir()
    calls = []

    def qb(path, params=None, post=False, base=dc.QB):
        calls.append((path, (params or {}).get("hashes")))
        return torrents if path == "torrents/info" else ""

    monkeypatch.setattr(dc, "MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(dc, "qb", qb)
    monkeypatch.setattr(dc, "measure", lambda p: (sizes[p.name] * GB, 9e12))
    monkeypatch.setattr(dc, "notify", lambda *a: None)
    dc.check("sonarr", cap_gb, dry_run=False)
    return [c for c in calls if c[0] != "torrents/info"]


def torrent(name, total_gb, state, tags=""):
    return {"name": name, "hash": name, "content_path": f"/x/{name}", "total_size": total_gb * GB, "state": state,
            "tags": tags}


def test_over_the_cap_with_nothing_running_starts_the_nearest_to_done(monkeypatch, tmp_path):
    torrents = [torrent("big", 60, "stoppedDL", "capped"), torrent("small", 15, "stoppedDL", "capped")]
    calls = run(monkeypatch, tmp_path, torrents, {"big": 45, "small": 12}, cap_gb=50)  # 57 GB held, cap 50
    assert ("torrents/start", "small") in calls
    assert ("torrents/start", "big") not in calls


def test_the_last_running_download_is_not_stopped(monkeypatch, tmp_path):
    calls = run(monkeypatch, tmp_path, [torrent("only", 60, "downloading")], {"only": 45}, cap_gb=50)
    assert ("torrents/stop", "only") not in calls
