#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import datetime as dt
import html as htmlmod
import json
import os
import platform
import re
import shutil
import ssl
import sys
import subprocess
import tempfile
import threading
import time
import traceback
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "21.0.0"
APP_NAME = "HorizonXI_Summoner_Unlock_Tracker"

# PyInstaller --onefile extracts bundled files to sys._MEIPASS.
# Keep bundled/read-only resources separate from writable persistent data.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    RESOURCE_ROOT = Path(sys._MEIPASS)
    SOURCE_ROOT = Path(sys.executable).resolve().parent
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        DATA_ROOT = Path(local_appdata) / APP_NAME
    else:
        DATA_ROOT = Path.home() / f".{APP_NAME}"
else:
    RESOURCE_ROOT = Path(__file__).resolve().parent
    SOURCE_ROOT = RESOURCE_ROOT.parent
    DATA_ROOT = SOURCE_ROOT

HTML_FILE = RESOURCE_ROOT / "Carbuncle_Rainbow_Tracker.html"
CACHE_DIR = DATA_ROOT / "_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WEATHER_SPECIAL = "https://horizonffxi.wiki/Special:WeatherForecast"
DIGGING_SPECIAL = "https://horizonffxi.wiki/Special:DiggingWeatherForecast"

# Display name -> the actual value expected by Horizon's zoneNameDropDown.
ZONE_QUERY = {
    "Batallia Downs": "Batallia_Downs",
    "Beaucedine Glacier": "Beaucedine_Glacier",
    "Buburimu Peninsula": "Buburimu_Peninsula",
    "Cape Teriggan": "Cape_Teriggan",
    "East Sarutabaruta": "East_Sarutabaruta",
    "Eastern Altepa Desert": "Eastern_Altepa_Desert",
    "Jugner Forest": "Jugner_Forest",
    "Konschtat Highlands": "Konschtat_Highlands",
    "La Theine Plateau": "La_Theine_Plateau",
    "Meriphataud Mountains": "Meriphataud_Mountains",
    "North Gustaberg": "North_Gustaberg",
    "Pashhow Marshlands": "Pashhow_Marshlands",
    "Rolanberry Fields": "Rolanberry_Fields",
    "Sauromugue Champaign": "Sauromugue_Champaign",
    "Tahrongi Canyon": "Tahrongi_Canyon",
    "The Sanctuary of Zi'Tah": "The_Sanctuary_of_ZiTah",
    "Valkurm Dunes": "Valkurm_Dunes",
    "Valley of Sorrows": "Valley_of_Sorrows",
    "West Sarutabaruta": "West_Sarutabaruta",
    "Western Altepa Desert": "Western_Altepa_Desert",
    "Xarcabard": "Xarcabard",
    "Yhoator Jungle": "Yhoator_Jungle",
    "Yuhtunga Jungle": "Yuhtunga_Jungle",
}
ZONES = list(ZONE_QUERY)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0 Safari/537.36"
)
VANA_DAY_SECONDS = 3456
VANA_EPOCH_UNIX = 1009810800  # 2002-01-01 00:00 JST == Vana midnight
LOCK = threading.Lock()
CACHE = {}

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")

def log_line(msg):
    print(f"{utc_now()} {msg}")

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")

def vana_day():
    return int((time.time() - VANA_EPOCH_UNIX) // VANA_DAY_SECONDS)

def clean(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(s or "")).strip()

class Rows(HTMLParser):
    """Dependency-free table row extractor."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.depth = 1
        elif self.cell is not None:
            self.depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.cell is not None and tag in ("td", "th") and self.depth <= 1:
            self.row.append(clean("".join(self.cell)))
            self.cell = None
            self.depth = 0
        elif self.cell is not None and self.depth > 1:
            self.depth -= 1

        if tag == "tr" and self.row is not None:
            if self.cell is not None:
                self.row.append(clean("".join(self.cell)))
                self.cell = None
                self.depth = 0
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

def fetch(url, referer=None, timeout=20):
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "close",
    }
    if referer:
        headers["Referer"] = referer

    start = time.perf_counter()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            data = r.read()
            meta = {
                "status": getattr(r, "status", None),
                "content_type": r.headers.get("Content-Type", ""),
                "content_length_header": r.headers.get("Content-Length"),
                "final_url": r.geturl(),
                "bytes": len(data),
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            }
            return data, meta
    except Exception:
        raise

def decode(data, content_type):
    m = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "", re.I)
    enc = m.group(1) if m else "utf-8"
    try:
        return data.decode(enc, errors="replace"), enc
    except LookupError:
        return data.decode("utf-8", errors="replace"), "utf-8-fallback"

def source_url(zone_display):
    zone_value = ZONE_QUERY[zone_display]
    # Horizon extension source uses 8 as ** All Weather Types **.
    query = urllib.parse.urlencode(
        {"weatherTypeDropDown": "8", "zoneNameDropDown": zone_value},
        quote_via=urllib.parse.quote_plus,
    )
    return WEATHER_SPECIAL + "?" + query

def parse_forecast_days(page, expected_zone_value, max_day=7):
    p = Rows()
    p.feed(page)

    # Horizon extension emits:
    # 0 zone
    # 1 Vana-days from today (0 == today, 1 == next Vana day, ...)
    # 2 Earth time
    # 3 Vana weekday
    # 4 Moon phase
    # 5 Normal
    # 6 Common
    # 7 Rare
    data_rows = [r for r in p.rows if len(r) >= 8]

    def zone_key(value):
        return clean(value).replace(" ", "_").lower()

    matching = [r for r in data_rows if zone_key(r[0]) == expected_zone_value.lower()]
    candidates = matching if matching else data_rows

    days = {}
    for r in candidates:
        try:
            offset = int(clean(r[1]))
        except (TypeError, ValueError):
            continue
        if 0 <= offset <= max_day and offset not in days:
            days[offset] = {
                "offset": offset,
                "earth_time": clean(r[2]),
                "vana_day": clean(r[3]),
                "moon": clean(r[4]),
                "normal": clean(r[5]),
                "common": clean(r[6]),
                "rare": clean(r[7]),
            }

    diag = {
        "row_count": len(p.rows),
        "data_row_count": len(data_rows),
        "matching_zone_rows": len(matching),
        "expected_zone_value": expected_zone_value,
        "available_offsets": sorted(days),
        "first_12_rows": p.rows[:12],
    }

    if 0 not in days:
        raise ValueError(
            "No forecast row with Vana-days-from-today = 0. Diagnostics: " +
            json.dumps(diag, ensure_ascii=False)[:3000]
        )

    return days, diag

def parse_today(page, expected_zone_value):
    days, diag = parse_forecast_days(page, expected_zone_value, max_day=0)
    d = days[0]
    row = [
        expected_zone_value,
        "0",
        d["earth_time"],
        d["vana_day"],
        d["moon"],
        d["normal"],
        d["common"],
        d["rare"],
    ]
    return d["normal"], d["common"], d["rare"], row, diag

def fetch_uncached(zone):
    url = source_url(zone)
    qzone = ZONE_QUERY[zone]
    try:
        data, meta = fetch(url, referer=DIGGING_SPECIAL)
        page, _encoding = decode(data, meta.get("content_type", ""))
        days, _diag = parse_forecast_days(page, qzone, max_day=14)
        today = days[0]
        future = [days[i] for i in range(1, 15) if i in days]
        return {
            "normal": today["normal"],
            "common": today["common"],
            "rare": today["rare"],
            "earth_time": today["earth_time"],
            "vana_day": today["vana_day"],
            "moon": today["moon"],
            "future": future,
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

def fetch_zone(zone, force=False):
    day = vana_day()
    with LOCK:
        entry = CACHE.get(zone)
        if not force and entry and entry["day"] == day:
            result = dict(entry["result"])
            result["cache_hit"] = True
            return result, True

    result = fetch_uncached(zone)
    if "error" not in result:
        with LOCK:
            CACHE[zone] = {"day": day, "result": dict(result)}
    return result, False

def fetch_all(force=False):
    out = {}
    all_cached = True
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_zone, z, force): z for z in ZONES}
        for future in concurrent.futures.as_completed(futures):
            zone = futures[future]
            try:
                result, cached = future.result()
            except Exception as exc:
                result, cached = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "source_url": source_url(zone),
                    "query_zone": ZONE_QUERY[zone],
                }, False
                log_line(f"[WORKER FAIL] {zone}: {traceback.format_exc()}")
            out[zone] = result
            all_cached = all_cached and cached

    return out, all_cached

def _valid_map(data):
    if not data or len(data) < 10000:
        return False
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"GIF87a")
        or data.startswith(b"GIF89a")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"RIFF")  # WEBP container, validated loosely
    )

MAP_CACHE = CACHE_DIR / "shakhrami-map2.jpg"

def _candidate_fancychat_maps():
    candidates = []

    # Known/common HorizonXI install roots. Checking a few drive letters is cheap and
    # avoids recursively scanning a whole disk.
    roots = []
    env_root = os.environ.get("HORIZONXI_ROOT")
    if env_root:
        roots.append(Path(env_root))

    for drive in ("C", "D", "E", "F", "G"):
        roots.append(Path(f"{drive}:/HorizonXI"))

    # Also support running this tracker from somewhere inside a HorizonXI tree.
    for p in [SOURCE_ROOT, *SOURCE_ROOT.parents]:
        if p.name.lower() == "horizonxi":
            roots.append(p)

    seen = set()
    for root in roots:
        key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)

        for addon_name in ("FancyChat", "fancychat"):
            base = root / "Game" / "addons" / addon_name / "maps" / "Maze of Shakhrami"
            # Prefer the clean base Map 2 for our own overlay.
            candidates.append((
                base / "Maps" / "maze_of_shakhrami_2.jpg",
                f"FancyChat base Map 2 ({base / 'Maps' / 'maze_of_shakhrami_2.jpg'})"
            ))
            # If the base map is absent but the NM map exists, it is still useful.
            candidates.append((
                base / "Notorious_Monsters" / "MazeofShakhramiNMs.jpg",
                f"FancyChat NM map ({base / 'Notorious_Monsters' / 'MazeofShakhramiNMs.jpg'})"
            ))
            candidates.append((
                base / "Notorious_Monsters" / "MazeofShakhramiNM2.jpg",
                f"FancyChat NM Map 2 ({base / 'Notorious_Monsters' / 'MazeofShakhramiNM2.jpg'})"
            ))
    return candidates

def redetect_map():
    for path, label in _candidate_fancychat_maps():
        try:
            if path.is_file():
                data = path.read_bytes()
                if _valid_map(data):
                    MAP_CACHE.write_bytes(data)
                    return {"available": True, "bytes": len(data)}
        except Exception:
            pass
    if MAP_CACHE.is_file():
        try:
            data = MAP_CACHE.read_bytes()
            if _valid_map(data):
                return {"available": True, "bytes": len(data)}
        except Exception:
            pass
    return {"available": False, "bytes": 0}

def map_status():
    if MAP_CACHE.is_file():
        try:
            data = MAP_CACHE.read_bytes()
            if _valid_map(data):
                return {"available": True, "bytes": len(data)}
        except Exception:
            pass
    return redetect_map()

def map_bytes():
    st = map_status()
    if not st["available"]:
        log_line("[MAP MISSING] No local FancyChat/base map or user-selected map found. Forecasts unaffected.")
        raise FileNotFoundError(
            "No local Shakhrami map found. Use 'Choose local map image' in the tracker."
        )
    data = MAP_CACHE.read_bytes()
    return data, "image/jpeg"

def save_uploaded_map(data, filename, content_type):
    if len(data) > 12 * 1024 * 1024:
        raise ValueError("Map file is larger than 12 MB.")
    if not _valid_map(data):
        raise ValueError("Selected file is not a supported PNG/JPEG/WEBP image.")
    MAP_CACHE.write_bytes(data)
    return map_status()

class Handler(BaseHTTPRequestHandler):
    server_version = "HorizonCarbuncleTracker/20"

    def log_message(self, fmt, *args):
        log_line("[HTTP] " + (fmt % args))

    def sendb(self, status, data, ctype, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def sendj(self, status, obj):
        self.sendb(
            status,
            json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def read_json_body(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        raw = self.rfile.read(min(n, 256 * 1024)) if n else b"{}"
        return json.loads(raw.decode("utf-8", errors="replace"))

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/map/redetect":
            try:
                st = redetect_map()
                return self.sendj(200, {"ok": True, **st})
            except Exception as exc:
                log_line("[MAP REDETECT FAIL] " + traceback.format_exc())
                return self.sendj(500, {"ok": False, "error": str(exc)})

        if u.path == "/api/map/upload":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0:
                    return self.sendj(400, {"ok": False, "error": "Empty upload"})
                if n > 12 * 1024 * 1024:
                    return self.sendj(413, {"ok": False, "error": "Map file is larger than 12 MB"})
                data = self.rfile.read(n)
                filename = urllib.parse.unquote(self.headers.get("X-Filename", "local-map"))
                ctype = self.headers.get("Content-Type", "application/octet-stream")
                st = save_uploaded_map(data, filename, ctype)
                return self.sendj(200, {"ok": True, **st})
            except Exception as exc:
                log_line("[MAP UPLOAD FAIL] " + traceback.format_exc())
                return self.sendj(400, {"ok": False, "error": str(exc)})

        return self.sendj(404, {"ok": False, "error": "Not found"})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path

        if p in ("/", "/Carbuncle_Rainbow_Tracker.html"):
            return self.sendb(200, HTML_FILE.read_bytes(), "text/html; charset=utf-8")

        if p == "/api/health":
            return self.sendj(200, {
                "ok": True,
                "tracker_version": VERSION,
                "vana_day": vana_day(),
            })

        if p == "/api/forecasts":
            try:
                # A browser scan must not reuse forecasts cached before a Wiki row rollover.
                force = (urllib.parse.parse_qs(u.query).get("fresh") or ["0"])[0] == "1"
                forecasts, cached = fetch_all(force=force)
                return self.sendj(200, {
                    "ok": True,
                    "tracker_version": VERSION,
                    "vana_day": vana_day(),
                    "cached": cached,
                    "forecasts": forecasts,
                })
            except Exception as exc:
                log_line("[API FORECASTS FAIL] " + traceback.format_exc())
                return self.sendj(502, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})

        if p == "/api/forecast":
            zone = (urllib.parse.parse_qs(u.query).get("zone") or [""])[0]
            if zone not in ZONES:
                return self.sendj(400, {"ok": False, "error": "Unknown zone"})
            result, cached = fetch_zone(zone)
            return self.sendj(200, {
                "ok": "error" not in result,
                "cached": cached,
                "zone": zone,
                **result,
            })

        if p == "/api/map/status":
            try:
                return self.sendj(200, {"ok": True, **map_status()})
            except Exception as exc:
                return self.sendj(500, {"ok": False, "available": False, "error": str(exc)})

        if p == "/assets/shakhrami-map2.jpg":
            try:
                data, ctype = map_bytes()
                return self.sendb(200, data, ctype)
            except Exception as exc:
                # Map failure is isolated from /api/forecasts.
                return self.sendb(502, ("MAP ONLY: " + str(exc)).encode("utf-8"), "text/plain; charset=utf-8")

        return self.sendb(404, b"Not found", "text/plain; charset=utf-8")

def self_test():
    if not HTML_FILE.is_file():
        raise RuntimeError(f"Bundled HTML file not found: {HTML_FILE}")
    sample = """
    <table>
      <tr><th>Zone</th><th>Vana-days</th><th>Earth Time</th><th>Day</th><th>Moon</th><th>Normal</th><th>Common</th><th>Rare</th></tr>
      <tr><td>Batallia_Downs</td><td>0</td><td>2026-10-06 13:00</td><td>Watersday</td><td>Full Moon</td><td>Clouds</td><td>Dust Storm</td><td>Rain</td></tr>
      <tr><td>Batallia_Downs</td><td>1</td><td>2026-10-06 13:57</td><td>Windsday</td><td>Full Moon</td><td>Gales</td><td>Clouds</td><td>Rain</td></tr>
      <tr><td>Batallia_Downs</td><td>7</td><td>2026-10-06 19:43</td><td>Firesday</td><td>Full Moon</td><td>Heat Waves</td><td>Clouds</td><td>Rain</td></tr>
      <tr><td>Batallia_Downs</td><td>14</td><td>2026-10-07 02:26</td><td>Firesday</td><td>Full Moon</td><td>Clouds</td><td>Gales</td><td>Rain</td></tr>
    </table>
    """
    n, c, r, row, diag = parse_today(sample, "Batallia_Downs")
    assert (n, c, r) == ("Clouds", "Dust Storm", "Rain")
    days, _ = parse_forecast_days(sample, "Batallia_Downs", max_day=7)
    assert days[1]["normal"] == "Gales"
    assert days[7]["normal"] == "Heat Waves"
    further, _ = parse_forecast_days(sample, "Batallia_Downs", max_day=14)
    assert further[14]["common"] == "Gales"
    assert source_url("Batallia Downs").endswith(
        "weatherTypeDropDown=8&zoneNameDropDown=Batallia_Downs"
    )
    assert ZONE_QUERY["The Sanctuary of Zi'Tah"] == "The_Sanctuary_of_ZiTah"
    candidates = _candidate_fancychat_maps()
    assert any("maze_of_shakhrami_2.jpg" in str(p).lower() for p, _ in candidates)

def main():
    self_test()
    log_line(f"[START] HorizonXI Carbuncle Rainbow Tracker v{VERSION}")
    log_line("[PARSER] weatherTypeDropDown=8; forecast offsets 0..7; weather columns=5,6,7 zero-based")

    server = None
    port = None
    for candidate in range(8765, 8780):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            pass

    if server is None:
        raise RuntimeError("No free port from 8765 to 8779")

    url = f"http://127.0.0.1:{port}/"
    print()
    print("HorizonXI Summoner Unlock Tracker v21")
    print("Browser URL:", url)
    print("Press Ctrl+C to stop.")
    print()

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log_line("[STOP] Ctrl+C")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
