"""Tests for the host-side encoder. Needs ffmpeg with hevc_videotoolbox (macOS). Run: python -m pytest tests"""

import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

import shrink  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def test_encode_cmd_converts_mp4_text_subtitles() -> None:
    info = {
        "streams": [{"codec_type": "video", "codec_name": "h264"}, {"codec_type": "subtitle", "codec_name": "mov_text"}]
    }
    cmd = shrink.encode_cmd(Path("a.mp4"), Path("a.mkv"), info)
    assert cmd[cmd.index("-c:v") + 1] == "hevc_videotoolbox"
    assert cmd[cmd.index("-c:s") + 1] == "srt"
    assert "-c:s" not in shrink.encode_cmd(Path("a.mkv"), Path("b.mkv"), {"streams": []})


def test_deadline_is_the_next_occurrence() -> None:
    assert shrink.deadline(None) == float("inf")
    assert 0 < shrink.deadline(3) - __import__("time").time() <= 24 * 3600


@pytest.fixture
def media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(shrink, "MEDIA_ROOT", tmp_path)
    monkeypatch.setattr(shrink, "finish", lambda rel, replace: shrink.swap_in_encode(tmp_path, rel, replace))
    (tmp_path / "tv" / "Show").mkdir(parents=True)
    return tmp_path


def _make_video(path: Path, *extra: str) -> None:
    lavfi = ["-f", "lavfi", "-i", "testsrc2=size=640x480:rate=30:duration=5", "-f", "lavfi", "-i", "sine=duration=5"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *lavfi, *extra, str(path)], check=True)


@needs_ffmpeg
def test_shrink_file_replaces_original_and_moves_it_to_trash(media: Path) -> None:
    src = media / "tv" / "Show" / "ep.avi"
    _make_video(src, "-c:v", "mpeg4", "-q:v", "1", "-c:a", "mp3")
    size = src.stat().st_size
    outcome, before, after = shrink.shrink_file("tv/Show/ep.avi", include_hardlinked=False, dry_run=False)
    assert outcome == "done" and before == size and after < size
    assert not src.exists()
    assert (media / "_trash" / "tv" / "Show" / "ep.avi").stat().st_size == size
    new = shrink.ffprobe(media / "tv" / "Show" / "ep.mkv")
    assert shrink.video_codec(new) == "hevc" and any(s["codec_type"] == "audio" for s in new["streams"])
    assert not list((media / "tv" / "Show").glob(".*"))  # temp file gone


@needs_ffmpeg
def test_shrink_file_skips_hardlinked_and_keeps_small_wins(media: Path) -> None:
    src = media / "tv" / "Show" / "ep.mkv"
    _make_video(src, "-c:v", "libx264", "-crf", "35", "-c:a", "aac")
    (media / "linked.mkv").hardlink_to(src)
    assert shrink.shrink_file("tv/Show/ep.mkv", include_hardlinked=False, dry_run=False)[0] == "skipped"
    (media / "linked.mkv").unlink()
    assert shrink.shrink_file("tv/Show/ep.mkv", include_hardlinked=False, dry_run=False)[0] == "kept"
    assert src.exists() and not (media / "_trash").exists()


def test_shrink_title_marks_keep_when_every_file_is_done(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(shrink, "SKIP", tmp_path / "skip.json")
    outcomes = {"a.avi": ("done", 100, 40), "b.avi": ("kept", 100, 90)}
    monkeypatch.setattr(shrink, "shrink_file", lambda rel, *_: outcomes[rel])
    calls = []
    monkeypatch.setattr(shrink.arr, "request", lambda url, key, body=None, method=None: calls.append((url, body)))
    monkeypatch.setattr(shrink, "rescan", lambda item: calls.append(("rescan", item)))
    args = Namespace(match=None, retry_failed=False, include_hardlinked=False, dry_run=False)
    title = {"item": "tv/Show", "note": "", "files": [{"path": "a.avi"}, {"path": "b.avi"}]}
    budget = {"left": 10, "deadline": float("inf")}
    assert shrink.shrink_title(title, args, {}, budget)
    assert calls[0] == ("rescan", "tv/Show")
    assert calls[1][1]["decision"] == "keep" and "0.00 GB" in calls[1][1]["note"]
    assert budget["left"] == 8


def test_can_read_disk_fails_when_probe_is_blocked(media: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (media / "tv" / "Show" / "ep.avi").write_bytes(b"x")
    queue = [{"item": "tv/Show", "files": [{"path": "tv/Show/missing.avi"}, {"path": "tv/Show/ep.avi"}]}]
    monkeypatch.setattr(shrink, "ffprobe", lambda path: {})
    assert not shrink.can_read_disk(queue)
    monkeypatch.setattr(shrink, "ffprobe", lambda path: {"format": {"duration": "1"}})
    assert shrink.can_read_disk(queue)
    assert shrink.can_read_disk([])
