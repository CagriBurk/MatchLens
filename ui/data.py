import re
from datetime import date, datetime

import numpy as np
import pandas as pd
import streamlit as st

from matchlens import markets, twins
from matchlens.bulletin import AGREEMENT_EDGE, BULLETIN_DIR, LOCAL_TZ

SNAPSHOT = re.compile(r"^(\d{4}-\d{2}-\d{2})_matches\.csv$")
COMPARE = ["home", "draw", "away", "over_2.5", "btts_yes"]
EDGE = AGREEMENT_EDGE


def today():
    return datetime.now(LOCAL_TZ).date()


def snapshot_dates():
    found = (SNAPSHOT.match(path.name) for path in BULLETIN_DIR.glob("*_matches.csv"))
    return sorted(date.fromisoformat(m.group(1)) for m in found if m)


@st.cache_data(show_spinner=False)
def read_snapshot(path, mtime):
    df = pd.read_csv(path, dtype={"event_id": str})
    df["kickoff_at"] = pd.to_datetime(df["kickoff_utc"], utc=True).dt.tz_convert(LOCAL_TZ)
    return df.sort_values(["kickoff_at", "league"]).reset_index(drop=True)


def load_day(day):
    path = BULLETIN_DIR / f"{day}_matches.csv"
    if not path.exists():
        return pd.DataFrame()
    return read_snapshot(str(path), path.stat().st_mtime)


def default_day(days):
    upcoming = [d for d in days if d >= today()]
    return upcoming[0] if upcoming else days[-1]


def upcoming_matches():
    days = [d for d in snapshot_dates() if d >= today()] or snapshot_dates()[-1:]
    frames = [load_day(d) for d in days]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def find_match(event_id):
    for day in reversed(snapshot_dates()):
        df = load_day(day)
        hit = df[df["event_id"].eq(str(event_id))]
        if len(hit):
            return hit.iloc[0]
    return None


def value(record, key):
    v = record.get(key) if hasattr(record, "get") else None
    return None if v is None or pd.isna(v) else float(v)


def has_market(record):
    return value(record, "market_home") is not None


def agreements(records, edge=EDGE):
    rows = []
    for _, r in records.iterrows():
        for key in COMPARE:
            m, t, p = value(r, key), value(r, f"twin_{key}"), value(r, f"market_{key}")
            if None in (m, t, p):
                continue
            rows.append({"record": r, "key": key, "model": m, "twin": t, "market": p, "low": min(m - p, t - p)})
    hits = [row for row in rows if row["low"] >= edge]
    near = max((row for row in rows if row["low"] > 0), key=lambda row: row["low"], default=None)
    return hits, near


def score_grid(record, size=6):
    rho = value(record, "rho") or 0.0
    matrix = markets.score_matrix(record["lam_home"], record["lam_away"], rho)
    grid = matrix[:size, :size].copy()
    grid[size - 1, :] += matrix[size:, :size].sum(axis=0)
    grid[:, size - 1] += matrix[:size, size:].sum(axis=1)
    grid[size - 1, size - 1] += matrix[size:, size:].sum()
    return grid, markets.top_scores(matrix, 5)


@st.cache_resource(ttl=6 * 3600, show_spinner="Loading odds twins pool")
def twin_finder():
    return twins.TwinFinder(twins.load_pool())


def twin_point(record):
    return value(record, "market_home"), value(record, "market_away"), value(record, "market_over_2.5")


def twin_summary(record):
    p_home, p_away, p_over = twin_point(record)
    return twin_finder().summarize(p_home, p_away, p_over, before=pd.Timestamp(record["kickoff_utc"]))


def twin_list(record):
    p_home, p_away, p_over = twin_point(record)
    return twin_finder().twin_table(p_home, p_away, p_over, before=pd.Timestamp(record["kickoff_utc"]))


def interval(p, n, z=1.96):
    return z * np.sqrt(p * (1 - p) / n) if n else np.nan
