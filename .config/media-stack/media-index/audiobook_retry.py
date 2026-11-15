"""Weekly retry of audiobook requests AudioBookRequest never got: search again, send only a release that is this exact
book. AudioBookRequest searches once, when a book is requested, and its pick only sorts by seeders, so it can take the
wrong volume of a series or a dramatized edition; this pick checks title, author and volume number, skips ebooks,
anything not in English, GraphicAudio / dramatized / "(1 of 5)" editions and files too small for the book's length
(a part of it), and skips a book that already has a torrent in qBittorrent.

    python3 audiobook_retry.py install   # launchd agent, Sundays 02:30 (host, /usr/bin/python3)
    docker exec -i -w /app audiobookrequest /app/.venv/bin/python - run [--dry-run] < audiobook_retry.py

`run` only works inside the audiobookrequest container (it uses the app's own search and download code).
"""

from __future__ import annotations

import difflib
import re
import sys

LABEL = "com.yesselman.audiobook-retry"
QB = "http://gluetun:8080/api/v2"  # from the audiobookrequest container
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
ROMAN = {"ii": 2, "iii": 3, "iv": 4, "vi": 6, "vii": 7, "viii": 8, "ix": 9}
NOISE = re.compile(r"\b(?:19|20)\d\d\b|\b\d+\s?(?:kbps|kb|k|mb|gb|hrs?|h|min|m)\b|\bmp3\b|\bm4b\b|\bm4a\b", re.I)
EBOOK = re.compile(r"\b(epub|mobi|azw3?|pdf|ebook|e-book|cbz|cbr|kindle)\b", re.I)
DRAMA = re.compile(r"graphic ?audio|dramati[sz]|full[- ]cast|\(\d+ of \d+\)", re.I)
FOREIGN = re.compile(  # English only: language names, their words for "audiobook", bracketed codes, other scripts
    r"\b(french|fran[cç]ais|truefrench|vff?|vostfr|tome|livre audio|german|deutsch|h[oö]rbuch|ungek[uü]rzt|spanish"
    r"|espa[nñ]ol|castellano|latino|audiolibro|italiano?|portugu[eê]se?|dublado|russian|polish|polski|dutch"
    r"|nederlands|luisterboek|swedish|svenska|ljudbok|danish|norwegian|finnish|hungarian|czech|turkish|japanese"
    r"|chinese|korean|hindi|arabic)\b| à |[\[(](?:fr|de|es|it|ru|pl|nl|pt|ita|ger|rus|spa|fre)[\])]"
    r"|[\u0400-\u04ff\u0600-\u06ff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", re.I)
VOLUME = re.compile(r"(?:t|b|bk|v|vol|book|tome|arc)0*(\d{1,2})")  # "T02", "bk3": a volume number glued to its label
MIN_KBIT = 30  # below this the file is a part of the book: The Way of Kings "1 of 5" came to 22 on 2026-11-15
STOP = {"a", "an", "the", "of", "and", "book", "volume", "vol", "part", "novel"}


def tokens(text: str) -> list[str]:
    """Lowercase words of a title, number words and roman numerals as digits, sizes and years dropped."""
    text = NOISE.sub(" ", text.lower().replace("’", "").replace("'", ""))
    out = []
    for t in re.findall(r"[a-z0-9]+", text):
        if t in WORDS:
            t = str(WORDS.index(t))
        elif t in ROMAN:
            t = str(ROMAN[t])
        elif VOLUME.fullmatch(t):
            t = VOLUME.fullmatch(t).group(1)
        out.append(t)
    return out


def close(word: str, toks: list[str]) -> bool:
    return any(difflib.SequenceMatcher(None, word, t).ratio() >= 0.8 for t in toks)


def other_book(book, name: str) -> str | None:
    """None when a release or torrent name looks like this book (title, author, volume number), else why not."""
    rel = tokens(name)
    want = [t for t in tokens(book.title) if not t.isdigit() and t not in STOP]
    if want and sum(close(t, rel) for t in want) / len(want) < 0.85:
        return "title differs"
    names = [n.split()[-1].lower() for n in (book.authors or []) + (book.narrators or []) if n.split()]
    if names and not any(close(n, rel) for n in names):
        return "author differs"
    def numbers(toks: list[str]) -> set[int]:
        return {int(t) for t in toks if t.isdigit() and len(t) <= 2}

    in_title, got = numbers(tokens(book.title)), numbers(rel)
    # The subtitle's "Book 1" is optional in a release name; a number in the title itself is not.
    if got not in (in_title, in_title | numbers(tokens(book.subtitle or ""))) and not (not in_title and got <= {1}):
        return "other volume"
    return None


def reason_to_skip(book, src) -> str | None:
    """None when the release is worth sending for this book."""
    if EBOOK.search(src.title):
        return "ebook"
    if DRAMA.search(src.title):
        return "dramatized"
    if FOREIGN.search(src.title) and not FOREIGN.search(book.title):  # a title may itself say "Tome" or "French"
        return "other language"
    if (src.seeders or 0) < 2:
        return "no seeders"
    secs = book.runtime_length_min * 60
    kbit = 8 * src.size / secs / 1000 if secs else 64
    if not MIN_KBIT <= kbit <= 400 or src.size < 30e6:
        return "wrong size"
    return other_book(book, src.title)


async def run(dry_run: bool) -> None:
    """Search every open request once; send the best-seeded matching release of each."""
    import asyncio
    import json
    import logging
    import urllib.request

    import aiohttp
    import structlog
    from app.internal.models import Audiobook, AudiobookRequest
    from app.internal.prowlarr.prowlarr import start_download
    from app.internal.query import query_sources
    from app.util.db import get_session
    from sqlmodel import select

    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))  # app logs each match

    with urllib.request.urlopen(f"{QB}/torrents/info?category=audiobooks", timeout=60) as r:
        torrents = [t["name"] for t in json.load(r)]
    sent, missed, waiting = 0, 0, 0
    with next(get_session()) as s:
        asins = set(s.exec(select(AudiobookRequest.asin)).all())
        books = sorted((b for b in s.exec(select(Audiobook)).all() if b.asin in asins and not b.downloaded),
                       key=lambda b: b.title)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(120)) as cs:
            for b in books:
                if DRAMA.search(b.title):
                    print(f"SKIP {b.title[:60]}: the request itself is a dramatized edition", flush=True)
                    continue
                if any(other_book(b, name) is None for name in torrents):
                    waiting += 1
                    continue
                try:
                    sources = (await query_sources(b.asin, s, cs)).sources or []
                except Exception as e:  # one bad search must not stop the run
                    print(f"ERR  {b.title[:60]}: {type(e).__name__}", flush=True)
                    continue
                why: dict[str, int] = {}
                good = []
                for src in sources:
                    reason = reason_to_skip(b, src)
                    if reason:
                        why[reason] = why.get(reason, 0) + 1
                    else:
                        good.append(src)
                if not good:
                    missed += 1
                    print(f"NONE {b.title[:60]}: {len(sources)} results {why}", flush=True)
                    continue
                g = max(good, key=lambda x: x.seeders or 0)
                print(f"SEND {b.title[:50]} <- {g.title[:70]} | {g.size / 1e6:.0f} MB | {g.seeders} seeds", flush=True)
                if not dry_run:
                    try:
                        await start_download(session=s, client_session=cs, guid=g.guid, indexer_id=g.indexer_id,
                                             asin_or_uuid=b.asin)
                        sent += 1
                    except Exception as e:
                        print(f"FAIL {b.title[:60]}: {type(e).__name__}", flush=True)
                    await asyncio.sleep(2)
    print(f"{len(books)} open requests: {sent} sent, {missed} without a matching release, "
          f"{waiting} already with a torrent")


def install() -> None:
    """Write and load the launchd agent: Sundays at 02:30, inside the 2-6 am bulk-write window."""
    from pathlib import Path

    from shrink import STATE_DIR, install_agent

    docker = "/Applications/OrbStack.app/Contents/MacOS/xbin/docker"
    script = Path(__file__).resolve()
    cmd = f'"{docker}" exec -i -w /app audiobookrequest /app/.venv/bin/python -u - run < "{script}"'
    log = STATE_DIR / "audiobook-retry.log"
    plist = install_agent(LABEL, ["/bin/sh", "-c", cmd], {"StartCalendarInterval": {"Weekday": 0, "Hour": 2,
                                                                                     "Minute": 30}}, log)
    print(f"installed {plist}: Sundays 02:30, log {log}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "install":
        install()
    elif command == "run":
        import asyncio

        asyncio.run(run("--dry-run" in sys.argv))
    else:
        sys.exit(__doc__)
