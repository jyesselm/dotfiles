"""Tests for the pure parts of the index and the shrink estimate. Run: python -m pytest tests"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("INDEX_DB", "/tmp/media-index-test.db")

import index  # noqa: E402


def test_item_for_groups_one_level_below_category() -> None:
    assert index.item_for("Movies/Heat (1995)/Heat.mkv") == ("Movies/Heat (1995)", "Movies")
    assert index.item_for("Movies/loose.mkv") == ("Movies/loose.mkv", "Movies")
    assert index.item_for("log.tsv") == ("log.tsv", "(root)")


def test_title_key_ignores_year_and_quality() -> None:
    assert index.title_key("Movies/Heat (1995)") == "heat"
    assert index.title_key("old/Heat.1995.1080p.BluRay.x264.mkv") == "heat"


def test_scan_indexes_and_skips_trash(tmp_path: Path) -> None:
    media = tmp_path / "media"
    (media / "Movies" / "Heat (1995)").mkdir(parents=True)
    (media / "Movies" / "Heat (1995)" / "Heat.mkv").write_bytes(b"x" * 10)
    (media / "_trash" / "Movies").mkdir(parents=True)
    (media / "_trash" / "Movies" / "gone.mkv").write_bytes(b"x")
    conn = index.connect(tmp_path / "db" / "index.db")
    index.scan(conn, media)
    rows = [dict(r) for r in conn.execute("select path, item, kind, size from files")]
    assert rows == [{"path": "Movies/Heat (1995)/Heat.mkv", "item": "Movies/Heat (1995)", "kind": "video", "size": 10}]


def test_shrink_saving_skips_hevc_and_estimates_h264() -> None:
    os.environ["MEDIA_ROOT"] = "/tmp"
    import server

    two_hours = 7200.0
    h264 = {"kind": "video", "codec": "h264", "duration_s": two_hours, "height": 1080, "size": 10 * 10**9}
    assert server.shrink_saving(h264) == 10 * 10**9 - int(two_hours * 4_000_000 / 8)
    assert server.shrink_saving({**h264, "codec": "hevc"}) == 0
    assert server.shrink_saving({**h264, "size": 4 * 10**9}) == 0  # saving under 30%


def test_swap_candidate_needs_english_1080p_and_real_saving() -> None:
    import arr

    two_hours = 2.0
    release = {
        "title": "Movie.2019.1080p.BluRay.x265-GRP",
        "quality": {"quality": {"name": "Bluray-1080p"}},
        "seeders": 50,
        "languages": [{"name": "English"}],
        "size": 6 * 10**9,
        "rejections": ["Existing file and the Quality profile does not allow upgrades"],
    }
    on_disk = 30 * 10**9
    assert arr.is_swap_candidate(release, on_disk, two_hours)
    assert not arr.is_swap_candidate({**release, "title": "Movie 2019 1080p ITA x265"}, on_disk, two_hours)
    assert not arr.is_swap_candidate({**release, "rejections": ["Hardcode subs found"]}, on_disk, two_hours)
    assert not arr.is_swap_candidate({**release, "size": 10**9}, on_disk, two_hours)  # micro-encode
    assert not arr.is_swap_candidate(release, 7 * 10**9, two_hours)  # under 30% smaller


def test_shrink_queue_lists_only_worthwhile_files_of_shrink_titles() -> None:
    import server

    server.conn.execute("delete from files")
    server.conn.execute("delete from decisions")
    row = "insert into files (path, item, category, kind, size, mtime, nlink, duration_s, height, codec, probed)"
    big = (7200.0, 1080, "h264", 1)
    server.conn.execute(row + " values ('TV/A/1.mkv', 'TV/A', 'TV', 'video', 10e9, 0, 1, ?, ?, ?, ?)", big)
    server.conn.execute(row + " values ('TV/A/2.mkv', 'TV/A', 'TV', 'video', 10e9, 0, 1, 7200, 1080, 'hevc', 1)")
    server.conn.execute(row + " values ('TV/B/1.mkv', 'TV/B', 'TV', 'video', 10e9, 0, 1, ?, ?, ?, ?)", big)
    server.set_decision("TV/A", "shrink")
    server.set_decision("TV/B", "keep")
    queue = server.shrink_queue()
    assert [(t["item"], [f["path"] for f in t["files"]]) for t in queue] == [("TV/A", ["TV/A/1.mkv"])]
