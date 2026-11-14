"""Home dashboard: one page over the media stack, the NAS and every machine on the tailnet.

Standard library only. A background thread refreshes a JSON snapshot every REFRESH_S from the
services' own APIs and plain TCP probes; the page fetches it from /api/state. Plex posters are
proxied through /poster so the token never reaches the browser. Nothing here writes anywhere.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

PORT = int(os.environ.get("PORT", "3000"))
REFRESH_S = 60
STATIC = Path(__file__).parent / "static"
ENV = os.environ
PLEX = f"http://{ENV.get('HOST_ADDR', 'host.docker.internal')}:32400"
PLEX_TOKEN = ENV.get("PLEX_TOKEN", "")
TAILNET = ENV.get("TAILNET", "tail2813f4.ts.net")
NAS_STATUS = "http://100.88.15.86:8765/status.json"
HOST_JSON = Path("/host/host.json")  # written by host-stats.py on the Mac
BACKUPS = Path("/backups")  # ~/backups/media-stack, written by backup.sh
DOCKER_SOCK = "/var/run/docker.sock"

# Services: name, icon, blurb, container host:port, published port (None = no page), API key env.
# Links are built in the browser from its own hostname plus the published port.
SERVICES = [
    ("Plex", "plex.svg", "Movies, TV, music", f"{ENV.get('HOST_ADDR', '')}:32400", 32400, None),
    ("Seerr", "jellyseerr.svg", "Request movies and TV", "seerr:5055", 5055, None),
    ("Audiobookshelf", "audiobookshelf.svg", "Audiobooks and podcasts", "audiobookshelf:80", 13378, None),
    ("AudioBookRequest", "📚", "Request audiobooks", "audiobookrequest:8000", 8000, None),
    ("Kavita", "📖", "Read manga", "kavita:5000", 5003, None),
    ("Suwayomi", "📥", "Manga: follow a series", "suwayomi:4567", 4567, None),
    ("RomM", "romm.svg", "Retro games", "romm:8080", 8090, None),
    ("Gamarr", "🎮", "Request games", "gamarr:5001", 5001, None),
    ("PairDrop", "pairdrop.png", "Send files between devices", "pairdrop:3000", 3010, None),
    ("Media Index", "💽", "Keep / delete / shrink", "media-index:8686", 8686, None),
    ("Radarr", "radarr.svg", "Movies", "radarr:7878", 7878, "RADARR_KEY"),
    ("Sonarr", "sonarr.svg", "TV", "sonarr:8989", 8989, "SONARR_KEY"),
    ("Lidarr", "lidarr.svg", "Music", "lidarr:8686", 8687, "LIDARR_KEY"),
    ("Bazarr", "bazarr.svg", "Subtitles", "bazarr:6767", 6767, None),
    ("spotDL", "spotify.svg", "Songs from Spotify links", "spotdl:8800", 8800, None),
    ("Sonobarr", "🎧", "Music discovery", "sonobarr:5000", 8688, None),
    ("Prowlarr", "prowlarr.svg", "Indexers", "prowlarr:9696", 9696, "PROWLARR_KEY"),
    ("FlareSolverr", "flaresolverr.svg", "Cloudflare helper", "flaresolverr:8191", None, None),
    ("qBittorrent", "qbittorrent.svg", "Downloads", "gluetun:8080", 8080, None),
    ("VPN", "gluetun.svg", "NordVPN tunnel", "gluetun:8000", None, None),
    ("Cleanuparr", "cleanuparr.png", "Replaces stalled downloads", "cleanuparr:11011", 11011, None),
    ("Uptime Kuma", "uptime-kuma.svg", "Up/down alerts", "uptime-kuma:3001", 3001, None),
]

# Machines: name, role, icon, tailnet host, IP, ssh user ("" = no ssh), probe port, links (label, url).
MACHINES = [
    ("Plex Server", "Mac mini · media stack", "apple.svg", "plex-server", "100.120.188.110", "jyesselm", 32400,
     [("Plex", "http://plex-server.{ts}:32400/web"), ("Uptime Kuma", "http://plex-server.{ts}:3001")]),
    ("Mac Studio", "Main workstation", "apple.svg", "mac-studio", "100.73.70.25", "jyesselm", 22,
     [("Notes", "http://mac-studio.{ts}:8766"), ("Tasks", "http://mac-studio.{ts}:8767"),
      ("Data Index", "http://mac-studio.{ts}:8768"), ("CHEM 114", "http://mac-studio.{ts}:8000"),
      ("Chess coach", "https://mac-studio.{ts}")]),
    ("NAS", "Synology · Yesselman Backup", "synology.svg", "yesselmanbackup", "100.88.15.86", "", 8765,
     [("DSM", "http://yesselmanbackup.{ts}:5000"), ("NAS portal", "http://yesselmanbackup.{ts}:8765")]),
    ("Home GPU", "Linux · GPU box", "linux.svg", "home-gpu", "100.103.114.116", "jyesselm", 22,
     [("Clips", "https://home-gpu.{ts}")]),
    ("MacBook Pro", "Laptop", "apple.svg", "josephs-macbook-pro-2", "100.85.67.82", "jyesselm", 22, []),
    ("Living Room TV", "Onn 4K Pro · Kodi", "android.svg", "living-room", "100.110.116.104", "", 8080, []),
]

# Public websites: name, URL. Up when the server answers at all (a login redirect counts).
SITES = [("Tasks", "https://tasks.jyesselman.com/")]

state: dict = {"ok": False}
state_lock = threading.Lock()
posters: dict[str, bytes] = {}


def get(url: str, headers: dict | None = None, timeout: float = 8) -> bytes:
    with urlopen(Request(url, headers=headers or {}), timeout=timeout) as r:
        return r.read()


def get_json(url: str, headers: dict | None = None, timeout: float = 8):
    return json.loads(get(url, headers, timeout))


def reachable(host: str, port: int, timeout: float = 2) -> bool:
    """True when something answers at host:port. A refused connection still means the machine is up."""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except ConnectionRefusedError:
        return True
    except OSError:
        return False
    finally:
        s.close()


def arr(key_env: str, host: str, path: str, v: int = 3):
    return get_json(f"http://{host}/api/v{v}/{path}", {"X-Api-Key": ENV.get(key_env, "")})


# ---- collectors: each returns its slice of the state or raises ----


def plex_recent() -> list[dict]:
    """Newest movies, shows and anime (no music, no YouTube), one entry per show."""
    out, seen = [], set()
    for key, kind in ((1, "Movie"), (2, "TV"), (4, "Anime")):
        d = get_json(f"{PLEX}/library/sections/{key}/recentlyAdded?X-Plex-Container-Size=20&X-Plex-Token={PLEX_TOKEN}",
                     {"Accept": "application/json"})
        for m in d.get("MediaContainer", {}).get("Metadata", []):
            t = m.get("type")
            title = m.get("grandparentTitle") if t == "episode" else m.get("parentTitle") if t == "season" else m.get("title")
            thumb = m.get("grandparentThumb") or m.get("parentThumb") or m.get("thumb")
            if not title or title in seen or not thumb:
                continue
            seen.add(title)
            sub = m.get("parentTitle") if t == "episode" else m.get("title") if t == "season" else None
            out.append({"title": title, "kind": kind, "sub": sub, "img": "/poster?p=" + quote(thumb),
                        "added": m.get("addedAt", 0), "year": m.get("parentYear") or m.get("year")})
    out.sort(key=lambda x: -x["added"])
    return out[:14]


def now_playing() -> list[dict]:
    d = get_json(f"{PLEX}/status/sessions?X-Plex-Token={PLEX_TOKEN}", {"Accept": "application/json"})
    out = []
    for m in d.get("MediaContainer", {}).get("Metadata", []):
        t = m.get("type")
        if t == "track":  # music plays all day; only video is worth a row
            continue
        if t == "episode":
            title, sub = m.get("grandparentTitle"), f"{m.get('parentTitle')} · {m.get('title')}"
        else:
            title, sub = m.get("title"), str(m.get("year") or "")
        thumb = m.get("grandparentThumb") if t == "episode" else m.get("thumb")
        out.append({"title": title, "sub": sub, "kind": t, "img": "/poster?p=" + quote(thumb) if thumb else None,
                    "user": (m.get("User") or {}).get("title"), "player": (m.get("Player") or {}).get("title"),
                    "state": (m.get("Player") or {}).get("state"),
                    "pct": round(100 * (m.get("viewOffset") or 0) / m["duration"]) if m.get("duration") else 0})
    return out


titles: dict[tuple, dict] = {}  # Seerr media id -> title/poster, looked up once


def requests_recent() -> list[dict]:
    """Latest Seerr requests with where each one stands (Seerr media status 5 = in Plex, 4 = partly)."""
    h = {"X-Api-Key": ENV.get("SEERR_KEY", "")}
    d = get_json("http://seerr:5055/api/v1/request?take=8&sort=added", h)
    out = []
    for r in d.get("results", []):
        key = (r["type"], r["media"]["tmdbId"])
        if key not in titles:
            m = get_json(f"http://seerr:5055/api/v1/{key[0]}/{key[1]}", h)
            titles[key] = {"title": m.get("title") or m.get("name"),
                           "img": "/poster?p=" + quote(m["posterPath"]) if m.get("posterPath") else None,
                           "year": (m.get("releaseDate") or m.get("firstAirDate") or "")[:4]}
        ms, rs = r["media"].get("status"), r.get("status")
        state = "declined" if rs == 3 else "pending" if rs == 1 else "available" if ms == 5 else "partial" if ms == 4 else "processing"
        out.append({**titles[key], "kind": "Movie" if r["type"] == "movie" else "TV", "state": state,
                    "by": (r.get("requestedBy") or {}).get("displayName"), "added": r.get("createdAt", "")[:10],
                    "seasons": [s["seasonNumber"] for s in r.get("seasons") or []]})
    return out


TRAKT_AUTH = Path("/trakt/.pytrakt.json")  # PlexTraktSync's sign-in; that container keeps the token fresh
# Trakt list slug -> tab label; a list that doesn't exist yet shows how to make it
WATCH_LISTS = {"non-plex-watchlist": "By myself", "non-plex-watchlist-together": "Together"}
REGION = "US"
MINE = ["Netflix", "HBO Max", "Prime Video", "Disney+", "Hulu", "Apple TV"]  # subscriptions you pay for, in shelf order
CHANNEL = re.compile(r"\s*(Amazon|Apple TV|Roku Premium) Channel\s*$", re.I)
where: dict[tuple, dict] = {}  # (type, TMDB id) -> title/poster/services from Seerr, looked up daily
details: dict[tuple, dict] = {}  # same key -> the detail sheet, also daily


def service(name: str) -> str:
    """One name per subscription: drop the storefront channel and the plan tier."""
    name = re.sub(r"( Standard| Premium Plus| Premium| Essential| Free)?( with Ads)?$", "", CHANNEL.sub("", name).strip())
    return {"Amazon Prime Video": "Prime Video"}.get(name, re.sub(r" Plus$", "+", name))


def watch_next() -> list[dict]:
    """The Trakt lists of things to stream elsewhere, each as one shelf per service that has them."""
    t = json.loads(TRAKT_AUTH.read_text())
    th = {"trakt-api-key": t["CLIENT_ID"], "trakt-api-version": "2", "Authorization": "Bearer " + t["OAUTH_TOKEN"],
          "User-Agent": "dashboard"}
    have = {lst["ids"]["slug"] for lst in get_json("https://api.trakt.tv/users/me/lists", th)}
    return [{"slug": slug, "name": name, "missing": slug not in have,
             "shelves": by_service(get_json(f"https://api.trakt.tv/users/me/lists/{slug}/items", th)) if slug in have else []}
            for slug, name in WATCH_LISTS.items()]


plex_seen: dict = {"at": 0, "ids": set()}


def plex_ids() -> set[str]:
    """Every external id in the Plex library ("tmdb:movie:603", "imdb:tt0133093", "tvdb:79126"), refreshed every 10 min.
    Newer agents list them under Guid; legacy ones only carry a single com.plexapp.agents.* guid."""
    if plex_seen["at"] < time.time() - 600:
        ids = set()
        for key in (1, 2, 4):
            d = get_json(f"{PLEX}/library/sections/{key}/all?includeGuids=1&X-Plex-Token={PLEX_TOKEN}", {"Accept": "application/json"}, 20)
            for m in d["MediaContainer"].get("Metadata", []):
                for g in [x["id"] for x in m.get("Guid", [])] + [m.get("guid") or ""]:
                    hit = re.match(r"(?:com\.plexapp\.agents\.)?(tmdb|themoviedb|imdb|tvdb|thetvdb)://([^?/]+)", g)
                    if hit:
                        src = {"themoviedb": "tmdb", "thetvdb": "tvdb"}.get(hit[1], hit[1])
                        ids.add(f"tmdb:{m['type']}:{hit[2]}" if src == "tmdb" else f"{src}:{hit[2]}")
        plex_seen.update(at=time.time(), ids=ids)
    return plex_seen["ids"]


def by_service(items: list[dict]) -> list[dict]:
    """Group Trakt list items into In Plex, one shelf per MINE service, then everything else (TMDB, via Seerr)."""
    shelves: dict[str, dict] = {}
    try:
        library = plex_ids()
    except Exception:  # Plex down: fall back to Seerr's last scan of it
        library = None
    for it in items:
        m = it.get(it["type"]) or {}
        ids = m.get("ids") or {}
        tmdb = ids.get("tmdb")
        if it["type"] not in ("movie", "show") or not tmdb:
            continue
        key = (it["type"], tmdb)
        if key not in where or where[key]["at"] < time.time() - 86400:
            d = seerr_title(it["type"], tmdb)
            p = next((w for w in d.get("watchProviders") or [] if w["iso_3166_1"] == REGION), {})
            subs = {}  # "AMC Plus Apple TV channel", "AMC+ Amazon Channel" and "AMC+" are one subscription
            for s in sorted(p.get("flatrate", []) + p.get("free", []) + p.get("ads", []), key=lambda s: (bool(CHANNEL.search(s["name"])), s["displayPriority"])):
                subs.setdefault(service(s["name"]), s.get("logoPath"))
            where[key] = {"title": d.get("title") or d.get("name"), "year": (d.get("releaseDate") or d.get("firstAirDate") or "")[:4],
                          "img": "/poster?p=" + quote(d["posterPath"]) if d.get("posterPath") else None,
                          "kind": "Movie" if it["type"] == "movie" else "TV", "link": p.get("link"), "services": subs,
                          "plex": (d.get("mediaInfo") or {}).get("status") in (4, 5), "at": time.time()}
        w = where[key]
        plex = w["plex"] if library is None else bool(library & {f"tmdb:{it['type']}:{tmdb}", f"imdb:{ids.get('imdb')}", f"tvdb:{ids.get('tvdb')}"})
        mine = [n for n in MINE if n in w["services"]]
        card = {k: w[k] for k in ("title", "year", "img", "kind", "link")} | {
            "tmdb": tmdb, "type": it["type"], "plex": plex, "mine": mine, "other": [n for n in w["services"] if n not in MINE]}
        names = ["In Plex"] if plex else mine or (["Other services"] if w["services"] else ["Rent or buy only"])
        for n in names:
            shelves.setdefault(n, {"name": n, "logo": w["services"].get(n), "items": []})["items"].append(card)
    rank = ["In Plex", *MINE, "Other services", "Rent or buy only"]
    order = sorted(shelves.values(), key=lambda s: rank.index(s["name"]))
    for s in order:
        if s["logo"]:
            s["logo"] = "/poster?p=" + quote(s["logo"])
    return order


# ---- listen: what to hear next, from Audiobookshelf history and Audible's public catalog ----

ABS = "http://audiobookshelf:80"
AUDIBLE = "https://api.audible.com/1.0/catalog/products"
AUDIBLE_FIELDS = "response_groups=product_attrs,product_desc,media,contributors,series,rating,relationships"
LISTEN_SHELF = 24  # cards per shelf
listen: dict = {"at": 0, "shelves": None, "building": False}


def listen_next() -> list[dict] | None:
    """The Listen tab's shelves, rebuilt in the background every six hours (about a hundred catalog calls); None
    until the first build finishes."""
    if listen["at"] < time.time() - 6 * 3600 and not listen["building"]:
        listen["building"] = True
        threading.Thread(target=build_listen, daemon=True).start()
    return listen["shelves"]


def book_key(title: str) -> str:
    """A title without its subtitle, case or punctuation, so editions of one book match."""
    return re.sub(r"[^a-z0-9]+", " ", re.split(r"[:(]", title)[0].lower()).strip()


def on_shelf(title: str, shelf: dict[str, dict]) -> dict | None:
    """The shelf's copy of a catalog title; Audible sometimes leads with the series ("The Farseer: Assassin's ...")."""
    return next((shelf[k] for part in title.split(":") if (k := book_key(part)) in shelf), None)


def number(sequence: str | None) -> float | None:
    try:
        return float(sequence)
    except (TypeError, ValueError):
        return None


def shelf_books() -> list[dict]:
    """Every book in Audiobookshelf with whether it was finished or started."""
    head = {"Authorization": "Bearer " + ENV.get("ABS_KEY", "")}
    progress = {p["libraryItemId"]: p["isFinished"] for p in get_json(f"{ABS}/api/me", head, 30)["mediaProgress"]}
    books = []
    for lib in get_json(f"{ABS}/api/libraries", head, 30)["libraries"]:
        if lib["mediaType"] != "book":
            continue
        for it in get_json(f"{ABS}/api/libraries/{lib['id']}/items?limit=0", head, 60)["results"]:
            m = it["media"]["metadata"]
            series, _, seq = (m.get("seriesName") or "").partition(" #")
            books.append({"id": it["id"], "title": m.get("title") or "", "author": m.get("authorName") or "",
                          "series": series, "seq": number(seq.split(",")[0]), "asin": m.get("asin"),
                          "done": progress.get(it["id"], False), "started": it["id"] in progress})
    return books


def audible(path: str) -> dict:
    return get_json(f"{AUDIBLE}/{path}{'&' if '?' in path else '?'}{AUDIBLE_FIELDS}", {"User-Agent": "Mozilla/5.0"}, 20)


def catalog_card(b: dict, why: str) -> dict:
    """A book from Audible's catalog that isn't on the shelf: the card asks AudioBookRequest for it."""
    author = ", ".join(a["name"] for a in (b.get("authors") or [])[:2])
    ser = (b.get("series") or [{}])[0]
    return {"title": b.get("title") or "", "author": author, "why": why, "owned": False,
            "note": f"{ser['title']} #{ser.get('sequence')}" if ser.get("title") else "",
            "img": (b.get("product_images") or {}).get("500"), "port": 8000,
            "path": "/search?q=" + quote(f"{b.get('title', '')} {author}")}


def shelf_card(b: dict, why: str) -> dict:
    return {"title": b["title"], "author": b["author"], "why": why, "owned": True,
            "note": f"{b['series']} #{b['seq']:g}" if b["series"] and b["seq"] is not None else b["series"],
            "img": f"/cover?id={b['id']}", "port": 13378, "path": f"/item/{b['id']}"}


def next_in_series(mine: list[dict], shelf: dict[str, dict]) -> dict | None:
    """The book after the last one finished in a series: from the shelf if it is there, else from Audible."""
    last = max(b["seq"] for b in mine if b["done"])
    waiting = [b for b in mine if not b["done"] and b["seq"] > last]
    if waiting:
        return shelf_card(min(waiting, key=lambda b: b["seq"]), f"next after #{last:g}")
    asin = next((b["asin"] for b in mine if b["done"] and b["asin"]), None)
    listed = [s for s in (audible(asin)["product"].get("series") or [] if asin else []) if s.get("asin")]
    ser = next((s for s in listed if book_key(s["title"]) == book_key(mine[0]["series"])), None)
    if not ser:  # only trust the numbering of the series Audiobookshelf names
        return None
    later = sorted((n, r["asin"]) for r in audible(ser["asin"])["product"].get("relationships") or []
                   if (n := number(r.get("sequence"))) is not None and n > last and n == int(n))
    for _, child in later[:8]:  # a number has several editions, and a later book may sit under another series name
        book = audible(child)["product"]
        if book.get("language") != "english" or not book.get("title"):
            continue
        own = on_shelf(book["title"], shelf)
        if not own:
            return catalog_card(book, f"next after #{last:g} · not on your shelf")
        if not own["done"]:
            return shelf_card(own, f"next after #{last:g}")
    return None


def listeners_liked(done: list[dict]) -> dict[str, dict]:
    """What Audible's listeners of each finished book also liked: book key -> the catalog book and the finished
    titles that led to it."""
    liked: dict[str, dict] = {}
    for b in done:
        try:
            similar = audible(f"{b['asin']}/sims?similarity_type=RawSimilarities&num_results=16")["similar_products"]
        except OSError:
            continue
        for sim in similar:
            if sim.get("language") == "english" and sim.get("title"):
                liked.setdefault(book_key(sim["title"]), {"book": sim, "from": []})["from"].append(b["title"])
    return liked


def new_to_you(liked: dict[str, dict], shelf: dict[str, dict], have_series: set[str], because) -> list[dict]:
    """Liked books that aren't on the shelf, one card per series (its lowest-numbered book), best supported first."""
    fresh: dict[str, tuple] = {}
    for key, hit in liked.items():
        title, ser = hit["book"]["title"], (hit["book"].get("series") or [{}])[0]
        seq, slot = number(ser.get("sequence")), ser.get("asin") or key
        side_story = ser.get("title") and (seq is None or seq < 1)  # novellas, companions, omnibus entries
        if on_shelf(title, shelf) or book_key(ser.get("title") or "") in have_series or side_story or "Dramatized" in title:
            continue
        score, why = because(key, "")
        rating = (hit["book"].get("rating") or {}).get("overall_distribution") or {}
        seq = seq or 0
        if slot not in fresh or seq < fresh[slot][0]:
            fresh[slot] = (seq, score, float(rating.get("display_average_rating") or 0), catalog_card(hit["book"], why))
    return [f[3] for f in sorted(fresh.values(), key=lambda f: (-f[1], -f[2]))][:LISTEN_SHELF]


def carry_on(by_series: dict[str, list[dict]], begun: set[str], shelf: dict[str, dict]) -> list[dict]:
    cards = []
    for name in sorted(begun):
        try:
            card = next_in_series(by_series[name], shelf)
        except OSError:
            card = None
        if card:
            cards.append(card)
    return cards


def build_listen() -> None:
    try:
        books = [b for b in shelf_books() if b["title"]]
        done = [b for b in books if b["done"]]
        by_series: dict[str, list[dict]] = {}
        for b in books:
            if b["series"] and b["seq"] is not None:
                by_series.setdefault(b["series"], []).append(b)
        begun = {name for name, mine in by_series.items() if any(b["done"] for b in mine)}
        liked = listeners_liked([b for b in done if b["asin"]])
        authors: dict[str, int] = {}
        for b in done:
            authors[b["author"]] = authors.get(b["author"], 0) + 1

        def because(key: str, author: str) -> tuple[int, str]:
            sources = list(dict.fromkeys(liked.get(key, {}).get("from", [])))
            score = 2 * len(sources) + min(authors.get(author, 0), 3)
            return score, ("listeners of " + " and ".join(sources[:2]) + " liked it" if sources
                           else f"you finished {authors[author]} by {author}" if author in authors else "")

        unheard = []
        for b in books:
            first = b["series"] not in by_series or b is min(by_series[b["series"]], key=lambda x: x["seq"])
            score, why = because(book_key(b["title"]), b["author"])
            if score and first and not b["started"] and b["series"] not in begun:
                unheard.append((score, shelf_card(b, why)))
        shelf = {book_key(b["title"]): b for b in books}
        listen["shelves"] = [
            {"name": "Continue a series", "items": carry_on(by_series, begun, shelf)},
            {"name": "On your shelf, not started",
             "items": [c for _, c in sorted(unheard, key=lambda u: -u[0])][:LISTEN_SHELF]},
            {"name": "New to you", "items": new_to_you(liked, shelf, {book_key(n) for n in by_series}, because)},
        ]
        listen["at"] = time.time()
    finally:
        listen["building"] = False


# ---- search: one box over what is on disk (Media Index), then what Seerr and Audible could fetch ----
KINDS = {"movies": "Movie", "tv": "TV", "anime": "Anime", "audiobooks": "Audiobook", "manga": "Manga", "music": "Music",
         "podcasts": "Podcast", "books": "Book", "downloads": "Downloading"}
SQUARE = ("audiobooks", "music", "podcasts")
SEERR_STATE = {5: "In Plex", 4: "Partly in Plex", 3: "Requested", 2: "Requested"}
FOUND = 18  # cards per shelf
disk: dict = {"at": 0.0, "items": []}


def disk_items() -> list[dict]:
    if time.time() - disk["at"] > 300:
        disk.update(at=time.time(), items=get_json("http://media-index:8686/api/items", timeout=30))
    return disk["items"]


def disk_title(item: dict) -> str:
    """A title's folder name without the "03 - " a series folder numbers it with."""
    return re.sub(r"^\d+(\.\d+)?\s*-\s*", "", item["item"].rsplit("/", 1)[-1])


def on_disk(words: list[str]) -> list[dict]:
    hits = [i for i in disk_items()
            if not i.get("trashed_at") and all(w in i["item"].split("/", 1)[-1].lower() for w in words)]
    hits.sort(key=lambda i: (i["category"] == "downloads", len(i["item"])))
    return [{"title": disk_title(i),
             "author": " · ".join([KINDS.get(i["category"], i["category"]), *i["item"].split("/")[1:-1]]),
             "why": "on a cold drive" if i.get("cold") else "", "img": "/art?item=" + quote(i["item"]),
             "href": "#library?" + quote(i["item"].rsplit("/", 1)[-1]), "owned": True, "badge": "In your library",
             "tall": i["category"] not in SQUARE} for i in hits[:FOUND]]


def requestable(q: str) -> list[dict]:
    d = get_json(f"http://seerr:5055/api/v1/search?query={quote(q)}", {"X-Api-Key": ENV.get("SEERR_KEY", "")})
    out = []
    for r in d.get("results", []):
        if r.get("mediaType") not in ("movie", "tv"):
            continue
        state = SEERR_STATE.get((r.get("mediaInfo") or {}).get("status"))
        out.append({"title": r.get("title") or r.get("name") or "", "tall": True, "owned": state == "In Plex",
                    "author": "Movie" if r["mediaType"] == "movie" else "TV", "badge": state or "Request",
                    "why": (r.get("releaseDate") or r.get("firstAirDate") or "")[:4], "port": 5055,
                    "img": "/poster?p=" + quote(r["posterPath"]) if r.get("posterPath") else None,
                    "path": f"/{r['mediaType']}/{r['id']}"})
    return out[:FOUND]


def search(q: str) -> list[dict]:
    words = re.findall(r"[a-z0-9]+", q.lower())
    if not words:
        return []
    have = on_disk(words)
    owned = {book_key(disk_title(i)) for i in disk_items() if i["category"] == "audiobooks"}
    shelves = [{"name": "In your library", "items": have}]
    books = f"?keywords={quote(q)}&num_results=12"
    for name, find in (("Movies and shows", lambda: requestable(q)),
                       ("Audiobooks to request", lambda: [catalog_card(b, "") for b in audible(books)["products"]
                                                          if book_key(b["title"]) not in owned])):
        try:
            shelves.append({"name": name, "items": find()})
        except Exception as e:  # one source down: the others still answer
            print(f"search {name}: {e}", flush=True)
    return shelves


def seerr_title(kind: str, tmdb) -> dict:
    """Seerr's copy of one TMDB movie or show (kind is Trakt's "movie" or "show")."""
    return get_json(f"http://seerr:5055/api/v1/{'movie' if kind == 'movie' else 'tv'}/{tmdb}",
                    {"X-Api-Key": ENV.get("SEERR_KEY", "")})


def title(kind: str, tmdb: str) -> dict:
    """The detail sheet for one title: blurb, cast, backdrop and YouTube trailer."""
    key = (kind, tmdb)
    if key not in details or details[key]["at"] < time.time() - 86400:
        d = seerr_title(kind, tmdb)
        yt = [v for v in d.get("relatedVideos") or [] if v.get("site") == "YouTube"]
        trailer = next((v for v in yt if v.get("type") == "Trailer"), yt[0] if yt else None)
        details[key] = {
            "title": d.get("title") or d.get("name"), "year": (d.get("releaseDate") or d.get("firstAirDate") or "")[:4],
            "tagline": d.get("tagline"), "runtime": d.get("runtime") or (d.get("episodeRunTime") or [None])[0],
            "genres": [g["name"] for g in d.get("genres") or []], "rating": round(d.get("voteAverage") or 0, 1),
            "overview": d.get("overview"), "cast": [c["name"] for c in (d.get("credits") or {}).get("cast", [])[:4]],
            "backdrop": f"/poster?p={quote(d['backdropPath'])}&w=1280" if d.get("backdropPath") else None,
            "trailer": trailer and trailer["key"], "at": time.time()}
    return details[key]


def plex_counts() -> dict:
    n = {}
    for key, name in ((1, "movies"), (2, "shows"), (4, "anime")):
        d = get_json(f"{PLEX}/library/sections/{key}/all?X-Plex-Container-Start=0&X-Plex-Container-Size=0&X-Plex-Token={PLEX_TOKEN}",
                     {"Accept": "application/json"})
        n[name] = d["MediaContainer"].get("totalSize", 0)
    return n


def queue() -> list[dict]:
    rows = []
    for key, host, kind, field in (("RADARR_KEY", "radarr:7878", "Movie", "movie"), ("SONARR_KEY", "sonarr:8989", "TV", "series")):
        d = arr(key, host, f"queue?pageSize=200&includeSeries=true&includeMovie=true")
        for r in d.get("records", []):
            size = r.get("size") or 0
            pct = round(100 * (1 - (r.get("sizeleft") or 0) / size)) if size else 0
            st = "warning" if r.get("trackedDownloadStatus") == "warning" or r.get("status") == "warning" else \
                 "downloading" if r.get("status") == "downloading" and pct < 100 else "queued"
            rows.append({"title": (r.get(field) or {}).get("title") or r.get("title"), "kind": kind, "pct": pct, "state": st})
    return rows


def arr_counts() -> dict:
    return {
        "radarr_missing": arr("RADARR_KEY", "radarr:7878", "wanted/missing?pageSize=1").get("totalRecords", 0),
        "sonarr_missing": arr("SONARR_KEY", "sonarr:8989", "wanted/missing?pageSize=1").get("totalRecords", 0),
        "lidarr_artists": len(arr("LIDARR_KEY", "lidarr:8686", "artist", 1)),
        "prowlarr_indexers": len(arr("PROWLARR_KEY", "prowlarr:9696", "indexer", 1)),
    }


def torrents() -> dict:
    t = get_json("http://gluetun:8080/api/v2/transfer/info")
    seeding = get_json("http://gluetun:8080/api/v2/torrents/info?filter=seeding")
    return {"dl_speed": t.get("dl_info_speed", 0), "up_speed": t.get("up_info_speed", 0), "seeding": len(seeding)}


def vpn() -> dict:
    d = get_json("http://gluetun:8000/v1/publicip/ip")
    return {"ip": d.get("public_ip"), "city": d.get("city"), "country": d.get("country")}


def storage() -> dict:
    s = get_json("http://media-index:8686/api/summary")
    items = get_json("http://media-index:8686/api/items?limit=400&sort=size")
    items = items if isinstance(items, list) else items.get("items", [])
    never = [{"item": i["item"].split("/", 1)[-1], "cat": i["category"], "size": i["size"], "files": i["files"],
              "codec": (i.get("codecs") or "").split(",")[0], "h": i.get("height")}
             for i in items if not i.get("plays") and not i.get("last_viewed") and not i.get("trashed_at")
             and i.get("decision") != "delete" and i["category"] not in ("downloads", "other")][:8]
    d = s["disk"]
    dec = s["decided"]
    return {"total": d["total"], "used": d["used"], "free": d["free"], "undecided": dec["undecided"]["items"],
            "shrinkable": s["shrinkable"], "trash": s["trash"], "trashed_items": dec["trashed"]["items"],
            "trashed_size": dec["trashed"]["size"], "cats": s["categories"], "never": never}


def nas() -> dict:
    d = get_json(NAS_STATUS)
    s = d["summary"]
    return {"v1": s["volume1_pct"], "v2": s["volume2_pct"], "raid": s["raid"], "temp": s["disk_max_temp_c"],
            "free1": s["volume1_free_bytes"], "free2": s["volume2_free_bytes"]}


def services(counts: dict, tor: dict, vp: dict, lib: dict) -> list[dict]:
    detail = {
        "Plex": f"{lib.get('movies', '?')} movies · {lib.get('shows', '?')} shows" if lib else "Movies, TV, music",
        "Radarr": f"Movies · {counts.get('radarr_missing', '?')} missing",
        "Sonarr": f"TV · {counts.get('sonarr_missing', '?')} wanted",
        "Lidarr": f"Music · {counts.get('lidarr_artists', '?')} artists",
        "Prowlarr": f"{counts.get('prowlarr_indexers', '?')} indexers",
        "qBittorrent": f"{tor.get('seeding', '?')} seeding",
        "VPN": f"NordVPN · {vp.get('city') or '?'}, {vp.get('country') or '?'}" if vp.get("ip") else "NordVPN · no tunnel",
    }
    with ThreadPoolExecutor(8) as ex:
        up = list(ex.map(lambda s: reachable(s[3].split(":")[0], int(s[3].split(":")[1])), SERVICES))
    return [{"name": n, "icon": ic, "desc": detail.get(n, blurb), "port": port, "up": ok}
            for (n, ic, blurb, _h, port, _k), ok in zip(SERVICES, up)]


def machines(peers: dict) -> list[dict]:
    with ThreadPoolExecutor(8) as ex:
        up = list(ex.map(lambda m: reachable(m[4], m[6]), MACHINES))
    return [{"name": n, "role": role, "icon": ic, "host": f"{host}.{TAILNET}", "ip": ip, "user": user,
             "online": peers[ip]["online"] if ip in peers else ok, "last_seen": (peers.get(ip) or {}).get("last_seen"),
             "links": [(label, url.format(ts=TAILNET)) for label, url in links]}
            for (n, role, ic, host, ip, user, _p, links), ok in zip(MACHINES, up)]


def host() -> dict:
    """Mac stats from host-stats.py; stale after 5 minutes means the launchd job stopped."""
    d = json.loads(HOST_JSON.read_text())
    d["stale"] = time.time() - d["time"] > 300
    return d


class DockerConn(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(DOCKER_SOCK)


def docker(path: str):
    c = DockerConn("docker")
    c.request("GET", path)
    return json.loads(c.getresponse().read())


def containers() -> list[dict]:
    out = []
    for c in docker('/containers/json?all=1&filters={"label":["com.docker.compose.project=media-stack"]}'):
        name = c["Names"][0].lstrip("/")
        i = docker(f"/containers/{name}/json")
        health = (i["State"].get("Health") or {}).get("Status")
        out.append({"name": name, "state": c["State"], "status": c["Status"], "health": health,
                    "restarts": i.get("RestartCount", 0), "started": i["State"].get("StartedAt", "")[:19]})
    return sorted(out, key=lambda c: (c["state"] == "running" and c["health"] != "unhealthy", c["name"]))


def backups() -> dict:
    """Last settings archive and what the log says happened to it, plus the last cloud sync."""
    tars = sorted(BACKUPS.glob("settings-*.tar.gz"), key=lambda f: f.stat().st_mtime)
    log = (BACKUPS / "backup.log").read_text(errors="replace").splitlines() if (BACKUPS / "backup.log").exists() else []
    last = tars[-1] if tars else None
    lines = [ln for ln in log if last and last.name in ln]
    cloud = [ln for ln in log if "cloud sync" in ln and "still running" not in ln]
    running = None
    try:
        i = docker("/containers/media-cloud-upload/json")
        if i["State"]["Running"]:
            text = (BACKUPS / "cloud.log").read_text(errors="replace")
            prog = re.findall(r"Transferred:\s+(\d+) / (\d+), (\d+)%", text)
            running = {"since": i["State"]["StartedAt"][:19], "pct": int(prog[-1][2]) if prog else None,
                       "files": f"{prog[-1][0]} of {prog[-1][1]} files" if prog else None}
    except Exception:
        pass
    return {
        "cloud_running": running,
        "last": last.stat().st_mtime if last else None, "size": last.stat().st_size if last else 0, "count": len(tars),
        "on_disk": any("_backups/settings" in ln for ln in lines),
        "on_drive": any(ln.rstrip().endswith(".tar.gz") and "gcrypt:" in ln for ln in lines),
        "cloud_sync": cloud[-1][:19] if cloud else None, "cloud_ok": bool(cloud) and "done" in cloud[-1],
    }


def sites() -> list[dict]:
    out = []
    for name, url in SITES:
        t = time.time()
        try:
            with urlopen(Request(url, method="HEAD", headers={"User-Agent": "dashboard"}), timeout=8) as r:
                code = r.status
        except Exception as e:  # HTTP errors still mean the site answered
            code = getattr(e, "code", None)
        out.append({"name": name, "url": url, "up": code is not None and code < 500, "code": code,
                    "ms": round((time.time() - t) * 1000)})
    return out


def collect() -> dict:
    out: dict = {"errors": {}}

    def run(name, fn, *a):
        try:
            out[name] = fn(*a)
        except Exception as e:  # one failing source must not blank the page
            out["errors"][name] = f"{type(e).__name__}: {e}"[:160]
            out[name] = None

    with ThreadPoolExecutor(8) as ex:
        jobs = {ex.submit(run, n, f) for n, f in (("recent", plex_recent), ("playing", now_playing), ("requests", requests_recent), ("watch", watch_next), ("listen", listen_next), ("counts", plex_counts), ("queue", queue),
                                                   ("arr", arr_counts), ("torrents", torrents), ("vpn", vpn),
                                                   ("storage", storage), ("nas", nas), ("sites", sites), ("host", host),
                                                   ("containers", containers), ("backups", backups))}
        for j in jobs:
            j.result()
    run("machines", machines, (out["host"] or {}).get("peers", {}))
    run("services", services, out["arr"] or {}, out["torrents"] or {}, out["vpn"] or {}, out["counts"] or {})
    out["ok"] = True
    out["updated"] = time.time()
    return out


def refresher():
    global state
    while True:
        snap = collect()
        with state_lock:
            state = snap
        if len(posters) > 200:
            posters.clear()
        time.sleep(REFRESH_S)


# ---- http ----


def poster(path: str, w: str = "185") -> bytes:
    """Plex thumb (/library/...) or TMDB poster/backdrop (/xyz.jpg, w185 or w1280), fetched once and kept in memory."""
    key = f"{w}{path}"
    if key not in posters:
        url = (f"{PLEX}/photo/:/transcode?width=320&height=480&minSize=1&upscale=1&url={quote(path, safe='')}&X-Plex-Token={PLEX_TOKEN}"
               if path.startswith("/library/") else f"https://image.tmdb.org/t/p/w{w}{path}")
        posters[key] = get(url, timeout=15)
    return posters[key]


MIME = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
        ".png": "image/png", ".json": "application/json"}


def poster_image(q: dict) -> bytes:
    p, w = q.get("p", [""])[0], q.get("w", ["185"])[0]
    if not p.startswith("/") or ".." in p or w not in ("185", "1280"):
        raise ValueError(p)
    return poster(p, w)


def cover_image(q: dict) -> bytes:
    """A shelf book's cover, same-origin as a JPEG: the iPad would not load Audiobookshelf's own."""
    book = q.get("id", [""])[0]
    if not re.fullmatch(r"[\w-]+", book):
        raise ValueError(book)
    return get(f"{ABS}/api/items/{book}/cover?width=400&format=jpeg")


def art_image(q: dict) -> bytes:
    """Media Index's poster for one item on disk, same-origin like the covers."""
    return get("http://media-index:8686/api/poster?item=" + quote(q.get("item", [""])[0]))


IMAGES = {"/poster": poster_image, "/cover": cover_image, "/art": art_image}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body: bytes, ctype: str, status=HTTPStatus.OK, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def send_image(self, fetch, q: dict):
        try:
            return self.send(fetch(q), "image/jpeg", cache="public, max-age=86400")
        except ValueError:
            return self.send(b"bad", "text/plain", HTTPStatus.BAD_REQUEST)
        except Exception:
            return self.send(b"", "image/jpeg", HTTPStatus.BAD_GATEWAY)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/state":
            with state_lock:
                body = json.dumps(state).encode()
            return self.send(body, "application/json")
        if u.path == "/api/search":
            return self.send(json.dumps(search(parse_qs(u.query).get("q", [""])[0])).encode(), "application/json")
        if u.path == "/api/title":
            q = parse_qs(u.query)
            kind, tmdb = q.get("type", [""])[0], q.get("tmdb", [""])[0]
            if kind not in ("movie", "show") or not tmdb.isdigit():
                return self.send(b"bad", "text/plain", HTTPStatus.BAD_REQUEST)
            try:
                return self.send(json.dumps(title(kind, tmdb)).encode(), "application/json")
            except Exception:
                return self.send(b"{}", "application/json", HTTPStatus.BAD_GATEWAY)
        if u.path in IMAGES:
            return self.send_image(IMAGES[u.path], parse_qs(u.query))
        f = STATIC / ("index.html" if u.path == "/" else u.path.lstrip("/"))
        if f.is_file() and STATIC in f.resolve().parents:
            cache = "no-store" if f.suffix == ".html" else "public, max-age=86400"
            return self.send(f.read_bytes(), MIME.get(f.suffix, "application/octet-stream"), cache=cache)
        self.send(b"not found", "text/plain", HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    threading.Thread(target=refresher, daemon=True).start()
    print(f"dashboard on :{PORT}", flush=True)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
