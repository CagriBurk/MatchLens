from math import pi
from pathlib import  Path
import csv
DATA_DIR = Path("data/raw/transfermarkt")
clubs_csv_path = DATA_DIR / "clubs.csv"
games_csv_path = DATA_DIR / "games.csv"
club_games_csv_path = DATA_DIR / "club_games.csv"
league_form_table = []

def get_league_matches(comp_id,season):
    matches=[]
    with open(games_csv_path,mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for satir in reader:
            if satir['competition_id'] == comp_id and satir['season'] == str(season):
                matches.append(satir)
                
    return matches

def get_team_recent_form(club_id, comp_id, season, limit=10):
    league_matches = get_league_matches(comp_id,season)
    game_dates = {}
    team_matches = [] 
    for satir in league_matches:
        game_dates[satir['game_id']] = satir['date']
    with open(club_games_csv_path, mode="r", encoding="utf-8") as file:
        reader= csv.DictReader(file)
        for satir in reader:
            if satir['club_id'] == str(club_id) and satir['game_id'] in game_dates:
                satir['date'] = game_dates[satir['game_id']]
                team_matches.append(satir)
    team_matches.sort(key=lambda x: x['date'], reverse=True)
    recent_matches = team_matches[:limit]
    total_matches = len(recent_matches)
    if total_matches == 0:
        return {"club_id":club_id,"error":"No matches found for this season"}
    wins = 0
    draws = 0
    losses = 0
    points = 0
    goals_for = 0
    goals_against = 0
    over_2_5_count = 0
    btts_count = 0  
    for match in recent_matches:
        own_g = int(match['own_goals'])
        opp_g = int(match['opponent_goals'])

        if own_g > opp_g:
            wins += 1
            points += 3
        elif opp_g == own_g:
            draws += 1
            points += 1
        else:
            losses += 1

        goals_for += own_g
        goals_against += opp_g

        if (own_g + opp_g) >= 3:
            over_2_5_count += 1
        if (own_g > 0 and opp_g > 0):
            btts_count += 1
    # Oranları ve ortalamaları hesapla
    points_per_match = round(points / total_matches, 2)
    goals_for_avg = round(goals_for / total_matches, 2)
    goals_against_avg = round(goals_against / total_matches, 2)
    goal_difference = goals_for - goals_against
    over_2_5_rate = round(over_2_5_count / total_matches, 2)
    btts_rate = round(btts_count / total_matches, 2)

    # Tüm veriyi paketle (Dictionary)
    form_data = {
        "club_id": club_id,
        "competition_id": comp_id,
        "season": season,
        "total_matches": total_matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "points": points,
        "points_per_match": points_per_match,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goal_difference,
        "goals_for_avg": goals_for_avg,
        "goals_against_avg": goals_against_avg,
        "over_2_5_rate": over_2_5_rate,
        "btts_rate": btts_rate
    }

    return form_data


def get_league_clubs(comp_id):
    clubs_list = []
    with open(clubs_csv_path, mode="r", encoding="utf-8") as file:
        reader= csv.DictReader(file)
        for satir in reader:
            if satir['domestic_competition_id'] == comp_id:
                clubs_list.append({
                "club_id": satir["club_id"],
                "name": satir["name"]
                }) 
    return clubs_list

gb1_clubs = get_league_clubs("GB1")

for club in gb1_clubs:
    form_data = get_team_recent_form(club['club_id'], "GB1", 2012, limit=10)
    if "error" not in form_data:
        # Fonksiyon sadece club_id dönüyordu. Tabloda isim yazması için ismi de ekleyelim:
        form_data['name'] = club['name']

        # Takımı listeye ekle
        league_form_table.append(form_data)
league_form_table.sort(key=lambda x: (x['points'], x['goal_difference']), reverse=True)
print("\n--- 2012 Premier Lig Son 10 Maç Form Tablosu ---")
for sira, takim in enumerate(league_form_table, start=1):
    print(f"{sira:2}. {takim['name']:<25} | Puan: {takim['points']} | Averaj: {takim['goal_difference']:3} | KG Var: {takim['btts_rate']}")