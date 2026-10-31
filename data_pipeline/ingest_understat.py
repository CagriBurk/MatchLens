import soccerdata as sd

from data_pipeline.db import connect

LEAGUES = ["ENG-Premier League"]
SEASONS = ["2324"]


def run(leagues=LEAGUES, seasons=SEASONS):
    understat = sd.Understat(leagues=leagues, seasons=seasons)
    match_stats = understat.read_team_match_stats().reset_index()
    with connect() as conn:
        match_stats.to_sql("tactical_match_stats", conn, if_exists="replace", index=False)
    print(f"tactical_match_stats: {len(match_stats)} rows")


if __name__ == "__main__":
    run()
