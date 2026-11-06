import gzip
import json
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

import pandas as pd
import requests

from data_pipeline.config import RAW_DIR
from data_pipeline.db import connect

URL = "https://bulten.nesine.com/api/bulten/getprebultenfull"
RAW = RAW_DIR / "nesine"
FOOTBALL = 1
MIN_ODDS = 1.01
MAX_KICKOFF_GAP = pd.Timedelta(minutes=20)
MIN_SIMILARITY = 0.55
MIN_MARGIN = 0.08
RESULT_ORDER = ("home", "draw", "away")
MARKETS = {
    1: {1: "home", 2: "draw", 3: "away"},
    3: {1: "dc_1x", 2: "dc_12", 3: "dc_x2"},
    7: {1: "ht_home", 2: "ht_draw", 3: "ht_away"},
    5: dict(enumerate([f"htft_{a}/{b}" for a in ("1", "X", "2") for b in ("1", "X", "2")], start=1)),
    11: {1: "under_1.5", 2: "over_1.5"},
    12: {1: "under_2.5", 2: "over_2.5"},
    13: {1: "under_3.5", 2: "over_3.5"},
    155: {1: "under_4.5", 2: "over_4.5"},
    38: {1: "btts_yes", 2: "btts_no"},
    209: {2: "ht_over_0.5"},
    14: {2: "ht_over_1.5"},
    43: {4: "goals_6plus"},
    342: {i + 1 + 3 * j: f"{r}&{side}_1.5" for j, side in enumerate(("under", "over")) for i, r in enumerate(RESULT_ORDER)},
    343: {i + 1 + 3 * j: f"{r}&{side}_2.5" for j, side in enumerate(("under", "over")) for i, r in enumerate(RESULT_ORDER)},
    414: {1 + 2 * i + j: f"{r}&btts_{s}" for i, r in enumerate(RESULT_ORDER) for j, s in enumerate(("yes", "no"))},
    446: {1: "btts_yes&under_2.5", 2: "btts_yes&over_2.5", 3: "btts_no&under_2.5", 4: "btts_no&over_2.5"},
    529: {1: "both_halves_over_1.5"},
}
COVERAGE = {3: 2.0}
EXPECTED_LINE = {11: 1.5, 12: 2.5, 13: 3.5, 155: 4.5, 209: 0.5, 14: 1.5, 342: 1.5, 343: 2.5, 446: 2.5}
NOISE = {"fc", "cf", "sc", "sk", "fk", "ac", "as", "afc", "cd", "ud", "sd", "rc", "if", "bk", "club", "de", "the", "calcio",
         "football", "futbol", "kulubu", "spor", "jk", "ss", "us", "ssc", "vfl", "vfb", "tsg", "fsv", "sv", "1", "rcd", "ca", "kv", "kaa", "krc"}


def fetch(now=None):
    now = now or datetime.now(timezone.utc)
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}, timeout=60)
    response.raise_for_status()
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{now:%Y-%m-%d_%H%M}.json.gz"
    with gzip.open(path, "wb") as handle:
        handle.write(response.content)
    return response.json(), now


def load_raw(path):
    with gzip.open(path, "rb") as handle:
        return json.loads(handle.read())


def events_and_offers(payload):
    leagues = {league["LID"]: league["N"] for league in payload["sg"].get("LA", [])}
    events, offers = [], []
    for event in payload["sg"]["EA"]:
        if event.get("TYPE") != FOOTBALL or not event.get("HN") or not event.get("AN"):
            continue
        code = event["C"]
        events.append({"code": code, "home": event["HN"], "away": event["AN"], "league_name": leagues.get(event.get("LC"), ""),
                       "kickoff": pd.Timestamp(event["ESD"], unit="ms", tz="UTC"), "event_mbs": event.get("EMBS")})
        for market in event.get("MA") or []:
            outcomes = MARKETS.get(market.get("MTID"))
            if not outcomes:
                continue
            expected = EXPECTED_LINE.get(market["MTID"])
            if expected is not None and abs(float(market.get("SOV", 0)) - expected) > 1e-9:
                continue
            prices = [o.get("O") for o in market.get("OCA") or [] if o.get("O") and o["O"] > MIN_ODDS]
            book = sum(1 / price for price in prices) / COVERAGE.get(market["MTID"], 1.0)
            complete = len(prices) == len(market.get("OCA") or [])
            for outcome in market.get("OCA") or []:
                key, odds = outcomes.get(outcome.get("N")), outcome.get("O")
                if key and odds and odds > MIN_ODDS:
                    fair = (1 / odds) / book if complete and book > 1 else None
                    offers.append({"code": code, "key": key, "odds": float(odds), "mbs": market.get("MBS"), "fair": fair})
    return pd.DataFrame(events), pd.DataFrame(offers)


def normalize(name):
    text = unicodedata.normalize("NFKD", str(name).replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
    tokens = [t for t in re.split(r"[^a-z0-9]+", text) if t and t not in NOISE]
    return " ".join(tokens)


def similarity(a, b):
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.95
    ta, tb = set(a.split()), set(b.split())
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return max(SequenceMatcher(None, a, b).ratio(), overlap * 0.9)


def match_events(fixtures, events):
    if fixtures.empty or events.empty:
        return pd.DataFrame(columns=["event_id", "code", "score"])
    rows = []
    kickoffs = pd.to_datetime(fixtures["kickoff_utc"], utc=True)
    for (_, fixture), kickoff in zip(fixtures.iterrows(), kickoffs):
        near = events[(events["kickoff"] - kickoff).abs() <= MAX_KICKOFF_GAP]
        scored = sorted(((similarity(fixture["home_team"], e.home) + similarity(fixture["away_team"], e.away)) / 2, e.code)
                        for e in near.itertuples())
        if not scored:
            continue
        best, code = scored[-1]
        runner = scored[-2][0] if len(scored) > 1 else 0.0
        if best >= MIN_SIMILARITY and best - runner >= MIN_MARGIN:
            rows.append({"event_id": str(fixture["event_id"]), "code": code, "score": best})
    matched = pd.DataFrame(rows, columns=["event_id", "code", "score"])
    return matched.sort_values("score", ascending=False).drop_duplicates("code")


def odds_for(fixtures, payload=None, now=None):
    if payload is None:
        payload, now = fetch(now)
    events, offers = events_and_offers(payload)
    matched = match_events(fixtures, events)
    if matched.empty or offers.empty:
        return pd.DataFrame(columns=["event_id", "code", "key", "odds", "mbs", "fair"]), matched
    table = matched.merge(offers, on="code")[["event_id", "code", "key", "odds", "mbs", "fair"]]
    table["fetched_at"] = (now or datetime.now(timezone.utc)).isoformat()
    return table, matched


def save(table):
    if table.empty:
        return 0
    with connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS nesine_odds (event_id TEXT, code INTEGER, key TEXT, odds REAL, mbs INTEGER, fetched_at TEXT, "
                     "fair REAL, PRIMARY KEY (event_id, key))")
        if "fair" not in {row[1] for row in conn.execute("PRAGMA table_info(nesine_odds)")}:
            conn.execute("ALTER TABLE nesine_odds ADD COLUMN fair REAL")
        conn.executemany("INSERT OR REPLACE INTO nesine_odds (event_id, code, key, odds, mbs, fetched_at, fair) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         table[["event_id", "code", "key", "odds", "mbs", "fetched_at", "fair"]].itertuples(index=False, name=None))
    return len(table)
