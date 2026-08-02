import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path("database/matchlens.db")

def calculate_form_snapshot(target_club_id, data_table, current_date):
    team_games = data_table[data_table['club_id'] == target_club_id]
    team_games = team_games[team_games['date'] < current_date]
    team_games = team_games.sort_values(by='date', ascending=False)

    last_10_games = team_games.head(10)
    length = len(last_10_games)

    if length == 0:
        return {
            "club_id": target_club_id, "matches_played": 0, "wins": 0, "draws": 0, "loses": 0,
            "last_10_games_own_goals": 0, "last_10_games_opp_goals": 0, "total_games_over_2_5": 0,
            "total_games_btts": 0, "avg_goal_per_game": 0, "btts_rate": 0, "total_over_2_5": 0,
            "points": 0, "average_point_per_game": 0
        }

    last_10_games_own_goals = last_10_games['own_goals'].sum()
    last_10_games_opp_goals = last_10_games['opponent_goals'].sum()

    wins = (last_10_games['own_goals'] > last_10_games['opponent_goals']).sum()
    loses = (last_10_games['own_goals'] < last_10_games['opponent_goals']).sum()
    draws = (last_10_games['own_goals'] == last_10_games['opponent_goals']).sum()

    total_games_over_2_5 = ((last_10_games['own_goals'] + last_10_games['opponent_goals']) > 2.5).sum()
    total_games_btts = ((last_10_games['own_goals'] > 0) & (last_10_games['opponent_goals'] > 0)).sum()
    
    avg_goal_per_game = (last_10_games_own_goals + last_10_games_opp_goals) / length
    points = (wins * 3) + (draws * 1)

    return {
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
        "average_point_per_game": points / length
    }

def build_team_form_snapshots(conn):
    print("Building team form snapshots")
    query = """
        SELECT cg.club_id, cg.game_id, cg.own_goals, cg.opponent_goals, g.date 
        FROM club_games cg
        JOIN games g ON cg.game_id = g.game_id
    """
    try:
        merged_df = pd.read_sql_query(query, conn)
        merged_df['date'] = pd.to_datetime(merged_df['date'])
        
        snapshot_list = []
        for index, row in merged_df.iterrows():
            stats_results = calculate_form_snapshot(row['club_id'], merged_df, row['date'])
            stats_results['date'] = row['date']
            stats_results['game_id'] = row['game_id']
            snapshot_list.append(stats_results)

        final_snapshot_df = pd.DataFrame(snapshot_list)
        final_snapshot_df.to_sql("team_form_snapshots", conn, if_exists="replace", index=False)
        print("team_form_snapshots created successfully")
    except Exception as e:
        print(f"Error in build_team_form_snapshots: {e}")

def build_match_features(conn):
    print("Building match features")
    query = """
    SELECT 
        g.game_id, g.date, g.competition_id, g.season,
        g.home_club_id, g.away_club_id, g.home_club_goals, g.away_club_goals,
        home_form.points AS home_points, 
        home_form.btts_rate AS home_btts_rate, 
        away_form.btts_rate AS away_btts_rate, 
        away_form.points AS away_points, 
        home_form.total_over_2_5 AS home_over_2_5_rate, 
        away_form.total_over_2_5 AS away_over_2_5_rate
    FROM games AS g
    JOIN team_form_snapshots AS home_form
      ON g.game_id = home_form.game_id AND g.home_club_id = home_form.club_id
    JOIN team_form_snapshots AS away_form
      ON g.game_id = away_form.game_id AND g.away_club_id = away_form.club_id
    """
    try:
        feature_df = pd.read_sql_query(query, conn)
        
        feature_df['form_advantage'] = feature_df['home_points'] - feature_df['away_points']
        feature_df['btts_tendency'] = (feature_df['home_btts_rate'] + feature_df['away_btts_rate']) / 2
        feature_df['over_2_5_tendency'] = (feature_df['home_over_2_5_rate'] + feature_df['away_over_2_5_rate']) / 2

        feature_df['target_btts'] = ((feature_df['home_club_goals'] > 0) & (feature_df['away_club_goals'] > 0)).astype(int)
        feature_df['target_over_2_5'] = ((feature_df['home_club_goals'] + feature_df['away_club_goals']) > 2.5).astype(int)

        feature_df.to_sql("match_features", conn, if_exists="replace", index=False)
        print("match_features created successfully")
    except Exception as e:
        print(f"Error in build_match_features: {e}")

def run():
    print("Starting Feature Engine")
    conn = sqlite3.connect(DB_PATH)
    build_team_form_snapshots(conn)
    build_match_features(conn)
    conn.close()
    print("Feature Engine completed")

if __name__ == "__main__":
    run()
