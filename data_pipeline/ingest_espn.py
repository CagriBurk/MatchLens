import argparse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pandas as pd

from data_pipeline.db import connect
from data_pipeline.espn import client, parse
from data_pipeline.espn.leagues import FIRST_YEAR, LEAGUES

UPCOMING_DAYS = 7


def current_year():
    return datetime.now(timezone.utc).year


def fetch_scoreboards(leagues, years):
    this_year = current_year()
    for league in leagues:
        for year in years:
            events = client.fetch_scoreboard(league, year, refresh=year >= this_year)
            print(f"scoreboard {league} {year}: {len(events)} events")


def cached_events(leagues, years):
    for league in leagues:
        for year in years:
            path = client.scoreboard_path(league, year)
            if path.exists():
                for event in client.read_cache(path):
                    if event.get("id") and event.get("status") and event.get("competitions"):
                        yield league, event


def summary_targets(leagues, years, sample=None, seed=7):
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=UPCOMING_DAYS)
    groups = {}
    for league, event in cached_events(leagues, years):
        state = event["status"]["type"].get("state")
        kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        if state == "post" or (state == "pre" and kickoff <= horizon):
            key = (league, event.get("season", {}).get("year"))
            groups.setdefault(key, []).append((league, event["id"]))
    targets = []
    rng = random.Random(seed)
    for key in sorted(groups, key=str):
        items = groups[key]
        if sample and len(items) > sample:
            items = rng.sample(items, sample)
        targets.extend(items)
    return targets


def fetch_summaries(targets, workers=4):
    done = failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(client.fetch_summary, league, event_id): (league, event_id) for league, event_id in targets}
        for future in as_completed(futures):
            try:
                future.result()
                done += 1
            except Exception as exc:
                failed += 1
                print(f"summary failed {futures[future]}: {exc}")
            if (done + failed) % 500 == 0:
                print(f"summaries: {done + failed}/{len(targets)}")
    print(f"summaries finished: {done} ok, {failed} failed")


def build_tables(leagues, years):
    matches, events, stats, odds = [], [], [], []
    seen = set()
    for league, event in cached_events(leagues, years):
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        match, match_events = parse.parse_scoreboard_event(event, league)
        events.extend(match_events)
        goal_events = sum(e["type"] in parse.GOAL_TYPES for e in match_events)
        match["events_consistent"] = match["completed"] and goal_events == (match["home_goals"] or 0) + (match["away_goals"] or 0)
        path = client.summary_path(league, event["id"])
        match["has_summary"] = path.exists()
        if path.exists():
            summary = client.read_cache(path)
            stats.extend(parse.parse_team_stats(summary, event["id"]))
            odds_row = parse.parse_bet365_odds(summary, event["id"])
            if odds_row:
                odds.append(odds_row)
            match["referee"] = parse.parse_referee(summary)
        matches.append(match)

    tables = {
        "espn_matches": pd.DataFrame(matches),
        "espn_match_events": pd.DataFrame(events),
        "espn_team_stats": pd.DataFrame(stats),
        "espn_odds": pd.DataFrame(odds),
    }
    with connect() as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
            print(f"{name}: {len(df)} rows")


def coverage_report():
    query = """
    SELECT m.league, m.season,
           COUNT(*) AS matches,
           SUM(m.has_summary) AS summaries,
           SUM(CASE WHEN s.event_id IS NOT NULL THEN 1 ELSE 0 END) AS with_stats,
           SUM(CASE WHEN s.corners IS NOT NULL THEN 1 ELSE 0 END) AS with_corners,
           SUM(CASE WHEN o.b365_home IS NOT NULL THEN 1 ELSE 0 END) AS with_b365_1x2,
           SUM(CASE WHEN o.b365_over IS NOT NULL THEN 1 ELSE 0 END) AS with_b365_ou
    FROM espn_matches m
    LEFT JOIN (
        SELECT event_id, MAX(wonCorners) AS corners FROM espn_team_stats GROUP BY event_id
    ) s ON s.event_id = m.event_id
    LEFT JOIN espn_odds o ON o.event_id = m.event_id
    WHERE m.completed = 1
    GROUP BY m.league, m.season
    ORDER BY m.league, m.season
    """
    with connect() as conn:
        df = pd.read_sql_query(query, conn)
    sampled = df["summaries"].replace(0, pd.NA)
    for col in ["with_stats", "with_corners", "with_b365_1x2", "with_b365_ou"]:
        df[col.replace("with_", "pct_")] = (100 * df[col] / sampled).round(0)
    columns = ["league", "season", "matches", "summaries", "pct_stats", "pct_corners", "pct_b365_1x2", "pct_b365_ou"]
    with pd.option_context("display.max_rows", 500, "display.width", 200):
        print(df[columns].to_string(index=False))
    return df


def main():
    parser = argparse.ArgumentParser(description="ESPN soccer ingestion")
    parser.add_argument("action", choices=["scoreboards", "summaries", "build", "coverage", "all"])
    parser.add_argument("--leagues", nargs="*", default=list(LEAGUES))
    parser.add_argument("--from-year", type=int, default=FIRST_YEAR)
    parser.add_argument("--to-year", type=int, default=current_year())
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    years = list(range(args.from_year, args.to_year + 1))

    if args.action in ("scoreboards", "all"):
        fetch_scoreboards(args.leagues, years)
    if args.action in ("summaries", "all"):
        targets = summary_targets(args.leagues, years, sample=args.sample)
        print(f"summary targets: {len(targets)}")
        fetch_summaries(targets, workers=args.workers)
    if args.action in ("build", "all"):
        build_tables(args.leagues, years)
    if args.action in ("coverage", "all"):
        coverage_report()


if __name__ == "__main__":
    main()
