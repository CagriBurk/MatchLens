import numpy as np
import pandas as pd

from data_pipeline.db import connect
from matchlens import selections

TYPICAL_BOOK = 1.15
SURPRISE_KEYS = ("goals_6plus", "htft_1/2", "htft_2/1", "both_halves_over_1.5")
SURPRISE_SIZE = 10
RESULT_COMBOS = tuple(k for k in selections.COMBOS if k.split("&")[0] in selections.RESULTS and ("btts_yes" in k or "over" in k))
COUPONS = {
    "blue": {"odds": (1.35, 1.65), "target": 0.20, "min_legs": 2, "max_legs": 6, "prefer": ()},
    "yellow": {"odds": (1.70, 2.40), "target": 0.06, "min_legs": 2, "max_legs": 6, "prefer": ()},
    "red": {"odds": (2.50, 4.50), "target": 0.02, "min_legs": 2, "max_legs": 4, "prefer": RESULT_COMBOS},
}
SCHEMA = """
CREATE TABLE IF NOT EXISTS coupon_log (
    day TEXT NOT NULL, coupon TEXT NOT NULL, leg INTEGER NOT NULL,
    event_id TEXT, league TEXT, kickoff_utc TEXT, home_team TEXT, away_team TEXT,
    key TEXT, odds REAL, mbs INTEGER, p_model REAL, p_twin REAL, p_safe REAL, p_book REAL, value INTEGER, created_at TEXT,
    home_goals REAL, away_goals REAL, outcome REAL, settled_at TEXT,
    PRIMARY KEY (day, coupon, leg)
)
"""
FIELDS = ["day", "coupon", "leg", "event_id", "league", "kickoff_utc", "home_team", "away_team", "key", "odds", "mbs",
          "p_model", "p_twin", "p_safe", "p_book", "value", "created_at"]


def book_probability(offer):
    fair = getattr(offer, "fair", None)
    return float(fair) if fair is not None and not pd.isna(fair) else 1 / (float(offer.odds) * TYPICAL_BOOK)


def candidates(records, offers):
    if records.empty or offers.empty:
        return pd.DataFrame()
    info = records.assign(event_id=records["event_id"].astype(str)).set_index("event_id")
    rows = []
    for offer in offers.itertuples():
        if offer.event_id not in info.index:
            continue
        record = info.loc[offer.event_id]
        p_model, p_twin = record.get(offer.key), record.get(f"twin_{offer.key}")
        if p_model is None or p_twin is None or pd.isna(p_model) or pd.isna(p_twin):
            continue
        p_safe = min(float(p_model), float(p_twin))
        rows.append({"event_id": offer.event_id, "league": record["league"], "kickoff_utc": record["kickoff_utc"],
                     "home_team": record["home_team"], "away_team": record["away_team"], "key": offer.key,
                     "odds": float(offer.odds), "mbs": int(offer.mbs or 1), "p_model": float(p_model), "p_twin": float(p_twin),
                     "p_safe": p_safe, "p_book": book_probability(offer), "ratio": p_safe * float(offer.odds)})
    return pd.DataFrame(rows)


def build(cands, odds, target, min_legs, max_legs, prefer=()):
    low, high = odds
    pool = cands[cands["odds"].between(low, high) & (cands["p_safe"] >= cands["p_book"]) & (cands["mbs"] <= max_legs)]
    pool = pool[~pool["key"].isin(SURPRISE_KEYS)].copy()
    pool["value"] = pool["ratio"] >= 1
    pool["preferred"] = pool["key"].isin(prefer)
    pool = pool.sort_values(["value", "preferred", "ratio", "p_safe"], ascending=False)
    legs, used, hit = [], set(), 1.0
    for row in pool.to_dict("records"):
        if len(legs) >= max_legs:
            break
        if row["event_id"] in used or (len(legs) >= min_legs and hit * row["p_safe"] < target):
            continue
        legs.append(row)
        used.add(row["event_id"])
        hit *= row["p_safe"]
    while legs and len(legs) < max(leg["mbs"] for leg in legs):
        legs.remove(max(legs, key=lambda leg: (leg["mbs"], -leg["ratio"])))
    return legs if len(legs) >= min_legs else []


def surprises(cands, size=SURPRISE_SIZE):
    pool = cands[cands["key"].isin(SURPRISE_KEYS)].sort_values(["ratio", "p_safe"], ascending=False)
    pool = pool.assign(value=pool["ratio"] >= 1)
    return pool.drop_duplicates(["event_id", "key"]).head(size).to_dict("records")


def make(records, offers):
    cands = candidates(records, offers)
    if cands.empty:
        return {}
    made = {name: build(cands, **config) for name, config in COUPONS.items()}
    made["surprise"] = surprises(cands)
    return made


def summary(legs):
    odds = float(np.prod([leg["odds"] for leg in legs])) if legs else np.nan
    hit = float(np.prod([leg["p_safe"] for leg in legs])) if legs else np.nan
    return odds, hit


def ensure_schema(conn):
    conn.execute(SCHEMA)
    if "p_book" not in {row[1] for row in conn.execute("PRAGMA table_info(coupon_log)")}:
        conn.execute("ALTER TABLE coupon_log ADD COLUMN p_book REAL")


def exists(day):
    with connect() as conn:
        ensure_schema(conn)
        return conn.execute("SELECT 1 FROM coupon_log WHERE day = ? LIMIT 1", (str(day),)).fetchone() is not None


def generate(day, records, offers, now=None, force=False):
    if exists(day) and not force:
        return 0
    now = now or pd.Timestamp.now(tz="UTC")
    upcoming = records[pd.to_datetime(records["kickoff_utc"], utc=True) > now]
    made = make(upcoming, offers)
    rows = []
    for coupon, legs in made.items():
        for i, leg in enumerate(legs, start=1):
            rows.append({**{k: leg[k] for k in FIELDS if k in leg}, "day": str(day), "coupon": coupon, "leg": i,
                         "value": int(leg["ratio"] >= 1), "created_at": now.isoformat()})
    with connect() as conn:
        ensure_schema(conn)
        conn.execute("DELETE FROM coupon_log WHERE day = ?", (str(day),))
        conn.executemany(f"INSERT INTO coupon_log ({', '.join(FIELDS)}) VALUES ({', '.join(':' + f for f in FIELDS)})", rows)
    return len(rows)


def leg_outcome(key, match):
    hg, ag = match["home_goals"], match["away_goals"]
    full = selections.full_time(hg, ag)
    if key in full:
        return float(full[key])
    if not match["events_consistent"] or pd.isna(match["ht_home"]) or pd.isna(match["ht_away"]):
        return None
    half = selections.half_time(hg, ag, match["ht_home"], match["ht_away"])
    return float(half[key]) if key in half else None


def settle(matches, now=None):
    now = now or pd.Timestamp.now(tz="UTC")
    with connect() as conn:
        ensure_schema(conn)
        pending = pd.read_sql_query("SELECT day, coupon, leg, event_id, key FROM coupon_log WHERE settled_at IS NULL", conn)
        if pending.empty:
            return 0
        done = matches[matches["state"].eq("post")].assign(event_id=lambda d: d["event_id"].astype(str)).set_index("event_id")
        updates = []
        for leg in pending.itertuples():
            if leg.event_id not in done.index:
                continue
            match = done.loc[leg.event_id]
            outcome = leg_outcome(leg.key, match) if match["regular"] else None
            updates.append((match["home_goals"], match["away_goals"], outcome, now.isoformat(), leg.day, leg.coupon, leg.leg))
        conn.executemany("UPDATE coupon_log SET home_goals = ?, away_goals = ?, outcome = ?, settled_at = ? "
                         "WHERE day = ? AND coupon = ? AND leg = ?", updates)
    return len(updates)


def load(day=None):
    with connect() as conn:
        ensure_schema(conn)
        query, params = ("SELECT * FROM coupon_log WHERE day = ? ORDER BY coupon, leg", (str(day),)) if day else ("SELECT * FROM coupon_log", ())
        return pd.read_sql_query(query, conn, params=params, dtype={"event_id": str})


def days():
    with connect() as conn:
        ensure_schema(conn)
        return [row[0] for row in conn.execute("SELECT DISTINCT day FROM coupon_log ORDER BY day")]
