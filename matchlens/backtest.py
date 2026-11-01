import argparse

import numpy as np
import pandas as pd

from data_pipeline.db import connect
from data_pipeline.espn.leagues import LEAGUES
from matchlens import dixon_coles, goal_calibration, markets, odds
from matchlens.data import finished, load_matches

DEFAULT_START = "2019-07-01"
EV_THRESHOLDS = (0.0, 0.03, 0.05, 0.10)
MAX_ODDS = 6.0
EPS = 1e-12


def walk_forward(matches, start, xi, ridge, targets=("home_goals", "away_goals"), fixed_rho=None):
    rows = []
    for league, league_matches in matches.groupby("league"):
        played = finished(league_matches)
        test = played[played["kickoff"] >= pd.Timestamp(start, tz="UTC")]
        model = None
        for week_start, week in test.groupby(test["kickoff"].dt.to_period("W-MON").dt.start_time):
            ref = pd.Timestamp(week_start, tz="UTC")
            try:
                model = dixon_coles.fit(played, ref, xi=xi, ridge=ridge, warm_start=model, targets=targets, fixed_rho=fixed_rho)
            except ValueError:
                continue
            for match in week.itertuples():
                lam_h, lam_a = model.expected_goals(match.home_team_id, match.away_team_id)
                rows.append({
                    "event_id": match.event_id, "league": league, "season": match.season,
                    "kickoff": match.kickoff, "home_team": match.home_team, "away_team": match.away_team,
                    "home_goals": match.home_goals, "away_goals": match.away_goals,
                    "ht_home_goals": match.ht_home, "ht_away_goals": match.ht_away,
                    "events_consistent": match.events_consistent,
                    "lam_home": lam_h, "lam_away": lam_a, "rho": model.rho,
                    "share_home_1h": model.shares["home_1h"], "share_away_1h": model.shares["away_1h"],
                    "share_early": model.shares["early"],
                })
    return pd.DataFrame(rows)


def add_market_probs(preds):
    records = []
    for row in preds.itertuples():
        shares = {"home_1h": row.share_home_1h, "away_1h": row.share_away_1h, "early": row.share_early}
        probs, matrix = markets.market_probs(row.lam_home, row.lam_away, row.rho, shares)
        probs["totals"] = markets.total_distribution(matrix)
        records.append(probs)
    return pd.concat([preds.reset_index(drop=True), pd.DataFrame(records)], axis=1)


def load_odds():
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM espn_odds", conn)


def outcome_index(df):
    return np.select([df["home_goals"] > df["away_goals"], df["home_goals"] == df["away_goals"]], [0, 1], 2)


def log_loss_1x2(probs, outcome):
    picked = probs[np.arange(len(outcome)), outcome]
    return float(-np.mean(np.log(np.clip(picked, EPS, 1))))


def binary_log_loss(p, y):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def accuracy_report(df):
    outcome = outcome_index(df)
    total = df["home_goals"] + df["away_goals"]
    model_1x2 = df[["home", "draw", "away"]].to_numpy()
    base = np.bincount(outcome, minlength=3) / len(outcome)
    report = {
        "matches": len(df),
        "ll_1x2_model": log_loss_1x2(model_1x2, outcome),
        "ll_1x2_base": log_loss_1x2(np.tile(base, (len(df), 1)), outcome),
        "ll_o25_model": binary_log_loss(df["over_2.5"], (total > 2.5).astype(int)),
        "ll_o25_base": binary_log_loss(np.full(len(df), (total > 2.5).mean()), (total > 2.5).astype(int)),
        "ll_btts_model": binary_log_loss(df["btts_yes"], ((df["home_goals"] > 0) & (df["away_goals"] > 0)).astype(int)),
    }
    odds_columns = ["b365_home", "b365_draw", "b365_away"]
    with_odds = df.dropna(subset=odds_columns) if set(odds_columns) <= set(df.columns) else df.iloc[:0]
    if len(with_odds):
        market = np.vstack([odds.fair_probs(r) for r in with_odds[["b365_home", "b365_draw", "b365_away"]].to_numpy()])
        o = outcome_index(with_odds)
        report["odds_matches"] = len(with_odds)
        report["ll_1x2_model_on_odds"] = log_loss_1x2(with_odds[["home", "draw", "away"]].to_numpy(), o)
        report["ll_1x2_market"] = log_loss_1x2(market, o)
    return report


def betting_report(df, thresholds=EV_THRESHOLDS):
    bets = []
    with_1x2 = df.dropna(subset=["b365_home", "b365_draw", "b365_away"])
    outcome = outcome_index(with_1x2)
    for side, idx in (("home", 0), ("draw", 1), ("away", 2)):
        price = with_1x2[f"b365_{side}"].to_numpy()
        ev = with_1x2[side].to_numpy() * price - 1
        profit = np.where(outcome == idx, price - 1, -1.0)
        bets.append(pd.DataFrame({"market": "1x2", "ev": ev, "odds": price, "profit": profit, "league": with_1x2["league"].to_numpy()}))
    with_ou = df.dropna(subset=["b365_over", "b365_under", "b365_goal_line"])
    for side in ("over", "under"):
        settle = odds.settle_over if side == "over" else odds.settle_under
        ev, profit = [], []
        for row in with_ou.itertuples():
            price = getattr(row, f"b365_{side}")
            ev.append(odds.asian_total_ev(row.totals, row.b365_goal_line, price, side))
            profit.append(settle(row.home_goals + row.away_goals, row.b365_goal_line, price))
        bets.append(pd.DataFrame({"market": "total", "ev": ev, "odds": with_ou[f"b365_{side}"].to_numpy(), "profit": profit, "league": with_ou["league"].to_numpy()}))
    bets = pd.concat(bets, ignore_index=True)
    bets = bets[bets["odds"] <= MAX_ODDS]
    rows = []
    for market, group in bets.groupby("market"):
        for threshold in thresholds:
            picked = group[group["ev"] > threshold]
            rows.append({
                "market": market, "min_ev": threshold, "bets": len(picked),
                "roi": picked["profit"].mean() if len(picked) else np.nan,
            })
    return pd.DataFrame(rows), bets


def run(leagues, start, xi, ridge, save=True):
    matches = load_matches(leagues)
    preds = add_market_probs(walk_forward(matches, start, xi, ridge))
    try:
        preds = preds.merge(load_odds(), on="event_id", how="left")
    except Exception:
        for col in ("b365_home", "b365_draw", "b365_away", "b365_over", "b365_under", "b365_goal_line"):
            preds[col] = np.nan
    if save:
        with connect() as conn:
            preds.drop(columns=["totals"]).to_sql("backtest_predictions", conn, if_exists="replace", index=False)
        goal_calibration.refresh()
    return preds


def print_reports(preds):
    per_league = pd.DataFrame({league: accuracy_report(group) for league, group in preds.groupby("league")}).T
    per_league.loc["ALL"] = accuracy_report(preds)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(per_league.round(4).to_string())
        summary, _ = betting_report(preds)
        print(summary.round(4).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Walk-forward backtest of the goal model")
    parser.add_argument("--leagues", nargs="*", default=list(LEAGUES))
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--xi", type=float, default=dixon_coles.XI)
    parser.add_argument("--ridge", type=float, default=dixon_coles.RIDGE)
    args = parser.parse_args()
    print_reports(run(args.leagues, args.start, args.xi, args.ridge))


if __name__ == "__main__":
    main()
