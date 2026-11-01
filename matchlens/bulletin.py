import argparse
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from data_pipeline.config import DATA_DIR
from data_pipeline.espn import client, parse
from data_pipeline.espn.leagues import LEAGUES
from data_pipeline.ingest_espn import current_year
from matchlens import dixon_coles, markets, odds, twins
from matchlens.data import finished, load_matches
from matchlens.market_lambda import DEFAULT_RHO, ImpliedLambda, fair_three_way, fair_two_way

LOCAL_TZ = ZoneInfo("Europe/Istanbul")
BULLETIN_DIR = DATA_DIR / "bulletins"
MIN_EV = 0.03
MARKET_SOURCES = ("b365", "dk")
MAX_ODDS = 6.0
AGREEMENT_EDGE = 0.04
ODDS_MARKETS = [
    ("1", "home", "b365_home"), ("X", "draw", "b365_draw"), ("2", "away", "b365_away"),
    ("1X", "dc_1x", "b365_dc_home_draw"), ("12", "dc_12", "b365_dc_home_away"), ("X2", "dc_x2", "b365_dc_draw_away"),
]
COMPARE_MARKETS = [("1", "home"), ("X", "draw"), ("2", "away"), ("O2.5", "over_2.5"), ("BTTS", "btts_yes")]
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
        b365 = parse.parse_bet365_odds(summary or {}, match.event_id) or {}
        dk = parse.parse_draftkings_odds(summary or {}, match.event_id) or {}
        if b365 or dk:
            rows[match.event_id] = {**b365, **dk}
    return rows


@lru_cache(maxsize=1)
def implied_lambda():
    return ImpliedLambda()


def over25_from_line(p_home, p_away, p_over_line, line):
    lam_h, lam_a = implied_lambda().solve([p_home], [p_away], [p_over_line], line=line)
    totals = markets.total_distribution(markets.score_matrix(lam_h[0], lam_a[0], DEFAULT_RHO))
    return markets.over_prob(totals, 2.5)


def goal_lines(odds_row):
    lines = []
    for src in MARKET_SOURCES:
        line, over, under = (odds_row.get(f"{src}_{k}") for k in ("goal_line", "over", "under"))
        if line is not None and not pd.isna(line) and over and under:
            lines.append((src, float(line), over, under))
    return lines


def market_view(odds_row):
    for src in MARKET_SOURCES:
        prices = [odds_row.get(f"{src}_{side}") for side in ("home", "draw", "away")]
        if all(prices):
            break
    else:
        return {}
    fair = fair_three_way([prices[0]], [prices[1]], [prices[2]])[0]
    view = {"market_home": fair[0], "market_draw": fair[1], "market_away": fair[2], "market_src": src,
            "market_odds_home": prices[0], "market_odds_draw": prices[1], "market_odds_away": prices[2]}
    lines = goal_lines(odds_row)
    exact = [entry for entry in lines if entry[0] == src and entry[1] == 2.5] or [entry for entry in lines if entry[1] == 2.5]
    chosen = exact[0] if exact else (lines[0] if lines else None)
    if chosen is None:
        return view
    line_src, line, over, under = chosen
    view.update({"market_line": line, "market_line_over": over, "market_line_under": under, "market_line_src": line_src})
    p_line = float(fair_two_way(over, under))
    if line == 2.5:
        view["market_over_2.5"], view["market_ou_src"] = p_line, line_src
    else:
        view["market_over_2.5"], view["market_ou_src"] = over25_from_line(fair[0], fair[2], p_line, line), f"{line_src}~"
    return view


def twin_view(finder, market, kickoff):
    if not market:
        return {}
    summary = finder.summarize(market["market_home"], market["market_away"], market.get("market_over_2.5"), before=kickoff)
    view = {f"twin_{m}": summary[m] for m in twins.MARKETS}
    view.update({"twin_n": summary["n"], "twin_scores": summary["top_scores"]})
    return view


def evaluate_match(match, model, odds_row, finder):
    lam_h, lam_a = model.expected_goals(match.home_team_id, match.away_team_id)
    probs, matrix = markets.market_probs(lam_h, lam_a, model.rho, model.shares)
    totals = markets.total_distribution(matrix)
    kickoff = match.kickoff.tz_convert(LOCAL_TZ).strftime("%H:%M")
    base = {"event_id": match.event_id, "league": match.league, "kickoff": kickoff, "kickoff_utc": match.kickoff_utc,
            "home_team": match.home_team, "away_team": match.away_team, "lam_home": lam_h, "lam_away": lam_a}
    market = market_view(odds_row) if odds_row else {}
    record = {**base, **probs, **market, **twin_view(finder, market, match.kickoff)}
    record["top_scores"] = " ".join(f"{h}-{a}" for h, a, _ in markets.top_scores(matrix, 3))
    record["rho"] = model.rho
    candidates = []
    if odds_row:
        record.update({k: v for k, v in odds_row.items() if k != "event_id"})
        for label, key, column in ODDS_MARKETS:
            price = odds_row.get(column)
            if price:
                candidates.append({**base, "market": label, "key": key, "line": None, "model_p": probs[key],
                                   "b365": price, "ev": odds.expected_value(probs[key], price)})
        line = odds_row.get("b365_goal_line")
        for side in ("over", "under"):
            price = odds_row.get(f"b365_{side}")
            if line is not None and price:
                candidates.append({**base, "market": f"{side.title()} {line:g}", "key": f"asian_{side}", "line": line,
                                   "model_p": None, "b365": price, "ev": odds.asian_total_ev(totals, line, price, side)})
    return record, candidates


def build(dates, leagues, refresh=True):
    matches, day = fixtures_for(dates, leagues, refresh)
    if day.empty:
        return pd.DataFrame(), pd.DataFrame()
    odds_rows = fetch_odds(day)
    finder = twins.TwinFinder(twins.load_pool())
    now = pd.Timestamp.now(tz="UTC")
    records, candidates = [], []
    for league, league_day in day.groupby("league"):
        model = dixon_coles.fit(finished(matches[matches["league"].eq(league)]), now)
        for match in league_day.itertuples():
            record, cands = evaluate_match(match, model, odds_rows.get(match.event_id), finder)
            records.append(record)
            candidates.extend(cands)
    return pd.DataFrame(records), pd.DataFrame(candidates)


def pct_text(value, digits=0):
    return "-" if value is None or pd.isna(value) else f"{100 * value:.{digits}f}"


def column(records, name):
    return records[name] if name in records else pd.Series(np.nan, index=records.index)


def match_names(df):
    return df["home_team"].str.slice(0, 18) + " - " + df["away_team"].str.slice(0, 18)


def compare_table(records):
    table = pd.DataFrame({
        "lg": records["league"], "time": records["kickoff"], "match": match_names(records),
        "xg": records["lam_home"].round(2).astype(str) + "-" + records["lam_away"].round(2).astype(str),
    })
    for label, key in COMPARE_MARKETS:
        model, twin, market = records[key], column(records, f"twin_{key}"), column(records, f"market_{key}")
        table[label] = [f"{pct_text(m)}/{pct_text(t)}/{pct_text(p)}" for m, t, p in zip(model, twin, market)]
    table["b365 1/X/2"] = records.apply(
        lambda r: "/".join(f"{r[c]:.2f}" for c in ("b365_home", "b365_draw", "b365_away"))
        if all(pd.notna(r.get(c)) for c in ("b365_home", "b365_draw", "b365_away")) else "-", axis=1)
    return table


def surprise_table(records):
    table = pd.DataFrame({"match": match_names(records)})
    for label, key in SURPRISE_MARKETS:
        twin = column(records, f"twin_{key}")
        table[label] = [f"{pct_text(m, 1)}/{pct_text(t, 1)}" for m, t in zip(records[key], twin)]
    return table


def scores_table(records):
    return pd.DataFrame({"match": match_names(records), "model": records["top_scores"],
                         "twins": column(records, "twin_scores").fillna("-")})


def agreement_table(records, edge=AGREEMENT_EDGE):
    rows = []
    for label, key in COMPARE_MARKETS:
        if f"twin_{key}" not in records or f"market_{key}" not in records:
            continue
        model, twin, market = records[key], records[f"twin_{key}"], records[f"market_{key}"]
        hit = (model - market > edge) & (twin - market > edge)
        for i in np.flatnonzero(hit.fillna(False).to_numpy()):
            r = records.iloc[i]
            rows.append({"lg": r["league"], "time": r["kickoff"], "match": match_names(records.iloc[[i]]).iloc[0],
                         "market": label, "model": pct_text(model.iloc[i]), "twins": pct_text(twin.iloc[i]),
                         "market%": pct_text(market.iloc[i])})
    return pd.DataFrame(rows)


def render(records, candidates, min_ev, show_edges=False):
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 500):
        print(f"Matches ({len(records)}): model / odds twins / Bet365 market, in %")
        print(compare_table(records).to_string(index=False))
        print("\nSurprise markets: model / odds twins, in %")
        print(surprise_table(records).to_string(index=False))
        print("\nMost likely scores")
        print(scores_table(records).to_string(index=False))
        agreement = agreement_table(records)
        print(f"\nModel and twins both above market by {AGREEMENT_EDGE:.0%} (informational; 2019-2026 backtest ROI of this rule was negative)")
        print("none" if agreement.empty else agreement.to_string(index=False))
        if not show_edges or candidates.empty:
            return
        value = candidates[(candidates["ev"] > min_ev) & (candidates["b365"] <= MAX_ODDS)].sort_values("ev", ascending=False)
        print(f"\nExperimental: model vs Bet365 (EV > {min_ev:.0%}); backtest ROI of this signal is negative")
        print("none" if value.empty else value[["league", "kickoff", "home_team", "away_team", "market", "b365", "ev"]].round(3).to_string(index=False))


def save(records, candidates, date):
    BULLETIN_DIR.mkdir(parents=True, exist_ok=True)
    records.to_csv(BULLETIN_DIR / f"{date}_matches.csv", index=False)
    if not candidates.empty:
        candidates.to_csv(BULLETIN_DIR / f"{date}_odds.csv", index=False)


def save_snapshots(records, candidates):
    if records.empty:
        return []
    local_day = pd.to_datetime(records["kickoff_utc"], utc=True).dt.tz_convert(LOCAL_TZ).dt.date
    for day, part in records.groupby(local_day):
        cands = candidates[candidates["event_id"].isin(part["event_id"])] if not candidates.empty else candidates
        save(part, cands, day)
    return sorted(set(local_day))


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
