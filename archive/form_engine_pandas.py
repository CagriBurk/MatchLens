import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw/transfermarkt")
games_csv_path = DATA_DIR / "games.csv"
club_games_csv_path = DATA_DIR / "club_games.csv"

games_df = pd.read_csv(games_csv_path)
games_df['date']= pd.to_datetime(games_df['date'])
club_games_df = pd.read_csv(club_games_csv_path)

comp_id = "GB1"
season = 2012

gb1_games = games_df[(games_df['competition_id']==comp_id) & (games_df['season']==season)]

gb1_club_games= club_games_df[club_games_df['game_id'].isin(gb1_games['game_id'])]

game_dates = gb1_games[['game_id', 'date']]

merged_df = pd.merge(gb1_club_games, game_dates, on='game_id', how='left')




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
            "club_id": 0,
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

unique_clubs= merged_df['club_id'].unique()
all_teams_forms=[]

def generate_snapshot_database(merged_dataframe, output_filepath):
    snapshot_list=[]
    for index,row in merged_dataframe.iterrows():
        current_id = row['club_id']
        current_date = row['date']
        current_game_id = row['game_id']
        stats_results = get_team_form_stats(current_id,merged_dataframe,current_date) 
        stats_results['date'] = current_date
        stats_results['game_id'] = current_game_id

        snapshot_list.append(stats_results)
        
    final_snapshot_df= pd.DataFrame(snapshot_list)
    output_path= DATA_DIR / "team_form_snapshot.csv"

    final_snapshot_df.to_csv(output_path, index=False)

output_path = DATA_DIR / "team_form_snapshot.csv"

if output_path.exists():
    print("Hazır snapshot dosyası bulundu, hesaplama yapılmadan okunuyor...")
    final_snapshot_df = pd.read_csv(output_path)
else:
    print("Snapshot dosyası bulunamadı, baştan hesaplanıyor. Lütfen bekleyin...")
    generate_snapshot_database(merged_df, output_path)
    final_snapshot_df = pd.read_csv(output_path)

clean_snapshot_df = final_snapshot_df.drop(columns=['date'])

games_with_home_form = pd.merge(
    gb1_games, 
    clean_snapshot_df, 
    left_on=['game_id', 'home_club_id'], 
    right_on=['game_id','club_id'], 
    how='left'
)

games_with_all_forms = pd.merge(
    games_with_home_form,
    clean_snapshot_df,
    left_on=['game_id', 'away_club_id'],
    right_on=['game_id','club_id'],
    how='left',
    suffixes=('_home', '_away') 
)

