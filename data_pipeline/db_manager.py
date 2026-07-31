import sqlite3

def get_connection():
    conn = sqlite3.connect("matchlens.db")
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

if __name__ == "__main__":
    init_db()
    print("Veritabanı ve tablo başarıyla oluşturuldu!")