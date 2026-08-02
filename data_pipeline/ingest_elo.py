import soccerdata as sd
import pandas as pd
import sqlite3
import time

# Yeni haritalama dosyamızı içe aktarıyoruz
from elo_mapper import get_clubelo_name

def fetch_club_elo():
    print("ClubElo API'den Tarihsel Güç Puanları Çekiliyor...")
    conn = sqlite3.connect("database/matchlens.db")
    
    teams_df = pd.read_sql_query("SELECT DISTINCT home_team FROM tactical_match_stats", conn)
    teams = teams_df['home_team'].tolist()
    
    elo = sd.ClubElo()
    all_elo_history = []
    
    print(f"Toplam {len(teams)} takımın on yıllara dayanan tarihsel Elo puanları indiriliyor...")
    
    for team in teams:
        # İsim Çeviriciyi Kullanıyoruz
        clubelo_name = get_clubelo_name(team)
        
        print(f"Orijinal: {team} -> ClubElo: {clubelo_name} çekiliyor...")
        try:
            team_elo = elo.read_team_history(clubelo_name)
            team_elo = team_elo.reset_index()
            
            # Veritabanında orijinal isimleriyle eşleşmesi için orijinal ismi kaydediyoruz
            team_elo['original_team_name'] = team
            
            all_elo_history.append(team_elo)
            time.sleep(1)
        except Exception as e:
            print(f"Hata ({clubelo_name}): {e}")
            
    final_elo_df = pd.concat(all_elo_history, ignore_index=True)
    
    # SQLite'a Kaydet
    final_elo_df.to_sql("historical_club_elo", conn, if_exists="replace", index=False)
    conn.close()
    
    print("\n[BAŞARILI] Gerçek Elo puanları 'historical_club_elo' tablosuna yazıldı!")

if __name__ == "__main__":
    fetch_club_elo()
