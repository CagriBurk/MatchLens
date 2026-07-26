import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path("database/matchlens.db")


conn = sqlite3.connect(DB_PATH)

query = """
SELECT g.game_id, g.date, g.home_club_id, g.away_club_id, g.home_club_goals, g.away_club_goals, home_form.points, home_form.btts_rate, away_form.btts_rate, away_form.points
FROM games AS g
JOIN team_form_snapshots AS home_form
  ON g.game_id = home_form.game_id
  AND g.home_club_id = home_form.club_id
JOIN team_form_snapshots AS away_form
  ON g.game_id = away_form.game_id
  AND g.away_club_id = away_form.club_id
WHERE g.competition_id = 'GB1'
  AND g.season = 2012

"""

team_match_records_df = pd.read_sql_query(query, conn)

team_match_records_df['date'] = pd.to_datetime(team_match_records_df['date'])

def get_team_form_stats(target_club_id, data_table, current_date):
    target_team_games= data_table[data_table['club_id']==target_club_id]

    target_team_games = target_team_games[target_team_games['date'] < current_date]

    target_team_games = target_team_games.sort_values(by='date', ascending=False)


    last_10_games= target_team_games.head(10)
    last_10_games_own_goals= last_10_games['own_goals'].sum()
    last_10_games_opp_goals= last_10_games['opponent_goals'].sum()

    wins = (last_10_games['own_goals'] > last_10_games['opponent_goals']).sum()
    loses= (last_10_games['own_goals'] < last_10_games['opponent_goals']).sum()
    draws= (last_10_games['own_goals'] == last_10_games['opponent_goals']).sum()
    length= len(last_10_games)
    if length == 0:

        zero_dict = {
            "club_id": target_club_id,
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "loses": 0,
            "last_10_games_own_goals": 0,
            "last_10_games_opp_goals": 0,
            "total_games_over_2_5": 0,
            "total_games_btts": 0,
            "avg_goal_per_game": 0,
            "btts_rate": 0,
            "total_over_2_5": 0,
            "points": 0,
            "average_point_per_game": 0
        }
        return zero_dict
    total_games_over_2_5= ((last_10_games['own_goals']+last_10_games['opponent_goals'])>2.5).sum()
    total_games_btts= ((last_10_games['own_goals']>0) & (last_10_games['opponent_goals']>0)).sum()
    avg_goal_per_game= ((last_10_games['own_goals']).sum() + (last_10_games['opponent_goals']).sum())/length
    points=(wins*3) + (draws*1)
    team_form_stats = {
        "club_id": target_club_id,
        "matches_played": length,
        "wins": wins,
        "draws": draws,
        "loses": loses,
        "last_10_games_own_goals": last_10_games_own_goals,
        "last_10_games_opp_goals": last_10_games_opp_goals,
        "total_games_over_2_5": total_games_over_2_5,
        "total_games_btts": total_games_btts,
        "avg_goal_per_game": avg_goal_per_game,
        "btts_rate": total_games_btts / length,
        "total_over_2_5": total_games_over_2_5 / length,
        "points": points,
        "average_point_per_game": points/length
    }
    return team_form_stats


def generate_snapshot_database(merged_dataframe, db_connection):
    snapshot_list=[]
    for index,row in merged_dataframe.iterrows():
        current_id = row['club_id']
        current_date = row['date']
        current_game_id = row['game_id']
        stats_results = get_team_form_stats(current_id,merged_dataframe,current_date) 
        stats_results['date'] = current_date
        stats_results['game_id'] = current_game_id

        snapshot_list.append(stats_results)

    final_snapshot_df=pd.DataFrame(snapshot_list)
    final_snapshot_df.to_sql("team_form_snapshots", db_connection, if_exists="replace", index=False)
    return final_snapshot_df
    
generate_snapshot_database(team_match_records_df,conn)
control_df = pd.read_sql_query("SELECT * FROM team_form_snapshots WHERE matches_played=10 LIMIT 5;", conn)
print(control_df)


feature_df= pd.read_sql_query(query, conn)
print(feature_df.head(10))
print(feature_df.shape)

conn.close()