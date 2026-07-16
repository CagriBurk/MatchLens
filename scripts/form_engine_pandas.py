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

print(gb1_club_games)

