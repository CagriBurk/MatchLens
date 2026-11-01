import pandas as pd

from data_pipeline.espn import parse
from data_pipeline.espn.leagues import FIRST_YEAR, LEAGUES
from data_pipeline.ingest_espn import cached_events, current_year

REGULAR_STATUS = "STATUS_FULL_TIME"
EARLY_MINUTE = 15


def load_matches(leagues=None, from_year=FIRST_YEAR, to_year=None):
    leagues = list(leagues or LEAGUES)
    years = range(from_year, (to_year or current_year()) + 1)
    rows, seen = [], set()
    for league, event in cached_events(leagues, years):
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        match, events = parse.parse_scoreboard_event(event, league)
        goals = [e for e in events if e["type"] in parse.GOAL_TYPES]
        home_id = match["home_team_id"]
        match["ht_home"] = sum(1 for e in goals if e["half"] == 1 and e["team_id"] == home_id)
        match["ht_away"] = sum(1 for e in goals if e["half"] == 1 and e["team_id"] != home_id)
        match["early_goals"] = sum(1 for e in goals if e["minute"] is not None and e["minute"] <= EARLY_MINUTE)
        match["goal_events"] = len(goals)
        rows.append(match)
    df = pd.DataFrame(rows)
    df["kickoff"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    total = df["home_goals"].fillna(-1) + df["away_goals"].fillna(-1)
    df["regular"] = df["status"].eq(REGULAR_STATUS)
    df["events_consistent"] = df["regular"] & df["goal_events"].eq(total)
    return df.sort_values("kickoff").reset_index(drop=True)
