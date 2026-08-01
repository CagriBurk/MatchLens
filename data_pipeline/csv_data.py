import pandas as pd

# CSV dosyanın tam adını ve yolunu buraya yaz
csv_yolu = "data/raw/transfermarkt/transfers.csv" 

# Veriyi okuyoruz
df = pd.read_csv(csv_yolu)

print("--- SÜTUNLAR VE VERİ TİPLERİ ---")
print(df.info())

print("\n--- İLK 3 SATIR ÖRNEĞİ ---")
# Ekrana düzgün sığması için transpoze (T) alarak yazdırıyoruz
print(df.head(3).T)