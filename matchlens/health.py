import argparse
import json
from datetime import datetime

import numpy as np
import pandas as pd

from data_pipeline.config import DATA_DIR
from data_pipeline.db import connect
from matchlens import goal_calibration, markets, selections

REPORT_DIR = DATA_DIR / "reports"
SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
EPS = 1e-6
FULL_KEYS = ["home", "draw", "away", "over_1.5", "over_2.5", "over_3.5", "btts_yes", "goals_6plus",
             "home&btts_yes", "away&btts_yes", "draw&btts_yes", "home&over_2.5", "away&over_2.5", "btts_yes&over_2.5"]
HALF_KEYS = ["ht_over_0.5", "ht_over_1.5", "both_halves_over_1.5", "htft_1/2", "htft_2/1"]
FOCUS = ["over_2.5", "btts_yes", "home", "draw"]
MAX_BIAS = 0.01
SLOPE_RANGE = (0.85, 1.15)
BASE_DAYS = 365
MIN_BASE = 100


def load_predictions():
    with connect() as conn:
        preds = pd.read_sql_query("SELECT * FROM backtest_predictions", conn)
        odds = pd.read_sql_query("SELECT * FROM espn_odds", conn).drop_duplicates("event_id")
        twins = pd.read_sql_query("SELECT * FROM twins_backtest", conn)
    preds["event_id"] = preds["event_id"].astype(str)
    odds["event_id"] = odds["event_id"].astype(str)
    twins["event_id"] = twins["event_id"].astype(str)
    preds["kickoff"] = pd.to_datetime(preds["kickoff"], utc=True)
    preds = preds.sort_values("kickoff").reset_index(drop=True)
    return preds, odds, twins.drop_duplicates("event_id")


def outcomes(preds):
    hg, ag = preds["home_goals"].to_numpy(float), preds["away_goals"].to_numpy(float)
    full = selections.full_time(hg, ag)
    out = {key: np.asarray(full[key], float) for key in FULL_KEYS}
    consistent = preds["events_consistent"].astype(bool).to_numpy()
    ht_h, ht_a = preds["ht_home_goals"].to_numpy(float), preds["ht_away_goals"].to_numpy(float)
    half = selections.half_time(hg, ag, ht_h, ht_a)
    valid = consistent & ~np.isnan(ht_h) & ~np.isnan(ht_a)
    for key in HALF_KEYS:
        out[key] = np.where(valid, np.asarray(half[key], float), np.nan)
    return pd.DataFrame(out, index=preds.index)


def model_probs(preds, goal_weights=None):
    matrix = markets.score_matrices(preds["lam_home"], preds["lam_away"], preds["rho"], goal_weights=goal_weights)
    goals = np.arange(matrix.shape[1])
    masks = selections.full_time(goals[:, None], goals[None, :])
    probs = {key: (matrix * masks[key]).sum(axis=(1, 2)) for key in FULL_KEYS}
    for key in HALF_KEYS:
        probs[key] = preds[key].to_numpy(float) if key in preds else np.full(len(preds), np.nan)
    return pd.DataFrame(probs, index=preds.index)


def market_probs(preds, odds):
    merged = preds[["event_id"]].merge(odds, on="event_id", how="left")
    out = pd.DataFrame(index=preds.index, columns=["home", "draw", "away", "over_2.5"], dtype=float)
    prices = merged[["b365_home", "b365_draw", "b365_away"]].to_numpy(float)
    inv = 1 / prices
    fair = inv / inv.sum(axis=1, keepdims=True)
    out[["home", "draw", "away"]] = fair
    line = merged["b365_goal_line"].to_numpy(float) == 2.5
    over, under = 1 / merged["b365_over"].to_numpy(float), 1 / merged["b365_under"].to_numpy(float)
    out["over_2.5"] = np.where(line, over / (over + under), np.nan)
    return out


def twin_probs(preds, twins):
    merged = preds[["event_id"]].merge(twins, on="event_id", how="left")
    out = {}
    for key in FULL_KEYS + HALF_KEYS:
        hits, count = merged.get(f"twin_{key}"), merged.get(f"twin_{key}_n")
        if hits is None or count is None:
            out[key] = np.full(len(merged), np.nan)
            continue
        count = count.to_numpy(float)
        out[key] = np.where(count > 0, hits.to_numpy(float) / np.where(count > 0, count, 1), np.nan)
    return pd.DataFrame(out, index=preds.index)


def base_rates(preds, actual):
    base = pd.DataFrame(np.nan, index=preds.index, columns=actual.columns)
    week = preds["kickoff"].dt.tz_convert(None).dt.to_period("W-MON").dt.start_time.to_numpy("datetime64[ns]")
    for _, group in preds.groupby("league"):
        idx = group.index.to_numpy()
        times = group["kickoff"].dt.tz_convert(None).to_numpy("datetime64[ns]")
        lo = np.searchsorted(times, week[idx] - np.timedelta64(BASE_DAYS, "D"))
        hi = np.searchsorted(times, week[idx])
        for key in actual.columns:
            y = actual.loc[idx, key].to_numpy(float)
            seen = ~np.isnan(y)
            hits = np.concatenate([[0], np.cumsum(np.where(seen, y, 0))])
            counts = np.concatenate([[0], np.cumsum(seen)])
            n = counts[hi] - counts[lo]
            base.loc[idx, key] = np.where(n >= MIN_BASE, (hits[hi] - hits[lo]) / np.maximum(n, 1), np.nan)
    return base


def log_loss(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calibration_fit(p, y, iterations=25):
    x = np.log(np.clip(p, EPS, 1 - EPS) / np.clip(1 - p, EPS, 1))
    design = np.column_stack([np.ones_like(x), x])
    beta = np.array([0.0, 1.0])
    for _ in range(iterations):
        mu = 1 / (1 + np.exp(-design @ beta))
        weight = np.clip(mu * (1 - mu), 1e-9, None)
        hessian = design.T @ (design * weight[:, None])
        beta = beta + np.linalg.solve(hessian, design.T @ (y - mu))
    return float(beta[0]), float(beta[1])


def metrics(p, y, base=None):
    valid = ~np.isnan(p) & ~np.isnan(y)
    if base is not None:
        valid &= ~np.isnan(base)
    p, y = p[valid], y[valid]
    if len(p) < 50:
        return {"n": int(len(p))}
    intercept, slope = calibration_fit(p, y)
    row = {"n": int(len(p)), "mean_p": float(p.mean()), "actual": float(y.mean()), "bias": float(p.mean() - y.mean()),
           "ll": log_loss(p, y), "slope": slope, "intercept": intercept}
    if base is not None:
        row["ll_base"] = log_loss(base[valid], y)
        row["skill"] = 1 - row["ll"] / row["ll_base"]
    return row


def status(row):
    if row.get("n", 0) < 50:
        return "n/a"
    bias_ok = abs(row["bias"]) <= MAX_BIAS
    slope_ok = SLOPE_RANGE[0] <= row["slope"] <= SLOPE_RANGE[1]
    skill_ok = row.get("skill", 1) > 0
    return "PASS" if bias_ok and slope_ok and skill_ok else "FAIL"


def evaluate(preds, model, actual, base, market, twins, mask):
    rows = []
    for key in FULL_KEYS + HALF_KEYS:
        y = actual[key].to_numpy(float)
        m = np.where(mask, model[key].to_numpy(float), np.nan)
        row = {"key": key, **metrics(m, y, base[key].to_numpy(float))}
        row["status"] = status(row)
        if key in market:
            both = ~np.isnan(market[key].to_numpy(float)) & ~np.isnan(m)
            if both.sum() >= 50:
                row["n_market"] = int(both.sum())
                row["ll_model_on_market"] = log_loss(m[both], y[both])
                row["ll_market"] = log_loss(market[key].to_numpy(float)[both], y[both])
        t = np.where(mask, twins[key].to_numpy(float), np.nan)
        both = ~np.isnan(t) & ~np.isnan(m) & ~np.isnan(y)
        if both.sum() >= 50:
            row["n_twin"] = int(both.sum())
            row["bias_twin"] = float(t[both].mean() - y[both].mean())
            row["ll_twin"] = log_loss(np.clip(t[both], 0.01, 0.99), y[both])
            row["ll_model_on_twin"] = log_loss(m[both], y[both])
        rows.append(row)
    return pd.DataFrame(rows).set_index("key")


def breakdown(preds, model, actual, twins, mask, by, keys=FOCUS):
    rows = []
    for value, group in preds[mask].groupby(by, observed=True):
        idx = group.index
        row = {"group": value, "n": len(idx)}
        for key in keys:
            y = actual.loc[idx, key].to_numpy(float)
            row[f"{key}_model"] = float(np.nanmean(model.loc[idx, key]) - np.nanmean(y))
            t = twins.loc[idx, key].to_numpy(float)
            ok = ~np.isnan(t) & ~np.isnan(y)
            row[f"{key}_twin"] = float(t[ok].mean() - y[ok].mean()) if ok.sum() >= 30 else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index("group")


def calibration_table(p, y, bins=np.linspace(0, 1, 11)):
    valid = ~np.isnan(p) & ~np.isnan(y)
    p, y = p[valid], y[valid]
    bucket = np.clip(np.searchsorted(bins, p + 1e-9, side="right") - 1, 0, len(bins) - 2)
    frame = pd.DataFrame({"bucket": bucket, "p": p, "y": y}).groupby("bucket").agg(n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean"))
    frame.index = [f"{100 * bins[i]:.0f}-{100 * bins[i + 1]:.0f}" for i in frame.index]
    return frame


def run(label, weights_mode="tune"):
    preds, odds, twins_bt = load_predictions()
    actual = outcomes(preds)
    tune = (preds["kickoff"] < SPLIT).to_numpy()
    final = ~tune
    weights = None
    if weights_mode == "tune":
        weights = goal_calibration.fit(preds[tune].dropna(subset=["lam_home", "lam_away", "rho", "home_goals", "away_goals"]))
    elif weights_mode == "saved":
        weights = goal_calibration.load()
    model = model_probs(preds, weights)
    market = market_probs(preds, odds)
    twins = twin_probs(preds, twins_bt)
    base = base_rates(preds, actual)
    preds["year"] = preds["kickoff"].dt.year
    lam = preds["lam_home"] + preds["lam_away"]
    preds["lam_bin"] = pd.cut(lam, [0, 2.2, 2.6, 3.0, 3.4, 10], labels=["<2.2", "2.2-2.6", "2.6-3.0", "3.0-3.4", "3.4+"])
    fav = np.maximum(model["home"], model["away"])
    preds["fav_bin"] = pd.cut(fav, [0, 0.4, 0.5, 0.6, 0.7, 1], labels=["<40", "40-50", "50-60", "60-70", "70+"])
    preds["month"] = preds["kickoff"].dt.month
    sections = {
        "tune": evaluate(preds, model, actual, base, market, twins, tune),
        "final": evaluate(preds, model, actual, base, market, twins, final),
        "by_year": breakdown(preds, model, actual, twins, np.ones(len(preds), bool), "year"),
        "by_league_final": breakdown(preds, model, actual, twins, final, "league"),
        "by_lambda_final": breakdown(preds, model, actual, twins, final, "lam_bin"),
        "by_favourite_final": breakdown(preds, model, actual, twins, final, "fav_bin"),
        "by_month_final": breakdown(preds, model, actual, twins, final, "month"),
        "calibration_over_2.5_final": calibration_table(np.where(final, model["over_2.5"], np.nan), actual["over_2.5"].to_numpy(float)),
    }
    return sections


def render(sections, label):
    lines = [f"# Model health: {label} ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"Tune < {SPLIT:%Y-%m-%d} <= final. PASS: |bias| <= {MAX_BIAS:.0%}, slope in {SLOPE_RANGE}, skill > 0.", ""]
    cols = ["n", "mean_p", "actual", "bias", "slope", "skill", "ll", "ll_model_on_market", "ll_market", "bias_twin", "ll_model_on_twin", "ll_twin", "status"]
    for name, table in sections.items():
        lines.append(f"## {name}")
        shown = table[[c for c in cols if c in table.columns]] if name in ("tune", "final") else table
        lines.append("```")
        lines.append(shown.round(4).to_string())
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def summary(sections):
    final = sections["final"]
    return {"pass": int((final["status"] == "PASS").sum()), "fail": int((final["status"] == "FAIL").sum()),
            "failing": final.index[final["status"].eq("FAIL")].tolist(),
            "final_ll": {k: round(float(final.loc[k, "ll"]), 4) for k in FOCUS if k in final.index},
            "final_bias": {k: round(float(final.loc[k, "bias"]), 4) for k in FOCUS if k in final.index}}


def main():
    parser = argparse.ArgumentParser(description="Model health report on walk-forward predictions")
    parser.add_argument("--label", default="current")
    parser.add_argument("--weights", choices=["none", "tune", "saved"], default="tune")
    args = parser.parse_args()
    sections = run(args.label, args.weights)
    text = render(sections, args.label)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now():%Y%m%d_%H%M}"
    (REPORT_DIR / f"health_{args.label}_{stamp}.md").write_text(text, encoding="utf-8")
    (REPORT_DIR / f"health_{args.label}_{stamp}.json").write_text(json.dumps(summary(sections), indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
