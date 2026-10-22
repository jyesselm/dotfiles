"""Tests for drive manifests. Run: python -m pytest tests"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import drives  # noqa: E402

BIG = drives.RENAMED_MIN_BYTES + 1


def test_catalog_round_trips_and_writes_to_drive(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(drives, "CATALOG_DIR", tmp_path / "catalog")
    mount = tmp_path / "Disk"
    (mount / "movies" / "Heat (1995)").mkdir(parents=True)
    (mount / "movies" / "Heat (1995)" / "Heat.mkv").write_bytes(b"x" * 10)
    (mount / "_trash").mkdir()
    (mount / "_trash" / "gone.mkv").write_bytes(b"x")
    (mount / "movies" / "Icon\r").write_bytes(b"")  # Finder folder icon
    drives.catalog(mount, "Disk")
    assert [(e.path, e.size) for e in drives.load("Disk")] == [("movies/Heat (1995)/Heat.mkv", 10)]
    assert (mount / drives.ON_DRIVE_NAME).exists()
    drives.catalog(mount, "Disk")  # the on-drive manifest is hidden, so it never lists itself
    assert len(drives.load("Disk")) == 1


def test_missing_matches_name_and_size_or_large_renames() -> None:
    old = [
        drives.Entry("movies/heat.mkv", BIG, 0),
        drives.Entry("tv/Show/S01E01.avi", 5, 0),
        drives.Entry("tv/Show/S01E02.avi", 6, 0),
    ]
    new = [drives.Entry("movies/Heat (1995)/Heat.1995.mkv", BIG, 0), drives.Entry("tv/Show/s01e01.avi", 5, 0)]
    assert drives.missing(old, new) == {"tv/Show": 6}


def test_backup_status_counts_only_the_mirrored_folders(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(drives, "CATALOG_DIR", tmp_path)
    monkeypatch.setattr(drives, "BACKUPS", {"backup": ["movies"]})
    main = [drives.Entry("movies/a.mkv", 7, 0), drives.Entry("movies/b.mkv", 9, 0), drives.Entry("tv/c.mkv", 99, 0)]
    drives.save(main, drives.catalog_path(drives.MAIN_DRIVE))
    drives.save([drives.Entry("movies/a.mkv", 7, 0)], drives.catalog_path("backup"))
    assert [row[:3] for row in drives.backup_status()] == [("backup", "movies", 9)]
