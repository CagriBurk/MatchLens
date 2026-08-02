import sqlite3
import pandas as pd
import os

def load_csvs_to_db():
    # Asıl veritabanımıza bağlanıyoruz
    db_path = "database/matchlens.db"
    conn = sqlite3.connect(db_path)
    
    # Tüm CSV'leri değil, yapay zeka için en kritik olanları seçiyoruz
    # Sol taraf: DB'de oluşacak tablo adı, Sağ taraf: CSV dosyasının adı
    csv_files = {
        "tm_clubs": "clubs.csv",
        "tm_games": "games.csv",
        "tm_team_form": "team_form_snapshot.csv",
        "tm_players": "players.csv",
        "tm_player_valuations": "player_valuations.csv"
    }

    # DİKKAT: CSV dosyalarının bulunduğu klasörün yolunu buraya yazmalısın.
    # Örneğin dosyalar ana dizindeyse "./" veya "data/" içindeyse "./data/" yap.
    csv_folder = "data/raw/transfermarkt" 

    print("CSV dosyaları veritabanına aktarılıyor. Boyuta göre 1-2 dakika sürebilir...\n" + "-"*40)

    for table_name, file_name in csv_files.items():
        file_path = os.path.join(csv_folder, file_name)
        
        if os.path.exists(file_path):
            print(f"⏳ {file_name} okunuyor...")
            # low_memory=False parametresi büyük dosyalarda tip karmaşasını önler
            df = pd.read_csv(file_path, low_memory=False)
            
            print(f"💾 '{table_name}' tablosu olarak SQL'e yazılıyor...")
            # if_exists="replace" ile kodu her çalıştırdığımızda tabloyu temizleyip baştan yazar
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            
            print(f"✅ Başarılı! ({len(df)} satır eklendi)\n")
        else:
            print(f"❌ HATA: {file_path} dosyası bulunamadı. Yolunu kontrol et!\n")

    conn.close()
    print("-" * 40 + "\n🚀 Tüm aktarım işlemleri kusursuz tamamlandı!")

if __name__ == "__main__":
    load_csvs_to_db()