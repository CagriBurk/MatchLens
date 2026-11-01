import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from data_pipeline.config import DATA_DIR
from data_pipeline.espn import client, parse
from data_pipeline.espn.leagues import LEAGUES
from data_pipeline.ingest_espn import current_year
from matchlens import dixon_coles, markets, odds
from matchlens.data import finished, load_matches

LOCAL_TZ = ZoneInfo("Europe/Istanbul")
BULLETIN_DIR = DATA_DIR / "bulletins"
MIN_EV = 0.03
MAX_ODDS = 6.0
ODDS_MARKETS = [
    ("1", "home", "b365_home"), ("X", "draw", "b365_draw"), ("2", "away", "b365_away"),
    ("1X", "dc_1x", "b365_dc_home_draw"), ("12", "dc_12", "b365_dc_home_away"), ("X2", "dc_x2", "b365_dc_draw_away"),
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


def evaluate_match(match, model, odds_row):
    lam_h, lam_a = model.expected_goals(match.home_team_id, match.away_team_id)
    probs, matrix = markets.market_probs(lam_h, lam_a, model.rho, model.shares)
    totals = markets.total_distribution(matrix)
    kickoff = match.kickoff.tz_convert(LOCAL_TZ).strftime("%H:%M")
    base = {"event_id": match.event_id, "league": match.league, "kickoff": kickoff, "kickoff_utc": match.kickoff_utc,
            "home_team": match.home_team, "away_team": match.away_team, "lam_home": lam_h, "lam_away": lam_a}
    record = {**base, **probs}
    record["top_scores"] = " ".join(f"{h}-{a}" for h, a, _ in markets.top_scores(matrix, 3))
    candidates = []
    if odds_row:
        record.update({k: v for k, v in odds_row.items() if k != "event_id"})
        prices = [odds_row.get("b365_home"), odds_row.get("b365_draw"), odds_row.get("b365_away")]
        market_probs = odds.fair_probs(prices) if all(prices) else [None] * 3
        for label, key, column in ODDS_MARKETS:
            price = odds_row.get(column)
            if not price:
                continue
            market_p = None
            if key in ("home", "draw", "away") and market_probs[0] is not None:
                market_p = float(market_probs[("home", "draw", "away").index(key)])
            candidates.append({**base, "market": label, "key": key, "line": None, "model_p": probs[key], "market_p": market_p,
                               "fair_odds": odds.fair_odds(probs[key]), "b365": price,
                               "ev": odds.expected_value(probs[key], price)})
        line = odds_row.get("b365_goal_line")
        for side in ("over", "under"):
            price = odds_row.get(f"b365_{side}")
            if line is None or not price:
                continue
            ev = odds.asian_total_ev(totals, line, price, side)
            candidates.append({**base, "market": f"{side.title()} {line:g}", "key": f"asian_{side}", "line": line,
                               "model_p": None, "market_p": None,
                               "fair_odds": None, "b365": price, "ev": ev})
    return record, candidates


def build(dates, leagues, refresh=True):
    matches, day = fixtures_for(dates, leagues, refresh)
    if day.empty:
        return pd.DataFrame(), pd.DataFrame()
    odds_rows = fetch_odds(day)
    now = pd.Timestamp.now(tz="UTC")
    records, candidates = [], []
    for league, league_day in day.groupby("league"):
        model = dixon_coles.fit(finished(matches[matches["league"].eq(league)]), now)
        for match in league_day.itertuples():
            record, cands = evaluate_match(match, model, odds_rows.get(match.event_id))
            records.append(record)
            candidates.extend(cands)
    return pd.DataFrame(records), pd.DataFrame(candidates)


def pct(series):
    return (100 * series).round(0).astype("Int64")


def render(records, candidates, min_ev):
    table = pd.DataFrame({
        "lg": records["league"], "time": records["kickoff"],
        "match": records["home_team"].str.slice(0, 18) + " - " + records["away_team"].str.slice(0, 18),
        "xg": records["lam_home"].round(2).astype(str) + "-" + records["lam_away"].round(2).astype(str),
        "1": pct(records["home"]), "X": pct(records["draw"]), "2": pct(records["away"]),
        "o1.5": pct(records["over_1.5"]), "o2.5": pct(records["over_2.5"]), "o3.5": pct(records["over_3.5"]),
        "btts": pct(records["btts_yes"]), "scores": records["top_scores"],
    })
    for column in ("b365_home", "b365_draw", "b365_away"):
        if column not in records:
            records[column] = None
    table["b365 1/X/2"] = records[["b365_home", "b365_draw", "b365_away"]].apply(
        lambda r: "/".join(f"{v:.2f}" for v in r) if r.notna().all() else "-", axis=1)
    specials = pd.DataFrame({
        "match": table["match"], "2H1.5o": pct(records["both_halves_over_1.5"]),
        "2HBTTS": pct(records["both_halves_btts"]), "6+": pct(records["goals_6plus"]),
        "0-15": pct(records["early_goal_0_15"]), "HT1.5o": pct(records["ht_over_1.5"]),
    })
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 500):
        print(f"Matches ({len(table)}), probabilities in %")
        print(table.to_string(index=False))
        print("\nSpecial markets (model only, %)")
        print(specials.to_string(index=False))
        if candidates.empty:
            print("\nNo Bet365 odds available for these fixtures")
            return
        value = candidates[(candidates["ev"] > min_ev) & (candidates["b365"] <= MAX_ODDS)].sort_values("ev", ascending=False)
        print(f"\nValue candidates (EV > {min_ev:.0%}, odds <= {MAX_ODDS})")
        if value.empty:
            print("none")
            return
        view = pd.DataFrame({
            "lg": value["league"], "time": value["kickoff"],
            "match": value["home_team"].str.slice(0, 18) + " - " + value["away_team"].str.slice(0, 18),
            "market": value["market"], "model%": pct(value["model_p"]), "market%": pct(value["market_p"]),
            "fair": value["fair_odds"].round(2), "b365": value["b365"].round(2), "ev%": pct(value["ev"]),
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
    args = parser.parse_args()
    records, candidates = build([args.date], args.leagues, refresh=not args.no_refresh)
    if records.empty:
        print(f"No scheduled fixtures on {args.date}")
        return
    render(records, candidates, args.min_ev)
    save(records, candidates, args.date)


if __name__ == "__main__":
    main()
