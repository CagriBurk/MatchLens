import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from data_pipeline.config import DATA_DIR
from data_pipeline.espn import client, parse
from data_pipeline.espn.leagues import LEAGUES
from data_pipeline.ingest_espn import current_year
from matchlens import blend, dixon_coles, markets, odds
from matchlens.market_lambda import ImpliedLambda
from matchlens.data import finished, load_matches

LOCAL_TZ = ZoneInfo("Europe/Istanbul")
BULLETIN_DIR = DATA_DIR / "bulletins"
MIN_EV = 0.03
MAX_ODDS = 6.0
ODDS_MARKETS = [
    ("1", "home", "b365_home"), ("X", "draw", "b365_draw"), ("2", "away", "b365_away"),
    ("1X", "dc_1x", "b365_dc_home_draw"), ("12", "dc_12", "b365_dc_home_away"), ("X2", "dc_x2", "b365_dc_draw_away"),
]
SURPRISE_MARKETS = [
    ("BH-BTTS", "both_halves_btts"), ("BH-O1.5", "both_halves_over_1.5"), ("6+", "goals_6plus"),
    ("0-15", "early_goal_0_15"), ("HT/FT 1/2", "htft_1/2"), ("HT/FT 2/1", "htft_2/1"),
]


def refresh_years():
    week_ago = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
    return sorted({week_ago.year, current_year()})


def refresh_scoreboards(leagues):
    for league in leagues:
        for year in refresh_years():
            client.fetch_scoreboard(league, year, refresh=True)


def fixtures_for(dates, leagues, refresh):
    if refresh:
        refresh_scoreboards(leagues)
    matches = load_matches(leagues, from_year=current_year() - 4)
    local_date = matches["kickoff"].dt.tz_convert(LOCAL_TZ).dt.date
    day = matches[local_date.isin(set(dates)) & matches["state"].eq("pre")]
    return matches, day.sort_values("kickoff")


def fetch_odds(day):
    rows = {}
    for match in day.itertuples():
        summary = client.fetch_summary(match.league, match.event_id)
        row = parse.parse_bet365_odds(summary or {}, match.event_id)
        if row:
            rows[match.event_id] = row
    return rows


def evaluate_match(match, model, odds_row, solver):
    model_lams = model.expected_goals(match.home_team_id, match.away_team_id)
    market_lams = blend.market_lambdas(solver, odds_row) if odds_row else None
    (lam_h, lam_a), source = blend.final_lambdas(match.league, model_lams, market_lams)
    probs, matrix = markets.market_probs(lam_h, lam_a, model.rho, model.shares)
    totals = markets.total_distribution(matrix)
    kickoff = match.kickoff.tz_convert(LOCAL_TZ).strftime("%H:%M")
    base = {"event_id": match.event_id, "league": match.league, "kickoff": kickoff, "kickoff_utc": match.kickoff_utc,
            "home_team": match.home_team, "away_team": match.away_team, "lam_home": lam_h, "lam_away": lam_a, "source": source}
    record = {**base, **probs, "model_lam_home": model_lams[0], "model_lam_away": model_lams[1]}
    record["top_scores"] = " ".join(f"{h}-{a}" for h, a, _ in markets.top_scores(matrix, 3))
    candidates = []
    if odds_row:
        record.update({k: v for k, v in odds_row.items() if k != "event_id"})
        model_probs, model_matrix = markets.market_probs(*model_lams, model.rho, model.shares)
        model_totals = markets.total_distribution(model_matrix)
        for label, key, column in ODDS_MARKETS:
            price = odds_row.get(column)
            if not price:
                continue
            candidates.append({**base, "market": label, "key": key, "line": None, "prob": probs[key],
                               "model_p": model_probs[key], "b365": price,
                               "ev": odds.expected_value(probs[key], price),
                               "model_ev": odds.expected_value(model_probs[key], price)})
        line = odds_row.get("b365_goal_line")
        for side in ("over", "under"):
            price = odds_row.get(f"b365_{side}")
            if line is None or not price:
                continue
            candidates.append({**base, "market": f"{side.title()} {line:g}", "key": f"asian_{side}", "line": line,
                               "prob": None, "model_p": None, "b365": price,
                               "ev": odds.asian_total_ev(totals, line, price, side),
                               "model_ev": odds.asian_total_ev(model_totals, line, price, side)})
    return record, candidates


def build(dates, leagues, refresh=True):
    matches, day = fixtures_for(dates, leagues, refresh)
    if day.empty:
        return pd.DataFrame(), pd.DataFrame()
    odds_rows = fetch_odds(day)
    solver = ImpliedLambda()
    now = pd.Timestamp.now(tz="UTC")
    records, candidates = [], []
    for league, league_day in day.groupby("league"):
        model = dixon_coles.fit(finished(matches[matches["league"].eq(league)]), now)
        for match in league_day.itertuples():
            record, cands = evaluate_match(match, model, odds_rows.get(match.event_id), solver)
            records.append(record)
            candidates.extend(cands)
    return pd.DataFrame(records), pd.DataFrame(candidates)


def pct(series, digits=0):
    values = (100 * series.astype(float)).round(digits)
    return values.astype("Int64") if digits == 0 else values


def prob_with_fair(series):
    return series.astype(float).map(lambda p: f"{100 * p:.1f}% @{1 / p:.1f}" if p > 0 else "-")


def match_names(df):
    return df["home_team"].str.slice(0, 18) + " - " + df["away_team"].str.slice(0, 18)


def render(records, candidates, min_ev, show_edges=False):
    for column in ("b365_home", "b365_draw", "b365_away"):
        if column not in records:
            records[column] = None
    table = pd.DataFrame({
        "lg": records["league"], "time": records["kickoff"], "match": match_names(records), "src": records["source"],
        "xg": records["lam_home"].round(2).astype(str) + "-" + records["lam_away"].round(2).astype(str),
        "1": pct(records["home"]), "X": pct(records["draw"]), "2": pct(records["away"]),
        "o1.5": pct(records["over_1.5"]), "o2.5": pct(records["over_2.5"]), "o3.5": pct(records["over_3.5"]),
        "btts": pct(records["btts_yes"]), "scores": records["top_scores"],
    })
    table["b365 1/X/2"] = records[["b365_home", "b365_draw", "b365_away"]].apply(
        lambda r: "/".join(f"{v:.2f}" for v in r) if r.notna().all() else "-", axis=1)
    surprise = pd.DataFrame({"match": match_names(records), "src": records["source"]})
    for label, key in SURPRISE_MARKETS:
        surprise[label] = prob_with_fair(records[key])
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 500):
        print(f"Matches ({len(table)}), probabilities in %, src=b365: anchored to Bet365 odds, src=model: model only")
        print(table.to_string(index=False))
        print("\nSurprise markets: probability @ fair odds")
        print(surprise.to_string(index=False))
        if not show_edges or candidates.empty:
            return
        value = candidates[(candidates["model_ev"] > min_ev) & (candidates["b365"] <= MAX_ODDS)].sort_values("model_ev", ascending=False)
        print(f"\nExperimental: pure model vs Bet365 (EV > {min_ev:.0%}); backtest ROI of this signal is negative")
        if value.empty:
            print("none")
            return
        view = pd.DataFrame({
            "lg": value["league"], "time": value["kickoff"], "match": match_names(value), "market": value["market"],
            "model%": pct(value["model_p"]), "b365": value["b365"].round(2), "model_ev%": pct(value["model_ev"]),
        })
        print(view.to_string(index=False))


def save(records, candidates, date):
    BULLETIN_DIR.mkdir(parents=True, exist_ok=True)
    records.to_csv(BULLETIN_DIR / f"{date}_matches.csv", index=False)
    if not candidates.empty:
        candidates.to_csv(BULLETIN_DIR / f"{date}_odds.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Daily goal-market bulletin")
    parser.add_argument("--date", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(), default=datetime.now(LOCAL_TZ).date())
    parser.add_argument("--leagues", nargs="*", default=list(LEAGUES))
    parser.add_argument("--min-ev", type=float, default=MIN_EV)
    parser.add_argument("--no-refresh", action="store_true")
    parser.add_argument("--show-edges", action="store_true")
    args = parser.parse_args()
    records, candidates = build([args.date], args.leagues, refresh=not args.no_refresh)
    if records.empty:
        print(f"No scheduled fixtures on {args.date}")
        return
    render(records, candidates, args.min_ev, args.show_edges)
    save(records, candidates, args.date)


if __name__ == "__main__":
    main()
