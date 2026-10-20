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
