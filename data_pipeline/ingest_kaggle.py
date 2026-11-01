
import numpy as np
import pandas as pd

from data_pipeline import linking
from data_pipeline.config import KAGGLE_DIR
from data_pipeline.db import connect
from data_pipeline.espn.matches import load_matches

MATCHES_CSV = KAGGLE_DIR / "club_football" / "Matches.csv"
ELO_CSV = KAGGLE_DIR / "club_football" / "EloRatings.csv"
DIVISIONS = {
    "E0": "eng.1", "E1": "eng.2", "SP1": "esp.1", "SP2": "esp.2", "I1": "ita.1", "D1": "ger.1",
    "F1": "fra.1", "T1": "tur.1", "B1": "bel.1", "DEN": "den.1", "NOR": "nor.1", "USA": "usa.1",
    "N1": "ned.1", "P1": "por.1", "D2": "ger.2", "I2": "ita.2", "F2": "fra.2", "SC0": "sco.1",
    "SWE": "swe.1", "JAP": "jpn.1", "POL": "pol.1", "SUI": "sui.1", "AUT": "aut.1",
}
COLUMNS = {
    "Division": "division", "MatchTime": "match_time", "HomeTeam": "home_name", "AwayTeam": "away_name",
    "HomeElo": "home_elo", "AwayElo": "away_elo",
    "FTHome": "home_goals", "FTAway": "away_goals",
    "HTHome": "ht_home", "HTAway": "ht_away",
    "HomeShots": "home_shots", "AwayShots": "away_shots", "HomeTarget": "home_sot", "AwayTarget": "away_sot",
    "HomeFouls": "home_fouls", "AwayFouls": "away_fouls", "HomeCorners": "home_corners", "AwayCorners": "away_corners",
    "HomeYellow": "home_yellow", "AwayYellow": "away_yellow", "HomeRed": "home_red", "AwayRed": "away_red",
    "OddHome": "odds_home", "OddDraw": "odds_draw", "OddAway": "odds_away",
    "MaxHome": "max_home", "MaxDraw": "max_draw", "MaxAway": "max_away",
    "Over25": "odds_over25", "Under25": "odds_under25", "MaxOver25": "max_over25", "MaxUnder25": "max_under25",
    "HandiSize": "ah_line", "HandiHome": "ah_home", "HandiAway": "ah_away",
}


def load_kaggle_matches():
    raw = pd.read_csv(MATCHES_CSV, low_memory=False)
    raw = raw[raw["Division"].isin(DIVISIONS)]
    df = raw.rename(columns=COLUMNS)[list(dict.fromkeys(COLUMNS.values()))].copy()
    df.insert(0, "league", raw["Division"].map(DIVISIONS))
    df.insert(1, "date", pd.to_datetime(raw["MatchDate"]))
    df = df.dropna(subset=["home_goals", "away_goals"])
    return df.reset_index(drop=True)


def odds_source_check(linked):
    with connect() as conn:
        espn_odds = pd.read_sql_query("SELECT event_id, b365_home, b365_draw, b365_away FROM espn_odds", conn)
    both = linked.merge(espn_odds, left_on="espn_event_id", right_on="event_id").dropna(subset=["odds_home", "b365_home"])
    if both.empty:
        return None
    return {
        "matches": len(both),
        "exact_home": float(np.isclose(both["odds_home"], both["b365_home"], atol=0.011).mean()),
        "mean_abs_diff_home": float((both["odds_home"] - both["b365_home"]).abs().mean()),
        "kaggle_margin": float((1 / both[["odds_home", "odds_draw", "odds_away"]]).sum(axis=1).mean() - 1),
        "b365_margin": float((1 / both[["b365_home", "b365_draw", "b365_away"]]).sum(axis=1).mean() - 1),
    }


def run():
    kaggle = load_kaggle_matches()
    espn = load_matches()
    linked, name_map = linking.link(kaggle, espn)
    with connect() as conn:
        linked.to_sql("kaggle_matches", conn, if_exists="replace", index=False)
        linking.save_name_map(conn, "kaggle", name_map)
        pd.read_csv(ELO_CSV).to_sql("kaggle_elo", conn, if_exists="replace", index=False)
    print(f"kaggle_matches: {len(linked)} rows, {linked['espn_event_id'].notna().sum()} linked to ESPN")
    rejected = name_map[~name_map["accepted"]]
    if len(rejected):
        print(f"Unmapped team names: {len(rejected)}")
        print(rejected.to_string(index=False))
    with pd.option_context("display.width", 200):
        print(linking.link_report(linked, espn).round(3).to_string())
    print(odds_source_check(linked))


def main():
    run()


if __name__ == "__main__":
    main()
