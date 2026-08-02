import soccerdata as sd
import pandas as pd
import sqlite3

def fetch_understat_match_stats():
    pd.set_option('display.max_columns', None)
    
    print("Understat'tan Taktiksel Maç Verileri Çekiliyor...")
    # Understat modülünü başlatıyoruz
    understat = sd.Understat(leagues="ENG-Premier League", seasons="2324")
    
    # Tüm maçların taktiksel istatistiklerini al
    match_stats = understat.read_team_match_stats()
    
    # 1. Aşama: Veriyi temizleyip SQL'e uygun hale getirme
    match_stats = match_stats.reset_index()
    
    print(f"\nToplam {len(match_stats)} maç verisi çekildi.")
    print("İşte veritabanına yazılacak muazzam Taktiksel Metrikler:")
    print(match_stats[['date', 'home_team', 'away_team', 'home_xg', 'away_xg', 'home_ppda', 'away_deep_completions']].head(3))
    
    # 2. Aşama: SQLite Veritabanına Kaydetme
    # database klasöründeki matchlens.db'ye bağlanıyoruz
    db_path = "database/matchlens.db"
    conn = sqlite3.connect(db_path)
    
    # Pandas'ın sihirli to_sql fonksiyonu ile tüm DataFrame'i tablo olarak yazıyoruz
    match_stats.to_sql("tactical_match_stats", conn, if_exists="replace", index=False)
    conn.close()
    
    print(f"\n[BAŞARILI] Veriler {db_path} içine 'tactical_match_stats' tablosu olarak kaydedildi!")

if __name__ == "__main__":
    fetch_understat_match_stats()
