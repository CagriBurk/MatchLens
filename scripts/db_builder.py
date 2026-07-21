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
query = """
SELECT
    cg.game_id,
    g.date,
    g.competition_id,
    g.season,
    cg.club_id,
    cg.opponent_id,
    cg.own_goals,
    cg.opponent_goals,
    cg.hosting,
    cg.is_win
FROM club_games AS cg
JOIN games AS g
    ON cg.game_id = g.game_id
WHERE g.competition_id = 'GB1'
  AND g.season = 2012
ORDER BY g.date ASC;
"""
result = conn.execute(query)

team_match_records_df= pd.read_sql_query(query,conn)

print(team_match_records_df.head())
print(team_match_records_df.shape)

conn.close() 