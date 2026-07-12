from pathlib import  Path
import csv
DATA_DIR = Path("data/raw/transfermarkt")
clubs_csv_path = DATA_DIR / "clubs.csv"
games_csv_path = DATA_DIR / "games.csv"
with open (clubs_csv_path, mode="r",encoding="utf-8") as file:
    reader=csv.DictReader(file)
    sayac=0
    for satir in reader:
        print(satir)
        sayac+=1
        if sayac== 3:
            break

