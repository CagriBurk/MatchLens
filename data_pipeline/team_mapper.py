import pandas as pd
import sqlite3
import difflib

conn = sqlite3.connect("database/matchlens.db")

query_api = "SELECT DISTINCT home_team_id AS api_id, home_team_name AS api_name FROM matches"
df_api = pd.read_sql_query(query_api, conn)

query_tm = "SELECT club_id AS tm_id, name AS tm_name FROM tm_clubs"
df_tm = pd.read_sql_query(query_tm, conn)

# TM takımlarını içinde arama yapabilmek için saf bir listeye çeviriyoruz
tm_team_list = df_tm['tm_name'].dropna().tolist()

mapping_data = []

print("Yapay zeka metin benzerliği algoritması çalışıyor...\n" + "-"*30)

# API'deki her bir takım için döngüye giriyoruz
for index, row in df_api.iterrows():
    api_id = row['api_id']
    api_name = row['api_name']
    
    # difflib ile TM listesinde %60 ve üzeri benzeyen EN İYİ 1 eşleşmeyi (n=1) arıyoruz
    matches = difflib.get_close_matches(api_name, tm_team_list, n=1, cutoff=0.6)
    
    if matches:
        best_match = matches[0]
        # Eşleşen takımın TM veritabanındaki orijinal ID'sini çekiyoruz
        tm_id = df_tm[df_tm['tm_name'] == best_match]['tm_id'].values[0]
        
        mapping_data.append({
            'api_id': api_id,
            'api_name': api_name,
            'tm_id': tm_id,
            'tm_name': best_match
        })
    else:
        # Eğer algoritma eşleşme bulamazsa "BULUNAMADI" yazsın, biz CSV'den düzeltiriz
        mapping_data.append({
            'api_id': api_id,
            'api_name': api_name,
            'tm_id': None,
            'tm_name': "BULUNAMADI"
        })

# Listeyi Pandas tablosuna çevir
df_mapping = pd.DataFrame(mapping_data)

# Dosyayı incelemek için ana dizine CSV olarak kaydet
csv_yolu = "team_mapping_draft.csv"
df_mapping.to_csv(csv_yolu, index=False)

print(f"Eşleştirme tamamlandı! Sonuçlar '{csv_yolu}' dosyasına kaydedildi.")

conn.close()