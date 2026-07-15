from math import pi
from pathlib import  Path
import csv
DATA_DIR = Path("data/raw/transfermarkt")
clubs_csv_path = DATA_DIR / "clubs.csv"
games_csv_path = DATA_DIR / "games.csv"
club_games_csv_path = DATA_DIR / "club_games.csv"
valid_game_ids = []
arsenal_matches = []
game_dates = {}

def get_league_matches(comp_id,season):
    matches=[]
    with open(games_csv_path,mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for satir in reader:
            if satir['competition_id'] == comp_id and satir['season'] == str(season):
                matches.append(satir)
                
    return matches

gb1_2012_matches = get_league_matches('GB1', '2012')
print(f"GB1 2012 sezonunda bulunan maç sayısı: {len(gb1_2012_matches)}")
for satir in gb1_2012_matches:
    game_dates[satir['game_id']] = satir['date']

with open(club_games_csv_path, mode="r", encoding="utf-8") as file:
    reader= csv.DictReader(file)
    for satir in reader:
        if satir['club_id'] == "11" and satir['game_id'] in game_dates:
            satir['date'] = game_dates[satir['game_id']]
            arsenal_matches.append(satir)

print(len(arsenal_matches))
arsenal_matches.sort(key=lambda x: x['date'], reverse=True)
recent_10_matches:arsenal_matches[:10]
for satir in recent_10_matches:
    print(satir['date'])