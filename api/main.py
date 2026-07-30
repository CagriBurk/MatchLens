from fastapi import FastAPI,HTTPException, status
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
def get_matches(game_id:int, limit:int =10):
    conn = sqlite3.connect("database/matchlens.db")
    df = pd.read_sql_query('SELECT * FROM match_features WHERE game_id = ?', conn, params=(game_id,))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="Match Not Found")
    return df.to_dict(orient="records")[0]


@app.get("/teams/{club_id}/form")
def get_team_latest_form(club_id: int):
    conn =sqlite3.connect("database/matchlens.db")
    df = pd.read_sql_query('SELECT * FROM team_form_snapshots WHERE club_id = ? ORDER BY date DESC LIMIT 1',conn,params=(club_id,))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="Team form not found")
    return df.to_dict(orient="records")[0]


@app.get("/matches/{game_id}/analysis")
def get_match_analysis(game_id: int):
    conn = sqlite3.connect("database/matchlens.db")
    df =pd.read_sql_query('SELECT * FROM match_features WHERE game_id =?',conn,params=(game_id,))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404,detail="Analysis not found")
    match_data = df.to_dict(orient="records")[0]
    adv_score = match_data["form_advantage"]

    if adv_score > 3:
        match_comment = "Ev sahibi takım net favori."
    elif adv_score < -3:
        match_comment = "Deplasman takımı daha formda."
    else:
        match_comment = "İki takım denk güçte, riskli maç."
    return {
        "game_id": match_data["game_id"],
        "home_club_id": match_data["home_club_id"],
        "away_club_id": match_data["away_club_id"],
        "form_advantage_score": adv_score,
        "analysis": match_comment
    }