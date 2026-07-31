import sqlite3

def get_connection():
    conn = sqlite3.connect("database/matchlens.db")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY,
        date TEXT,
        league_id INTEGER,
        league_name TEXT,
        season INTEGER,
        home_team_id INTEGER,
        home_team_name TEXT,
        away_team_id INTEGER,
        away_team_name TEXT,
        home_goals INTEGER,
        away_goals INTEGER,
        status_short TEXT
    )
    """

    cursor.execute(query)
    conn.commit()
    conn.close()

def save_matches(matches: list[dict]):
    if not matches: return
    conn = get_connection()
    cursor = conn.cursor()

    query="""
    INSERT OR REPLACE INTO matches (
        match_id, date, league_id, league_name, season, 
        home_team_id, home_team_name, away_team_id, away_team_name, 
        home_goals, away_goals, status_short
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = []
    
    for match in matches:
        val = (
            match.get("fixture_id"),
            match.get("date"),
            match.get("league_id"),
            match.get("league_name"),
            match.get("season"),
            match.get("home_team_id"),
            match.get("home_team_name"),
            match.get("away_team_id"),
            match.get("away_team_name"),
            match.get("home_goals"),
            match.get("away_goals"),
            match.get("status_short")
        )
        values.append(val)

    cursor.executemany(query, values)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Veritabanı ve matches tablosu hazır.")
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM matches")
    match_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"Veritabanındaki toplam maç sayısı: {match_count}")