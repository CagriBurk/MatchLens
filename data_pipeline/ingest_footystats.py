import re

import numpy as np
import pandas as pd

from data_pipeline import linking
from data_pipeline.config import FOOTYSTATS_DIR
from data_pipeline.db import connect
from data_pipeline.espn.matches import load_matches

FILE_PATTERN = re.compile(r"(?P<prefix>.+)-matches-(?P<start>\d{4})-to-(?P<end>\d{4})-stats\.csv")
LEAGUES = {
    "england-premier-league": "eng.1", "england-championship": "eng.2", "spain-segunda-division": "esp.2",
    "turkey-super-lig": "tur.1", "belgium-pro-league": "bel.1", "denmark-superliga": "den.1",
    "norway-eliteserien": "nor.1", "usa-mls": "usa.1", "sweden-allsvenskan": "swe.1", "japan-j1-league": "jpn.1",
    "japan-j1-100-year-vision-league": "jpn.1.vision", "poland-ekstraklasa": "pol.1",
    "switzerland-super-league": "sui.1", "south-korea-k-league-1": "kor.1", "finland-veikkausliiga": "fin.1",
    "europe-uefa-champions-league": "uefa.champions", "europe-uefa-europa-league": "uefa.europa",
    "europe-uefa-europa-conference-league": "uefa.europa.conf",
}
COLUMNS = {
    "status": "status", "referee": "referee", "Game Week": "game_week", "attendance": "attendance",
    "home_team_name": "home_name", "away_team_name": "away_name",
    "home_team_goal_count": "home_goals", "away_team_goal_count": "away_goals",
    "home_team_goal_count_half_time": "ht_home", "away_team_goal_count_half_time": "ht_away",
    "home_team_goal_timings": "home_goal_timings", "away_team_goal_timings": "away_goal_timings",
    "home_team_corner_count": "home_corners", "away_team_corner_count": "away_corners",
    "home_team_yellow_cards": "home_yellow", "away_team_yellow_cards": "away_yellow",
    "home_team_red_cards": "home_red", "away_team_red_cards": "away_red",
    "home_team_first_half_cards": "home_cards_1h", "home_team_second_half_cards": "home_cards_2h",
    "away_team_first_half_cards": "away_cards_1h", "away_team_second_half_cards": "away_cards_2h",
    "home_team_shots": "home_shots", "away_team_shots": "away_shots",
    "home_team_shots_on_target": "home_sot", "away_team_shots_on_target": "away_sot",
    "home_team_fouls": "home_fouls", "away_team_fouls": "away_fouls",
    "home_team_possession": "home_possession", "away_team_possession": "away_possession",
    "team_a_xg": "home_xg", "team_b_xg": "away_xg",
    "Home Team Pre-Match xG": "home_prematch_xg", "Away Team Pre-Match xG": "away_prematch_xg",
    "Pre-Match PPG (Home)": "home_prematch_ppg", "Pre-Match PPG (Away)": "away_prematch_ppg",
    "odds_ft_home_team_win": "odds_home", "odds_ft_draw": "odds_draw", "odds_ft_away_team_win": "odds_away",
    "odds_ft_over15": "odds_over15", "odds_ft_over25": "odds_over25", "odds_ft_over35": "odds_over35",
    "odds_ft_over45": "odds_over45", "odds_btts_yes": "odds_btts_yes", "odds_btts_no": "odds_btts_no",
}
RESULT_COLUMNS = [c for c in COLUMNS.values() if c.endswith(("_goals", "ht_home", "ht_away", "_xg", "_corners", "_yellow", "_red", "_shots", "_sot", "_fouls", "_possession")) or "_cards_" in c]
ODDS_COLUMNS = [c for c in COLUMNS.values() if c.startswith("odds_")]


def read_file(path):
    parts = FILE_PATTERN.match(path.name)
    if not parts or parts["prefix"] not in LEAGUES:
        return None
    raw = pd.read_csv(path)
    df = raw.rename(columns=COLUMNS)[list(COLUMNS.values())].copy()
    df.insert(0, "league", LEAGUES[parts["prefix"]])
    df.insert(1, "season", parts["start"] if parts["start"] == parts["end"] else f"{parts['start']}/{parts['end']}")
    df.insert(2, "kickoff", pd.to_datetime(raw["timestamp"], unit="s", utc=True))
    df.insert(3, "date", df["kickoff"].dt.tz_convert(None).dt.normalize())
    return df


def clean(df):
    df = df.copy()
    complete = df["status"].eq("complete")
    df.loc[~complete, RESULT_COLUMNS] = np.nan
    df[RESULT_COLUMNS] = df[RESULT_COLUMNS].where(df[RESULT_COLUMNS] >= 0)
    df[ODDS_COLUMNS] = df[ODDS_COLUMNS].where(df[ODDS_COLUMNS] > 1)
    for column in ("home_prematch_xg", "away_prematch_xg"):
        df[column] = df[column].where(df[column] > 0)
    return df


def load_footystats():
    frames = [read_file(path) for path in sorted(FOOTYSTATS_DIR.glob("*-matches-*-stats.csv"))]
    df = pd.concat([f for f in frames if f is not None], ignore_index=True)
    return clean(df).drop_duplicates(["league", "kickoff", "home_name", "away_name"]).reset_index(drop=True)


def run():
    footystats = load_footystats()
    espn = load_matches()
    linked, name_map = linking.link(footystats, espn)
    with connect() as conn:
        linked.drop(columns=["date"]).to_sql("footystats_matches", conn, if_exists="replace", index=False)
        linking.save_name_map(conn, "footystats", name_map)
    complete = linked["status"].eq("complete")
    print(f"footystats_matches: {len(linked)} rows, {complete.sum()} complete, {linked['espn_event_id'].notna().sum()} linked to ESPN")
    rejected = name_map[~name_map["accepted"]]
    if len(rejected):
        print(f"Unmapped team names: {len(rejected)}")
        print(rejected.to_string(index=False))
    with pd.option_context("display.width", 200):
        print(linking.link_report(linked[complete], espn).round(3).to_string())


if __name__ == "__main__":
    run()
