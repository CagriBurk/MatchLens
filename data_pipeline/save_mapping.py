import pandas as pd
import sqlite3

# 1. Az önce düzelttiğimiz CSV dosyasını okuyoruz
df_mapping = pd.read_csv("team_mapping_draft.csv")

# 2. Asıl veritabanımıza bağlanıyoruz
conn = sqlite3.connect("database/matchlens.db")

# 3. CSV içeriğini 'team_mapping' adlı bir tablo olarak gömüyoruz
print("Köprü tablosu veritabanına ekleniyor...")
df_mapping.to_sql("team_mapping", conn, if_exists="replace", index=False)

conn.close()
print("Başarılı! API ve Transfermarkt dünyaları artık birbirine bağlandı.")