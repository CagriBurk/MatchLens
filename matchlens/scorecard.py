import numpy as np
import pandas as pd

from data_pipeline.db import connect
from matchlens import coupons, tracking

SOURCES = {"model": "model_p", "twin": "twin_p", "market": "market_p"}
EPS = 1e-6
BINS = np.linspace(0, 1, 11)
COUPON_TYPES = ("blue", "yellow", "red")


def load_predictions():
    with connect() as conn:
        tracking.ensure_schema(conn)
        log = pd.read_sql_query("SELECT * FROM prediction_log WHERE settled_at IS NOT NULL AND outcome IS NOT NULL", conn)
    return log[~log["market"].str.startswith("asian_")].reset_index(drop=True)


def brier(p, y):
    return float(np.mean((p - y) ** 2)) if len(p) else np.nan


def log_loss(p, y):
    if not len(p):
        return np.nan
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def scores(p, y):
    p, y = np.asarray(p, float), np.asarray(y, float)
    return {"n": len(p), "mean_p": float(p.mean()) if len(p) else np.nan, "actual": float(y.mean()) if len(y) else np.nan,
            "brier": brier(p, y), "log_loss": log_loss(p, y)}


def common_rows(log, sources=SOURCES):
    return log.dropna(subset=list(sources.values()))


def source_table(log, sources=SOURCES):
    common = common_rows(log, sources)
    rows = {name: scores(common[col], common["outcome"]) for name, col in sources.items()}
    return pd.DataFrame(rows).T


def market_table(log, sources=SOURCES):
    rows = []
    for market, group in log.groupby("market"):
        row = {"market": market, "n": len(group), "actual": group["outcome"].mean()}
        for name, col in sources.items():
            scored = group.dropna(subset=[col])
            row[f"{name}_n"] = len(scored)
            row[f"{name}_mean"] = scored[col].mean() if len(scored) else np.nan
            row[f"{name}_brier"] = brier(scored[col].to_numpy(), scored["outcome"].to_numpy())
        rows.append(row)
    return pd.DataFrame(rows).set_index("market") if rows else pd.DataFrame()


def calibration(log, column, bins=BINS):
    scored = log.dropna(subset=[column])
    if scored.empty:
        return pd.DataFrame(columns=["low", "high", "n", "mean_p", "actual"])
    bucket = np.clip(np.searchsorted(bins, scored[column].to_numpy() + 1e-9, side="right") - 1, 0, len(bins) - 2)
    table = scored.groupby(bucket).agg(n=("outcome", "size"), mean_p=(column, "mean"), actual=("outcome", "mean"))
    table["low"], table["high"] = bins[table.index], bins[table.index + 1]
    return table[["low", "high", "n", "mean_p", "actual"]].reset_index(drop=True)


def market_source_table(log):
    priced = log.dropna(subset=["market_p"]) if "market_src" in log else log.iloc[0:0]
    rows = []
    for src, group in priced.groupby(priced["market_src"].fillna("?")):
        rows.append({"source": src, **scores(group["market_p"], group["outcome"]),
                     "model_brier_same": brier(group["model_p"].to_numpy(), group["outcome"].to_numpy())})
    return pd.DataFrame(rows)


def coupon_results(legs):
    if legs.empty:
        return pd.DataFrame(columns=["day", "coupon", "legs", "odds", "expected", "status", "payout"])
    rows = []
    for (day, coupon), group in legs[legs["coupon"].isin(COUPON_TYPES)].groupby(["day", "coupon"]):
        settled = group["settled_at"].notna()
        live = group[~(settled & group["outcome"].isna())]
        odds = float(np.prod(live["odds"])) if len(live) else 1.0
        expected = float(np.prod(live["p_safe"])) if len(live) else 1.0
        if (live["outcome"] == 0).any():
            status = "lost"
        elif settled.all():
            status = "won"
        else:
            status = "pending"
        payout = odds if status == "won" else 0.0 if status == "lost" else np.nan
        rows.append({"day": day, "coupon": coupon, "legs": len(live), "odds": odds, "expected": expected, "status": status, "payout": payout})
    return pd.DataFrame(rows)


def coupon_summary(results):
    rows = []
    for coupon in COUPON_TYPES:
        group = results[results["coupon"].eq(coupon)] if not results.empty else results
        done = group[group["status"].isin(["won", "lost"])]
        won = int(done["status"].eq("won").sum())
        rows.append({"coupon": coupon, "coupons": len(group), "settled": len(done), "won": won,
                     "hit_rate": won / len(done) if len(done) else np.nan,
                     "expected": float(done["expected"].mean()) if len(done) else np.nan,
                     "avg_odds": float(done["odds"].mean()) if len(done) else np.nan,
                     "roi": float(done["payout"].sum() / len(done) - 1) if len(done) else np.nan})
    return pd.DataFrame(rows).set_index("coupon")


def leg_summary(legs):
    done = legs[legs["outcome"].notna() & legs["coupon"].isin(COUPON_TYPES + ("surprise",))]
    if done.empty:
        return pd.DataFrame(columns=["legs", "hit_rate", "p_safe", "p_book", "avg_odds", "roi"])
    table = done.groupby("coupon").agg(legs=("outcome", "size"), hit_rate=("outcome", "mean"), p_safe=("p_safe", "mean"),
                                       p_book=("p_book", "mean"), avg_odds=("odds", "mean"))
    table["roi"] = done.assign(ret=done["outcome"] * done["odds"]).groupby("coupon")["ret"].mean() - 1
    return table


def load_coupons():
    return coupons.load()
