"""Home dashboard: one page over the media stack, the NAS and every machine on the tailnet.

Standard library only. A background thread refreshes a JSON snapshot every REFRESH_S from the
services' own APIs and plain TCP probes; the page fetches it from /api/state. Plex posters are
proxied through /poster so the token never reaches the browser. Nothing here writes anywhere.
"""

from __future__ import annotations

import json
import os
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

# Services: name, icon, blurb, container host:port, published port (None = no page), API key env.
# Links are built in the browser from its own hostname plus the published port.
SERVICES = [
    ("Plex", "plex.svg", "Movies, TV, music", f"{ENV.get('HOST_ADDR', '')}:32400", 32400, None),
    ("Seerr", "jellyseerr.svg", "Request movies and TV", "seerr:5055", 5055, None),
    ("Audiobookshelf", "audiobookshelf.svg", "Audiobooks and podcasts", "audiobookshelf:80", 13378, None),
    ("AudioBookRequest", "📚", "Request audiobooks", "audiobookrequest:8000", 8000, None),
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


def machines() -> list[dict]:
    with ThreadPoolExecutor(8) as ex:
        up = list(ex.map(lambda m: reachable(m[4], m[6]), MACHINES))
    return [{"name": n, "role": role, "icon": ic, "host": f"{host}.{TAILNET}", "ip": ip, "user": user, "online": ok,
             "links": [(label, url.format(ts=TAILNET)) for label, url in links]}
            for (n, role, ic, host, ip, user, _p, links), ok in zip(MACHINES, up)]


def collect() -> dict:
    out: dict = {"errors": {}}

    def run(name, fn, *a):
        try:
            out[name] = fn(*a)
        except Exception as e:  # one failing source must not blank the page
            out["errors"][name] = f"{type(e).__name__}: {e}"[:160]
            out[name] = None

    with ThreadPoolExecutor(8) as ex:
        jobs = {ex.submit(run, n, f) for n, f in (("recent", plex_recent), ("counts", plex_counts), ("queue", queue),
                                                   ("arr", arr_counts), ("torrents", torrents), ("vpn", vpn),
                                                   ("storage", storage), ("nas", nas), ("machines", machines))}
        for j in jobs:
            j.result()
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


def poster(path: str) -> bytes:
    if path not in posters:
        url = f"{PLEX}/photo/:/transcode?width=320&height=480&minSize=1&upscale=1&url={quote(path, safe='')}&X-Plex-Token={PLEX_TOKEN}"
        posters[path] = get(url, timeout=15)
    return posters[path]


MIME = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
        ".png": "image/png", ".json": "application/json"}


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

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/state":
            with state_lock:
                body = json.dumps(state).encode()
            return self.send(body, "application/json")
        if u.path == "/poster":
            p = parse_qs(u.query).get("p", [""])[0]
            if not p.startswith("/library/"):
                return self.send(b"bad", "text/plain", HTTPStatus.BAD_REQUEST)
            try:
                return self.send(poster(p), "image/jpeg", cache="public, max-age=86400")
            except Exception:
                return self.send(b"", "image/jpeg", HTTPStatus.BAD_GATEWAY)
        f = STATIC / ("index.html" if u.path == "/" else u.path.lstrip("/"))
        if f.is_file() and STATIC in f.resolve().parents:
            cache = "no-store" if f.suffix == ".html" else "public, max-age=86400"
            return self.send(f.read_bytes(), MIME.get(f.suffix, "application/octet-stream"), cache=cache)
        self.send(b"not found", "text/plain", HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    threading.Thread(target=refresher, daemon=True).start()
    print(f"dashboard on :{PORT}", flush=True)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
