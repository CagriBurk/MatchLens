import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path("database/matchlens.db")
RAW_DATA_DIR = Path("data/raw/transfermarkt")

competitions_csv_path = RAW_DATA_DIR / "competitions.csv"
games_csv_path = RAW_DATA_DIR / "games.csv"
club_games_csv_path= RAW_DATA_DIR / "club_games.csv"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

competitions_df = csv_reader = pd.read_csv(competitions_csv_path)
competitions_df.to_sql("competitions",conn,if_exists="replace",index=False)

games_df = csv_reader = pd.read_csv(games_csv_path)
games_df.to_sql("games",conn,if_exists="replace",index=False)

club_games_df = csv_reader = pd.read_csv(club_games_csv_path)
club_games_df.to_sql("club_games",conn,if_exists="replace",index=False)


conn.close() 