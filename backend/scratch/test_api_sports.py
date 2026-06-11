import requests
import json

API_KEY = "295d4fb1c2874959ac098d3978746dcb"
HEADERS = {
    "x-apisports-key": API_KEY
}

def check_fixtures(season=2026):
    print(f"\n--- CHECKING FIXTURES FOR LEAGUE 1, SEASON {season} ---")
    url = f"https://v3.football.api-sports.io/fixtures?league=1&season={season}"
    response = requests.get(url, headers=HEADERS)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    
    # Check for errors or warnings in the API response
    if data.get("errors"):
        print("API Errors:", data["errors"])
    if data.get("warnings"):
        print("API Warnings:", data["warnings"])
        
    fixtures = data.get("response", [])
    total_matches = len(fixtures)
    print(f"Total matches returned: {total_matches}")
    
    if total_matches > 0:
        print("\n--- FIRST 5 MATCHES ---")
        for f in fixtures[:5]:
            fixture_id = f.get("fixture", {}).get("id")
            date = f.get("fixture", {}).get("date")
            round_name = f.get("fixture", {}).get("round")
            home_team = f.get("teams", {}).get("home", {}).get("name")
            away_team = f.get("teams", {}).get("away", {}).get("name")
            print(f"ID: {fixture_id} | Date: {date} | Round: {round_name} | {home_team} vs {away_team}")
            
        print("\n--- LAST 5 MATCHES ---")
        for f in fixtures[-5:]:
            fixture_id = f.get("fixture", {}).get("id")
            date = f.get("fixture", {}).get("date")
            round_name = f.get("fixture", {}).get("round")
            home_team = f.get("teams", {}).get("home", {}).get("name")
            away_team = f.get("teams", {}).get("away", {}).get("name")
            print(f"ID: {fixture_id} | Date: {date} | Round: {round_name} | {home_team} vs {away_team}")
    else:
        print("No fixtures returned.")

def check_leagues():
    print("\n--- SEARCHING FOR 'World Cup' LEAGUES ---")
    url = "https://v3.football.api-sports.io/leagues?search=World Cup"
    response = requests.get(url, headers=HEADERS)
    print(f"Status Code: {response.status_code}")
    data = response.json()
    
    if data.get("errors"):
        print("API Errors:", data["errors"])
        
    leagues = data.get("response", [])
    print(f"Total leagues matching 'World Cup': {len(leagues)}")
    for item in leagues:
        league = item.get("league", {})
        country = item.get("country", {})
        seasons = item.get("seasons", [])
        season_years = [s.get("year") for s in seasons]
        print(f"League ID: {league.get('id')} | Name: {league.get('name')} | Country: {country.get('name')} | Seasons: {season_years}")

if __name__ == "__main__":
    # Check both 2026 and 2022
    check_fixtures(2026)
    check_fixtures(2022)
    check_leagues()
