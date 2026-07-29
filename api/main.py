from fastapi import FastAPI,HTTPException
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

@app.get("/teams/{club_id}/home-matches")
def home_matches(club_id: int, limit:int =10):
    conn = sqlite3.connect("database/matchlens.db")
    df = pd.read_sql_query('SELECT * FROM match_features WHERE home_club_id = ? LIMIT ?', conn, params=(club_id,limit))
    conn.close()
    return df.to_dict(orient="records")

@app.get("/matches/{game_id}")
def get_matches(club_id:int, limit:int =10):
    conn = sqlite3.connect/"database/matchlens.db"
    df = pd.read_sql_query('SELECT * FROM match_features WHERE home_club_id = ? LIMIT ?', conn, params=(club_id,limit))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="Match Not Found")
    return df.to_dict(orient="records")[0]