import pandas as pd
import sqlite3

conn = sqlite3.connect("database/matchlens.db")

query_api = "SELECT DISTINCT home_team_id AS api_id, home_team_name AS api_name FROM matches"
df_api = pd.read_sql_query(query_api,conn)

query_tm = "SELECT club_id AS tm_id, name AS tm_name FROM tm_clubs"
df_tm = pd.read_sql_query(query_tm,conn)

print(df_api.head(5))
print(df_tm.head(5))
