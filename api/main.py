from fastapi import FastAPI
import sqlite3
import pandas as pd

app = FastAPI(title="Matchlens API")

@app.get("/")
def read_root():
    return{"status": "Matchlens API has been started succesfully"}

@app.get("/features")
def get_features(limit: int=10):
    conn = sqlite3.connect("database/matchlens.db")
    df = pd.read_sql_query('SELECT * FROM match_features LIMIT ?', conn, params=(limit,))
    conn.close()
    return df.to_dict(orient="records")

@app.get("/features/{game_id}")
def get_feature_by_id(game_id: int):
    conn = sqlite3.connect("database/matchlens.db")
    df = pd.read_sql_query('SELECT * FROM match_features WHERE game_id = ?', conn, params=(game_id,))
    conn.close()
    return df.to_dict(orient="records")

