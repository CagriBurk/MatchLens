import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path("database/matchlens.db")
RAW_DATA_DIR = Path("data/raw/transfermarkt")

competitions_csv_path = RAW_DATA_DIR / "competitions.csv"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(DB_PATH)
competitions_df = csv_reader = pd.read_csv(competitions_csv_path)

competitions_df.to_sql("competitions",conn,if_exists="replace",index=False)
query= """
SELECT game_id, competition_id, season, date, home_club_id, away_club_id,home_club_goals, away_club_goals
FROM games
WHERE competition_id='GB1' AND season =2012
ORDER BY date ASC
LIMIT 10;
"""
result = conn.execute(query)

tables = result.fetchall()
print(tables)


conn.close() 