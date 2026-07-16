import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw/transfermarkt")
games_csv_path = DATA_DIR / "games.csv"
club_games_csv_path = DATA_DIR / "club_games.csv"

games_df = pd.read_csv(games_csv_path)
club_games_df = pd.read_csv(club_games_csv_path)

comp_id = "GB1"
season = 2012

gb1_games = games_df[(games_df['competition_id']==comp_id) & (games_df['season']==season)]

gb1_club_games= club_games_df[club_games_df['game_id'].isin(gb1_games['game_id'])]

game_dates = gb1_games[['game_id', 'date']]

merged_df = pd.merge(gb1_club_games, game_dates, on='game_id', how='left')

arsenal_games= merged_df[merged_df['club_id']==11]
arsenal_games = arsenal_games.sort_values(by='date', ascending=False)

last_10_games= arsenal_games.head(10)
last_10_games_own_goals= last_10_games['own_goals'].sum()
last_10_games_opp_goals= last_10_games['opponent_goals'].sum()

wins = (last_10_games['own_goals'] > last_10_games['opponent_goals']).sum()
loses= (last_10_games['own_goals'] < last_10_games['opponent_goals']).sum()
draws= (last_10_games['own_goals'] == last_10_games['opponent_goals']).sum()
length= len(last_10_games)
total_games_over_2_5= ((last_10_games['own_goals']+last_10_games['opponent_goals'])>2.5).sum()
total_games_btts= ((last_10_games['own_goals']>0) & (last_10_games['opponent_goals']>0)).sum()
avg_goal_per_game= ((last_10_games['own_goals']).sum() + (last_10_games['opponent_goals']).sum())/length
