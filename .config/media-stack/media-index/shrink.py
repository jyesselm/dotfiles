"""Re-encode titles marked Shrink to HEVC with the Mac's hardware encoder. Runs on the macOS host, not in Docker.

Reads the queue from the media-index API (never the SQLite file, which isn't safe to open across the OrbStack
boundary). One file at a time: encode to a hidden temp file next to the original, check the duration matches and the
result is at least MIN_SAVING smaller, move the original into _trash (never deleted), then put the new .mkv in its
place. Each finished title gets a Radarr/Sonarr rescan and is marked Keep with a "shrunk" note so it leaves the queue.

    python3 shrink.py run [--match TEXT] [--limit N] [--until HOUR] [--include-hardlinked] [--retry-failed] [--dry-run]
    python3 shrink.py install     # launchd agent: nightly at 01:00, stops starting new files at 08:00

Written for /usr/bin/python3 (3.9), which launchd runs.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

import arr  # Radarr/Sonarr client shared with the container; only its request() is used here

MEDIA_ROOT = Path("/Volumes/plex-media")
API = "http://localhost:8686/api"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
STATE_DIR = Path.home() / ".local/share/media-index"
LOG = STATE_DIR / "encode.log"
SKIP = STATE_DIR / "encode-skip.json"  # path -> outcome for files not to try again ("kept" or "failed: ...")
LOCK = STATE_DIR / "encode.lock"

# VideoToolbox constant quality. 75 scored VMAF >= 95 ("looks the same") on both a 720p Blu-ray and an SD DivX clip.
QUALITY = 75
MIN_SAVING = 0.2  # keep the original unless the encode is at least 20% smaller
DURATION_TOLERANCE_S = 1.0
PROBE_TIMEOUT_S = 120  # a probe blocked by a macOS privacy prompt nobody answers would otherwise hang for hours
ARR = {
    "movies": ("http://localhost:7878/api/v3", "movie", "HOMEPAGE_VAR_RADARR_KEY", "RescanMovie"),
    "tv": ("http://localhost:8989/api/v3", "series", "HOMEPAGE_VAR_SONARR_KEY", "RescanSeries"),
}
LABEL = "com.yesselman.media-shrink"
START_HOUR, STOP_HOUR = 1, 8

log = logging.getLogger("shrink")


def ffprobe(path: Path) -> dict:
    """Streams and format of a media file.

    Args:
        path: File to probe.

    Returns:
        ffprobe's JSON (keys "streams" and "format"); empty dict when unreadable.
    """
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name", "-of", "json"]
    try:
        out = subprocess.run([*cmd, str(path)], capture_output=True, timeout=PROBE_TIMEOUT_S, check=False).stdout
    except subprocess.TimeoutExpired:
        return {}
    return json.loads(out or b"{}")


def duration(info: dict) -> float:
    """Container duration in seconds, 0 when unknown."""
    return float(info.get("format", {}).get("duration") or 0)


def video_codec(info: dict) -> str:
    """Codec of the first video stream, "" when there is none."""
    return next((s["codec_name"] for s in info.get("streams", []) if s.get("codec_type") == "video"), "")


def encode_cmd(src: Path, dest: Path, info: dict) -> list[str]:
    """ffmpeg command: HEVC video at QUALITY, every audio/subtitle/attachment stream copied, into .mkv.

    Args:
        src: Original file.
        dest: Output .mkv.
        info: ffprobe of src (MP4 text subtitles can't be copied into MKV, so they become SRT).

    Returns:
        The argument list.
    """
    sub_codecs = {s.get("codec_name") for s in info.get("streams", []) if s.get("codec_type") == "subtitle"}
    return [
        "ffmpeg", "-nostdin", "-v", "error", "-y", "-fflags", "+genpts", "-i", str(src),
        "-map", "0:V:0", "-map", "0:a?", "-map", "0:s?", "-map", "0:t?",
        "-c", "copy", "-c:v", "hevc_videotoolbox", "-q:v", str(QUALITY), "-tag:v", "hvc1",
        *(["-c:s", "srt"] if "mov_text" in sub_codecs else []),
        str(dest),
    ]  # fmt: skip


def check_output(src_info: dict, out: Path, src_size: int) -> str:
    """Why the encode can't replace the original, or "" when it can.

    Args:
        src_info: ffprobe of the original.
        out: Encoded file.
        src_size: Original size in bytes.

    Returns:
        A reason, or "".
    """
    out_info = ffprobe(out)
    if video_codec(out_info) != "hevc":
        return "output has no HEVC video"
    if abs(duration(out_info) - duration(src_info)) > DURATION_TOLERANCE_S:
        return f"duration {duration(out_info):.1f}s vs original {duration(src_info):.1f}s"
    if out.stat().st_size > src_size * (1 - MIN_SAVING):
        return f"not worth it: {gb(out.stat().st_size)} vs {gb(src_size)}"
    return ""


def gb(size: float) -> str:
    """Bytes as a short GB string."""
    return f"{size / 1e9:.2f} GB"


def encode_paths(root: Path, rel: str) -> tuple[Path, Path, Path, Path]:
    """Paths for re-encoding one file.

    Args:
        root: Media root.
        rel: Original file, relative to root.

    Returns:
        (original, final .mkv, hidden encode output, place in _trash). Plex and the index skip dotfiles.
    """
    src = root / rel
    final = src.with_suffix(".mkv")
    return src, final, src.with_name(f".{final.stem}.shrinking.mkv"), root / "_trash" / rel


def swap_in_encode(root: Path, rel: str, replace: bool) -> dict:
    """Move the original to _trash and the encode into its place, or delete the encode. Runs in the container.

    Args:
        root: Media root.
        rel: Original file, relative to root.
        replace: Swap the encode in; otherwise discard it.

    Returns:
        {"ok", "message"}.
    """
    src, final, tmp, trash = encode_paths(root, rel)
    if not tmp.exists():
        return {"ok": False, "message": "no encode output"}
    if not replace:
        tmp.unlink()  # our own encode, never an original
        return {"ok": True, "message": "encode discarded"}
    if not src.exists() or trash.exists() or (final != src and final.exists()):
        return {"ok": False, "message": "original missing, or something is already at the .mkv path or in _trash"}
    trash.parent.mkdir(parents=True, exist_ok=True)
    src.rename(trash)
    try:
        tmp.rename(final)
    except OSError:
        trash.rename(src)
        raise
    return {"ok": True, "message": "replaced"}


def shrink_file(rel: str, include_hardlinked: bool, dry_run: bool) -> tuple[str, int, int]:
    """Re-encode one file in place (original to _trash).

    Args:
        rel: Path relative to MEDIA_ROOT, as the queue lists it.
        include_hardlinked: Also encode files that share data with a torrent (frees nothing until it's removed).
        dry_run: Print what would happen; touch nothing.

    Returns:
        (outcome, bytes before, bytes after). Outcome is "done", "already", "kept" (encode not worth it),
        "skipped" (hardlinked) or "failed: <reason>".
    """
    src, final, tmp, trash = encode_paths(MEDIA_ROOT, rel)
    if not src.exists():
        return ("already" if final.exists() else "failed: missing"), 0, 0
    size = src.stat().st_size
    if src.stat().st_nlink > 1 and not include_hardlinked:
        return "skipped", size, size
    info = ffprobe(src)
    if not info:
        return "failed: ffprobe can't read it", size, size
    if video_codec(info) in ("hevc", "av1"):
        return "already", size, size
    if (final != src and final.exists()) or trash.exists():
        return "failed: something is already at the .mkv path or in _trash", size, size
    if dry_run:
        log.info("  would encode (%s)", gb(size))
        return "dry run", size, size
    started = time.time()
    proc = subprocess.run(encode_cmd(src, tmp, info), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        finish(rel, replace=False)
        return f"failed: ffmpeg: {proc.stderr.strip()[-300:]}", size, size
    reason = check_output(info, tmp, size)
    new_size = tmp.stat().st_size
    if reason:
        finish(rel, replace=False)
        return ("kept" if reason.startswith("not worth") else f"failed: {reason}"), size, new_size
    done = finish(rel, replace=True)
    if not done["ok"]:
        return f"failed: {done['message']}", size, new_size
    log.info("  %s -> %s in %.0f min", gb(size), gb(new_size), (time.time() - started) / 60)
    return "done", size, new_size


def finish(rel: str, replace: bool) -> dict:
    """Have the media-index container swap in or discard the encode of rel.

    macOS blocks Python (but not ffmpeg) from changing the external disk under launchd; the container can.

    Args:
        rel: Original file, relative to MEDIA_ROOT.
        replace: Original to _trash and encode into place; otherwise delete the encode.

    Returns:
        The API's {"ok", "message"}.
    """
    try:
        return arr.request(f"{API}/shrink-finish", "", {"path": rel, "replace": replace}, "POST")
    except OSError as err:
        return {"ok": False, "message": f"media-index unreachable ({err})"}


def read_env(path: Path = ENV_FILE) -> dict[str, str]:
    """KEY=VALUE pairs from the stack's .env (for the Radarr/Sonarr API keys)."""
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {k.strip(): v.strip().strip("\"'") for k, v in pairs}


def rescan(item: str) -> None:
    """Ask Radarr (movies/) or Sonarr (tv/) to rescan the title's folder so it picks up the new files."""
    category = item.split("/")[0]
    if category not in ARR:
        return
    base, kind, env_key, command = ARR[category]
    key = read_env().get(env_key, "")
    try:
        entries = arr.request(f"{base}/{kind}", key)
        match = next((e for e in entries if e.get("path") == str(MEDIA_ROOT / item)), None)
        if match:
            arr.request(f"{base}/command", key, {"name": command, f"{kind}Id": match["id"]}, "POST")
            log.info("  %s: %s requested", item, command)
    except OSError as err:
        log.warning("  %s: rescan failed (%s)", item, err)


def load_skip() -> dict[str, str]:
    """Files not to try again."""
    return json.loads(SKIP.read_text()) if SKIP.exists() else {}


def shrink_title(title: dict, args: argparse.Namespace, skip: dict[str, str], budget: dict) -> bool:
    """Process one queued title; mark it Keep (leaves the queue) once every file is done or not worth it.

    Args:
        title: Queue entry: item, note, files.
        args: Command-line options.
        skip: Paths not to try again; updated in place and saved.
        budget: {"left": files still allowed, "deadline": epoch seconds}; updated in place.

    Returns:
        False when the run should stop (limit or deadline reached).
    """
    finished, before, after = 0, 0, 0
    for f in title["files"]:
        rel = f["path"]
        previous = skip.get(rel, "")
        if (args.match and args.match not in rel) or (previous.startswith("failed") and not args.retry_failed):
            continue
        if previous == "kept":  # already tried; the encode wasn't worth it
            finished += 1
            continue
        if budget["left"] <= 0 or time.time() >= budget["deadline"]:
            break
        outcome, size, new_size = _shrink_logged(rel, args, skip)
        budget["left"] -= outcome not in ("already", "skipped")
        finished += outcome in ("done", "already", "kept")
        if outcome == "done":
            before, after = before + size, after + new_size
    if before:
        rescan(title["item"])
    if finished == len(title["files"]) and not args.dry_run:
        mark_done(title, before, after)
    return budget["left"] > 0 and time.time() < budget["deadline"]


def _shrink_logged(rel: str, args: argparse.Namespace, skip: dict[str, str]) -> tuple[str, int, int]:
    """shrink_file with logging; remembers files that failed or weren't worth it."""
    log.info("%s", rel)
    try:
        outcome, size, new_size = shrink_file(rel, args.include_hardlinked, args.dry_run)
    except OSError as err:
        outcome, size, new_size = f"failed: {err}", 0, 0
    if outcome == "kept" and not args.dry_run:
        log.info("  kept original: encode would be %s vs %s", gb(new_size), gb(size))
    elif outcome not in ("done", "dry run"):
        log.info("  %s", outcome)
    if outcome.startswith(("kept", "failed")) and not args.dry_run:
        skip[rel] = outcome
        SKIP.write_text(json.dumps(skip, indent=1))
    return outcome, size, new_size


def mark_done(title: dict, before: int, after: int) -> None:
    """Set the title to Keep with a "shrunk" note (kept after any existing note), which drops it from the queue."""
    stamp = time.strftime("%Y-%m-%d")
    note = f"shrunk {stamp}: {gb(before)} -> {gb(after)}" if before else f"shrink checked {stamp}: nothing to gain"
    note = f"{title['note']}; {note}" if title.get("note") else note
    arr.request(f"{API}/decision", "", {"item": title["item"], "decision": "keep", "note": note}, "POST")
    log.info("%s: marked keep (%s)", title["item"], note)


def deadline(until: int | None) -> float:
    """Epoch seconds of the next HOUR:00 (no new file starts after it); far future when no hour is given."""
    if until is None:
        return float("inf")
    now = time.localtime()
    cutoff = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, until, 0, 0, 0, 0, -1))
    return cutoff if cutoff > time.time() else cutoff + 24 * 3600


def can_read_disk(queue: list[dict]) -> bool:
    """Whether ffprobe can read the media disk from this process.

    Launched by launchd, macOS asks before Homebrew's ffmpeg may read a removable volume, and nobody is there at night
    to click Allow. Probe one queued file up front so a blocked run stops at once instead of failing every file.

    Args:
        queue: The shrink queue.

    Returns:
        True when a queued file could be probed (or none exists to try).
    """
    existing = (MEDIA_ROOT / f["path"] for t in queue for f in t["files"])
    sample = next((p for p in existing if p.exists()), None)
    return sample is None or bool(ffprobe(sample))


def run(args: argparse.Namespace) -> None:
    """Work through the shrink queue, one file at a time, until it's empty or the limit/deadline is hit."""
    lock = open(LOCK, "w")  # noqa: SIM115 - held for the whole run
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.info("another run is in progress")
        return
    queue = arr.request(f"{API}/shrink-queue", "")
    log.info("run started: %d titles, %d files queued", len(queue), sum(len(t["files"]) for t in queue))
    if not can_read_disk(queue):
        log.error(
            "ffprobe can't read %s: give ffmpeg and ffprobe Removable Volumes access (README, Media Index). Stopping.",
            MEDIA_ROOT,
        )
        return
    skip, budget = load_skip(), {"left": args.limit or float("inf"), "deadline": deadline(args.until)}
    for title in queue:
        if not shrink_title(title, args, skip, budget):
            log.info("stopping (file limit or stop hour reached); the next run resumes here")
            break
    if not args.dry_run:
        arr.request(f"{API}/scan", "", {}, "POST")  # refresh the index so finished files drop out of the queue
    log.info("run finished")


def install() -> None:
    """Write and load the launchd agent: nightly at START_HOUR, kept awake, no new file after STOP_HOUR."""
    plist = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    data = {
        "Label": LABEL,
        "ProgramArguments": [
            "/usr/bin/caffeinate",
            "-i",
            "/usr/bin/python3",
            str(Path(__file__).resolve()),
            "run",
            "--until",
            str(STOP_HOUR),
        ],
        "StartCalendarInterval": {"Hour": START_HOUR, "Minute": 0},
        "Nice": 10,
        "LowPriorityIO": True,
        "StandardOutPath": str(LOG),
        "StandardErrorPath": str(LOG),
        "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
    }
    plist.write_bytes(plistlib.dumps(data))
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True, check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True)
    print(f"installed {plist}: nightly at {START_HOUR:02d}:00, log {LOG}")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="install the nightly launchd agent")
    r = sub.add_parser("run", help="process the shrink queue")
    r.add_argument("--match", help="only files whose path contains this text")
    r.add_argument("--limit", type=int, help="stop after encoding this many files")
    r.add_argument("--until", type=int, help="don't start a new file after this hour (0-23)")
    r.add_argument("--include-hardlinked", action="store_true", help="also encode files shared with a torrent")
    r.add_argument("--retry-failed", action="store_true", help="retry files that failed before")
    r.add_argument("--dry-run", action="store_true", help="list what would be encoded")
    args = parser.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(LOG)] + ([logging.StreamHandler()] if sys.stderr.isatty() else [])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=handlers)
    if args.command == "install":
        install()
    else:
        run(args)


if __name__ == "__main__":
    main()
