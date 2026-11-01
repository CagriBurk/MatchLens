import argparse

import numpy as np
import pandas as pd

from data_pipeline.db import connect
from matchlens import markets
from matchlens.market_lambda import ImpliedLambda, fair_three_way, fair_two_way

WEIGHTS = np.round(np.arange(0.0, 1.01, 0.1), 2)
SPLIT = "2023-07-01"
EV_THRESHOLDS = (0.02, 0.05, 0.10)
MAX_ODDS = 6.0
EPS = 1e-12
RESULT_SOURCES = {
    "b365": ["b365_home", "b365_draw", "b365_away"],
    "kaggle": ["k_home", "k_draw", "k_away"],
    "footystats": ["fs_home", "fs_draw", "fs_away"],
}
KAGGLE_QUERY = """
SELECT espn_event_id AS event_id, odds_home AS k_home, odds_draw AS k_draw, odds_away AS k_away,
       max_home AS k_max_home, max_draw AS k_max_draw, max_away AS k_max_away,
       odds_over25 AS k_over25, odds_under25 AS k_under25, max_over25 AS k_max_over25, max_under25 AS k_max_under25
FROM kaggle_matches WHERE espn_event_id IS NOT NULL AND score_match = 1
"""
FOOTYSTATS_QUERY = """
SELECT espn_event_id AS event_id, odds_home AS fs_home, odds_draw AS fs_draw, odds_away AS fs_away,
       odds_over15 AS fs_over15, odds_over25 AS fs_over25, odds_over35 AS fs_over35,
       odds_btts_yes AS fs_btts_yes, odds_btts_no AS fs_btts_no
FROM footystats_matches WHERE espn_event_id IS NOT NULL
"""


def load_frame():
    with connect() as conn:
        preds = pd.read_sql_query("SELECT * FROM backtest_predictions", conn)
        kaggle = pd.read_sql_query(KAGGLE_QUERY, conn).drop_duplicates("event_id")
        footystats = pd.read_sql_query(FOOTYSTATS_QUERY, conn).drop_duplicates("event_id")
    df = preds.merge(kaggle, on="event_id", how="left").merge(footystats, on="event_id", how="left")
    df["kickoff"] = pd.to_datetime(df["kickoff"], utc=True)
    return df


def market_inputs(df):
    result = np.full((len(df), 3), np.nan)
    source = np.full(len(df), None, dtype=object)
    for name, columns in RESULT_SOURCES.items():
        available = df[columns].notna().all(axis=1).to_numpy() & np.isnan(result[:, 0])
        if available.any():
            result[available] = fair_three_way(*df.loc[available, columns].to_numpy().T)
            source[available] = name
    over = np.full(len(df), np.nan)
    kaggle_ou = df[["k_over25", "k_under25"]].notna().all(axis=1).to_numpy()
    over[kaggle_ou] = fair_two_way(df.loc[kaggle_ou, "k_over25"], df.loc[kaggle_ou, "k_under25"])
    b365_ou = np.isnan(over) & df["b365_goal_line"].eq(2.5).to_numpy() & df[["b365_over", "b365_under"]].notna().all(axis=1).to_numpy()
    over[b365_ou] = fair_two_way(df.loc[b365_ou, "b365_over"], df.loc[b365_ou, "b365_under"])
    return result, over, source


def add_market_lambdas(df):
    result, over, source = market_inputs(df)
    lam_home, lam_away = ImpliedLambda().solve(result[:, 0], result[:, 2], over, line=2.5)
    return df.assign(mkt_home=result[:, 0], mkt_draw=result[:, 1], mkt_away=result[:, 2], mkt_over25=over,
                     mkt_source=source, mkt_lam_home=lam_home, mkt_lam_away=lam_away)


def blended_probs(df, weight):
    lam_home = np.exp(weight * np.log(df["lam_home"]) + (1 - weight) * np.log(df["mkt_lam_home"]))
    lam_away = np.exp(weight * np.log(df["lam_away"]) + (1 - weight) * np.log(df["mkt_lam_away"]))
    return markets.core_probs(lam_home.to_numpy(), lam_away.to_numpy(), df["rho"].to_numpy())


def outcomes(df):
    hg, ag = df["home_goals"].to_numpy(), df["away_goals"].to_numpy()
    total = hg + ag
    return {
        "result": np.select([hg > ag, hg == ag], [0, 1], 2),
        "over_1.5": (total > 1.5).astype(float), "over_2.5": (total > 2.5).astype(float),
        "over_3.5": (total > 3.5).astype(float), "btts_yes": ((hg > 0) & (ag > 0)).astype(float),
    }


def log_loss_binary(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def log_loss_result(home, draw, away, result):
    probs = np.column_stack([home, draw, away])
    return float(-np.mean(np.log(np.clip(probs[np.arange(len(result)), result], EPS, 1))))


def scores(probs, y):
    row = {"1x2": log_loss_result(probs["home"], probs["draw"], probs["away"], y["result"])}
    for market in ("over_1.5", "over_2.5", "over_3.5", "btts_yes"):
        row[market] = log_loss_binary(probs[market], y[market])
    return row


def weight_table(df):
    y = outcomes(df)
    return pd.DataFrame([{"w": w, **scores(blended_probs(df, w), y)} for w in WEIGHTS]).set_index("w")


def reference_scores(df):
    y = outcomes(df)
    row = {"1x2_market_direct": log_loss_result(df["mkt_home"], df["mkt_draw"], df["mkt_away"], y["result"])}
    has_over = df["mkt_over25"].notna().to_numpy()
    row["over_2.5_market_direct"] = log_loss_binary(df.loc[has_over, "mkt_over25"].to_numpy(), y["over_2.5"][has_over])
    btts = df[["fs_btts_yes", "fs_btts_no"]].notna().all(axis=1).to_numpy()
    if btts.any():
        fair = fair_two_way(df.loc[btts, "fs_btts_yes"], df.loc[btts, "fs_btts_no"])
        sub = df[btts]
        row["btts_fs_direct"] = log_loss_binary(fair, y["btts_yes"][btts])
        row["btts_market_lambda_on_fs"] = log_loss_binary(blended_probs(sub, 0.0)["btts_yes"], y["btts_yes"][btts])
        row["btts_model_on_fs"] = log_loss_binary(blended_probs(sub, 1.0)["btts_yes"], y["btts_yes"][btts])
    return row


def bet_rows(df, probs, y):
    rows = []
    offers = [
        ("1x2_b365", [("home", "b365_home", 0), ("draw", "b365_draw", 1), ("away", "b365_away", 2)]),
        ("1x2_avg", [("home", "k_home", 0), ("draw", "k_draw", 1), ("away", "k_away", 2)]),
        ("1x2_max", [("home", "k_max_home", 0), ("draw", "k_max_draw", 1), ("away", "k_max_away", 2)]),
    ]
    for name, sides in offers:
        for key, column, index in sides:
            price = df[column].to_numpy()
            rows.append(pd.DataFrame({"market": name, "ev": probs[key] * price - 1, "odds": price,
                                      "profit": np.where(y["result"] == index, price - 1, -1.0)}))
    totals = [("o25_avg", "k_over25", "k_under25"), ("o25_max", "k_max_over25", "k_max_under25")]
    for name, over_col, under_col in totals:
        for side, column in (("over", over_col), ("under", under_col)):
            p = probs["over_2.5"] if side == "over" else 1 - probs["over_2.5"]
            hit = y["over_2.5"] if side == "over" else 1 - y["over_2.5"]
            price = df[column].to_numpy()
            rows.append(pd.DataFrame({"market": name, "ev": p * price - 1, "odds": price, "profit": np.where(hit == 1, price - 1, -1.0)}))
    for side, column in (("yes", "fs_btts_yes"), ("no", "fs_btts_no")):
        p = probs["btts_yes"] if side == "yes" else 1 - probs["btts_yes"]
        hit = y["btts_yes"] if side == "yes" else 1 - y["btts_yes"]
        price = df[column].to_numpy()
        rows.append(pd.DataFrame({"market": "btts_fs", "ev": p * price - 1, "odds": price, "profit": np.where(hit == 1, price - 1, -1.0)}))
    bets = pd.concat(rows, ignore_index=True).dropna(subset=["odds"])
    return bets[bets["odds"] <= MAX_ODDS]


def roi_table(df, weights):
    y = outcomes(df)
    rows = []
    for w in weights:
        bets = bet_rows(df, blended_probs(df, w), y)
        for market, group in bets.groupby("market"):
            for threshold in EV_THRESHOLDS:
                picked = group[group["ev"] > threshold]
                rows.append({"w": w, "market": market, "min_ev": threshold, "bets": len(picked),
                             "roi": picked["profit"].mean() if len(picked) else np.nan})
    return pd.DataFrame(rows).pivot_table(index=["market", "min_ev"], columns="w", values=["bets", "roi"])


def run():
    df = add_market_lambdas(load_frame())
    df = df.dropna(subset=["mkt_lam_home"])
    split = pd.Timestamp(SPLIT, tz="UTC")
    tune, test = df[df["kickoff"] < split], df[df["kickoff"] >= split]
    print(f"matches with market lambda: {len(df)} (tune {len(tune)}, test {len(test)})")
    print(df["mkt_source"].value_counts().to_string())
    with pd.option_context("display.width", 220, "display.max_columns", 40, "display.max_rows", 200):
        tune_table, test_table = weight_table(tune), weight_table(test)
        print("\nLog-loss by model weight w (tune)")
        print(tune_table.round(4).to_string())
        print("\nLog-loss by model weight w (test)")
        print(test_table.round(4).to_string())
        best = tune_table.idxmin()
        print("\nBest w on tune:", best.to_dict())
        print("\nReference (test):", {k: round(v, 4) for k, v in reference_scores(test).items()})
        per_league = {league: weight_table(group).idxmin() for league, group in df.groupby("league")}
        print("\nBest w per league (all periods)")
        print(pd.DataFrame(per_league).T.to_string())
        print("\nROI on test period")
        print(roi_table(test, sorted({0.0, float(best["1x2"]), float(best["over_2.5"]), 1.0})).round(3).to_string())
    return df


def main():
    argparse.ArgumentParser(description="Model vs market calibration and blend weights").parse_args()
    run()


if __name__ == "__main__":
    main()
