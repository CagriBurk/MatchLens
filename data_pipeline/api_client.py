import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://v3.football.api-sports.io"

TARGET_LEAGUE_IDS = {
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    203,  # Super Lig
}

def fetch_daily_fixtures(date_str: str) -> dict:
    api_key = os.getenv("API_FOOTBALL_KEY")

    if not api_key:
        raise ValueError("API_FOOTBALL_KEY is missing. Please define it in your .env file.")
    url = f"{BASE_URL}/fixtures"
    headers = {
        "x-apisports-key": api_key
    }
    params={
        "date": date_str
    }
    response = requests.get(url,headers=headers, params=params, timeout=15)
    response.raise_for_status()
    return response.json()

def parse_fixture(raw_fixture: dict) -> dict:
    fixture = raw_fixture.get("fixture", {})
    league = raw_fixture.get("league", {})
    teams = raw_fixture.get("teams", {})
    goals = raw_fixture.get("goals", {})

    home_team = teams.get("home", {})
    away_team = teams.get("away", {})
    status = fixture.get("status", {})

    return {
        "fixture_id": fixture.get("id"),
        "date": fixture.get("date"),
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "season": league.get("season"),
        "home_team_id": home_team.get("id"),
        "home_team_name": home_team.get("name"),
        "away_team_id": away_team.get("id"),
        "away_team_name": away_team.get("name"),
        "status_short": status.get("short"),
        "status_long": status.get("long"),
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
    }


def get_target_league_fixtures(date_str: str) -> list[dict]:
    data = fetch_daily_fixtures(date_str)
    fixtures = data.get("response", [])

    parsed_fixtures = []

    for raw_fixture in fixtures:
        parsed = parse_fixture(raw_fixture)

        if parsed.get("league_id") in TARGET_LEAGUE_IDS:
            parsed_fixtures.append(parsed)

    return parsed_fixtures

if __name__ == "__main__":
    data = fetch_daily_fixtures("2025-10-18")
    fixtures = data.get("response", [])

    print("Raw fixture count:", len(fixtures))

    league_ids = set()

    for raw_fixture in fixtures:
        parsed = parse_fixture(raw_fixture)
        league_ids.add((parsed["league_id"], parsed["league_name"], parsed["season"]))

    for league in sorted(league_ids):
        print(league)