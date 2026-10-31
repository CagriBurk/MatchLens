import time

import pandas as pd
import soccerdata as sd

from data_pipeline.db import connect
from data_pipeline.team_names import to_clubelo


def run():
    with connect() as conn:
        teams = pd.read_sql_query("SELECT DISTINCT home_team FROM tactical_match_stats", conn)["home_team"].tolist()

    elo = sd.ClubElo()
    histories = []
    for team in teams:
        clubelo_name = to_clubelo(team)
        try:
            history = elo.read_team_history(clubelo_name).reset_index()
        except Exception as exc:
            print(f"ClubElo fetch failed for {team} ({clubelo_name}): {exc}")
            continue
        history["original_team_name"] = team
        histories.append(history)
        time.sleep(1)

    if not histories:
        raise RuntimeError("No Elo history fetched")

    elo_df = pd.concat(histories, ignore_index=True)
    with connect() as conn:
        elo_df.to_sql("historical_club_elo", conn, if_exists="replace", index=False)
    print(f"historical_club_elo: {len(elo_df)} rows for {len(histories)}/{len(teams)} teams")


if __name__ == "__main__":
    run()
