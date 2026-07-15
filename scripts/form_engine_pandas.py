from math import pi
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw/transfermarkt")
games_csv_path = DATA_DIR / "games.csv"

games_df = pd.read_csv(games_csv_path)

comp_id = "GB1"
season = 2012

gb1_games = games_df[(games_df['competition_id']==comp_id) & (games_df['season']==season)]
print(f"GB1 2012 maç sayısı: {len(gb1_games)}")