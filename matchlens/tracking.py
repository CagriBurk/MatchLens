import numpy as np
import pandas as pd

from data_pipeline.db import connect
from matchlens import odds

MIN_EV = 0.03
LOG_MARKETS = [
    "home", "draw", "away", "dc_1x", "dc_12", "dc_x2", "over_1.5", "over_2.5", "over_3.5", "btts_yes",
    "ht_over_0.5", "ht_over_1.5", "both_halves_over_1.5", "both_halves_btts", "goals_6plus", "early_goal_0_15",
    "htft_1/2", "htft_2/1",
]
HALF_MARKETS = {"ht_over_0.5", "ht_over_1.5", "both_halves_over_1.5", "both_halves_btts", "early_goal_0_15", "htft_1/2", "htft_2/1"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS prediction_log (
    event_id TEXT NOT NULL, market TEXT NOT NULL, league TEXT, kickoff_utc TEXT,
    home_team TEXT, away_team TEXT, lam_home REAL, lam_away REAL,
    model_p REAL, line REAL, b365 REAL, ev REAL, logged_at TEXT,
    home_goals REAL, away_goals REAL, outcome REAL, profit REAL, settled_at TEXT,
    PRIMARY KEY (event_id, market)
)
"""
UPSERT = """
INSERT INTO prediction_log (event_id, market, league, kickoff_utc, home_team, away_team, lam_home, lam_away,
                            model_p, line, b365, ev, logged_at)
VALUES (:event_id, :market, :league, :kickoff_utc, :home_team, :away_team, :lam_home, :lam_away,
        :model_p, :line, :b365, :ev, :logged_at)
ON CONFLICT(event_id, market) DO UPDATE SET
    kickoff_utc = excluded.kickoff_utc, lam_home = excluded.lam_home, lam_away = excluded.lam_away,
    model_p = excluded.model_p, line = excluded.line, b365 = excluded.b365, ev = excluded.ev,
    logged_at = excluded.logged_at
WHERE prediction_log.settled_at IS NULL
"""
MATCH_FIELDS = ["event_id", "league", "kickoff_utc", "home_team", "away_team", "lam_home", "lam_away"]


def clean(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return float(value) if isinstance(value, (np.floating, np.integer)) else value


def prediction_rows(records, candidates, logged_at):
    priced = {}
    if not candidates.empty:
        priced = {(c["event_id"], c["key"]): c for c in candidates.to_dict("records")}
    rows = []
    for record in records.to_dict("records"):
        base = {field: record[field] for field in MATCH_FIELDS}
        for market in LOG_MARKETS:
            offer = priced.get((record["event_id"], market), {})
            rows.append({**base, "market": market, "model_p": record[market], "line": None,
                         "b365": offer.get("b365"), "ev": offer.get("ev"), "logged_at": logged_at})
    if not candidates.empty:
        meta = records.set_index("event_id")[["lam_home", "lam_away"]].to_dict("index")
        for offer in candidates[candidates["key"].str.startswith("asian_")].to_dict("records"):
            base = {field: offer.get(field) for field in MATCH_FIELDS[:5]}
            rows.append({**base, **meta[offer["event_id"]], "market": offer["key"], "model_p": None,
                         "line": offer["line"], "b365": offer["b365"], "ev": offer["ev"], "logged_at": logged_at})
    return [{k: clean(v) for k, v in row.items()} for row in rows]


def log_predictions(records, candidates, now=None):
    if records.empty:
        return 0
    now = now or pd.Timestamp.now(tz="UTC")
    rows = prediction_rows(records, candidates, now.isoformat())
    rows = [r for r in rows if pd.Timestamp(r["kickoff_utc"]) > now]
    with connect() as conn:
        conn.execute(SCHEMA)
        conn.executemany(UPSERT, rows)
    return len(rows)


def market_outcome(market, match):
    hg, ag = match["home_goals"], match["away_goals"]
    total = hg + ag
    if market in HALF_MARKETS and not match["events_consistent"]:
        return None
    ht_h, ht_a = match["ht_home"], match["ht_away"]
    sh_h, sh_a = hg - ht_h, ag - ht_a
    outcomes = {
        "home": hg > ag, "draw": hg == ag, "away": hg < ag,
        "dc_1x": hg >= ag, "dc_12": hg != ag, "dc_x2": hg <= ag,
        "over_1.5": total > 1.5, "over_2.5": total > 2.5, "over_3.5": total > 3.5,
        "btts_yes": hg > 0 and ag > 0,
        "ht_over_0.5": ht_h + ht_a > 0.5, "ht_over_1.5": ht_h + ht_a > 1.5,
        "both_halves_over_1.5": ht_h + ht_a >= 2 and sh_h + sh_a >= 2,
        "both_halves_btts": ht_h > 0 and ht_a > 0 and sh_h > 0 and sh_a > 0,
        "goals_6plus": total >= 6, "early_goal_0_15": match["early_goals"] > 0,
        "htft_1/2": ht_h > ht_a and hg < ag, "htft_2/1": ht_h < ht_a and hg > ag,
    }
    if market in outcomes:
        return float(outcomes[market])
    return None


def market_profit(row, match):
    if row["b365"] is None or np.isnan(row["b365"]):
        return None
    total = match["home_goals"] + match["away_goals"]
    if row["market"] == "asian_over":
        return odds.settle_over(total, row["line"], row["b365"])
    if row["market"] == "asian_under":
        return odds.settle_under(total, row["line"], row["b365"])
    outcome = market_outcome(row["market"], match)
    return None if outcome is None else outcome * row["b365"] - 1


def settle(matches, now=None):
    now = now or pd.Timestamp.now(tz="UTC")
    with connect() as conn:
        conn.execute(SCHEMA)
        pending = pd.read_sql_query("SELECT event_id, market, line, b365 FROM prediction_log WHERE settled_at IS NULL", conn)
        if pending.empty:
            return 0
        done = matches[matches["state"].eq("post")].set_index("event_id")
        updates = []
        for row in pending.to_dict("records"):
            if row["event_id"] not in done.index:
                continue
            match = done.loc[row["event_id"]]
            if not match["regular"]:
                updates.append((None, None, None, None, now.isoformat(), row["event_id"], row["market"]))
                continue
            updates.append((clean(match["home_goals"]), clean(match["away_goals"]),
                            market_outcome(row["market"], match), market_profit(row, match),
                            now.isoformat(), row["event_id"], row["market"]))
        conn.executemany(
            "UPDATE prediction_log SET home_goals = ?, away_goals = ?, outcome = ?, profit = ?, settled_at = ? "
            "WHERE event_id = ? AND market = ?", updates)
    return len(updates)


def report(min_ev=MIN_EV):
    with connect() as conn:
        conn.execute(SCHEMA)
        log = pd.read_sql_query("SELECT * FROM prediction_log WHERE settled_at IS NOT NULL", conn)
    if log.empty:
        return None, None
    scored = log.dropna(subset=["model_p", "outcome"])
    p = scored["model_p"].clip(1e-9, 1 - 1e-9)
    scored = scored.assign(brier=(p - scored["outcome"]) ** 2,
                           logloss=-(scored["outcome"] * np.log(p) + (1 - scored["outcome"]) * np.log(1 - p)))
    accuracy = scored.groupby("market").agg(n=("outcome", "size"), model=("model_p", "mean"), actual=("outcome", "mean"),
                                            brier=("brier", "mean"), logloss=("logloss", "mean"))
    bets = log.dropna(subset=["profit", "ev"])
    bets = bets[bets["ev"] > min_ev]
    betting = bets.groupby("market").agg(bets=("profit", "size"), profit=("profit", "sum"), roi=("profit", "mean"))
    if len(bets):
        betting.loc["ALL"] = [len(bets), bets["profit"].sum(), bets["profit"].mean()]
    return accuracy, betting
