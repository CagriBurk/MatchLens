import gzip
import json
import threading
import time

import requests

from data_pipeline.config import ESPN_RAW_DIR

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
SUMMARY_KEYS = ("header", "boxscore", "odds", "pickcenter", "gameInfo", "rosters")
MIN_INTERVAL_SECONDS = 0.15
SCOREBOARD_LIMIT = 1000

_session = requests.Session()
_session.headers["User-Agent"] = "Mozilla/5.0"
_throttle_lock = threading.Lock()
_last_request = [0.0]


def _throttle():
    with _throttle_lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.monotonic()


def get_json(path: str, params: dict, retries: int = 4):
    for attempt in range(retries):
        _throttle()
        try:
            response = _session.get(f"{BASE_URL}/{path}", params=params, timeout=20)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if response.status_code == 200:
            return response.json()
        if response.status_code in (400, 404):
            return None
        time.sleep(2 ** attempt)
    raise RuntimeError(f"ESPN request failed: {path} {params}")


def read_cache(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_cache(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    tmp.replace(path)


def scoreboard_path(league: str, year: int):
    return ESPN_RAW_DIR / "scoreboard" / league / f"{year}.json.gz"


def summary_path(league: str, event_id: str):
    return ESPN_RAW_DIR / "summary" / league / f"{event_id}.json.gz"


def fetch_scoreboard(league: str, year: int, refresh: bool = False) -> list:
    path = scoreboard_path(league, year)
    if path.exists() and not refresh:
        return read_cache(path)
    data = get_json(f"{league}/scoreboard", {"dates": year, "limit": SCOREBOARD_LIMIT})
    events = (data or {}).get("events", [])
    if len(events) >= SCOREBOARD_LIMIT:
        print(f"Warning: {league} {year} hit the scoreboard limit, results may be truncated")
    write_cache(path, events)
    return events


def summary_is_final(summary: dict) -> bool:
    competitions = summary.get("header", {}).get("competitions") or [{}]
    return competitions[0].get("status", {}).get("type", {}).get("state") == "post"


def fetch_summary(league: str, event_id: str, refresh: bool = False):
    path = summary_path(league, event_id)
    if path.exists() and not refresh:
        cached = read_cache(path)
        if summary_is_final(cached):
            return cached
    data = get_json(f"{league}/summary", {"event": event_id})
    if data is None:
        return None
    trimmed = {key: data.get(key) for key in SUMMARY_KEYS}
    write_cache(path, trimmed)
    return trimmed
