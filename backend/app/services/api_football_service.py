import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.config import settings
from app.models import Match, SystemSetting
from app.services.scoring_service import recalculate_match

STADIUM_OFFSETS = {
    "1": -6,  # Estadio Azteca (Mexico City) - Mexico does not use DST
    "2": -6,  # Estadio Akron (Guadalajara) - Mexico does not use DST
    "3": -6,  # Estadio BBVA (Monterrey) - Mexico does not use DST
    "4": -5,  # AT&T Stadium (Dallas) - CDT (UTC-5)
    "5": -5,  # NRG Stadium (Houston) - CDT (UTC-5)
    "6": -5,  # Arrowhead Stadium (Kansas City) - CDT (UTC-5)
    "7": -4,  # Mercedes-Benz Stadium (Atlanta) - EDT (UTC-4)
    "8": -4,  # Hard Rock Stadium (Miami) - EDT (UTC-4)
    "9": -4,  # Gillette Stadium (Boston) - EDT (UTC-4)
    "10": -4, # MetLife Stadium (New York) - EDT (UTC-4)
    "11": -4, # Lincoln Financial Field (Philadelphia) - EDT (UTC-4)
    "12": -4, # BMO Field (Toronto) - EDT (UTC-4)
    "13": -7, # BC Place (Vancouver) - PDT (UTC-7)
    "14": -7, # Lumen Field (Seattle) - PDT (UTC-7)
    "15": -7, # Levi's Stadium (San Francisco) - PDT (UTC-7)
    "16": -7, # SoFi Stadium (Los Angeles) - PDT (UTC-7)
}


def parse_datetime(date_str: str) -> datetime:
    """Parse API-Football ISO datetime format into naive UTC datetime."""
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(date_str)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def fetch_and_sync_fixtures(db: Session) -> dict:
    """
    Fetch all fixtures from API-Football for the configured league and season,
    and upsert them in the local database.
    If active_league_id == 1, falls back to the open-source GitHub JSON matches.
    """
    active_league_id = SystemSetting.get_int(db, "active_league_id", settings.API_FOOTBALL_LEAGUE_ID)
    active_season = SystemSetting.get_int(db, "active_season", settings.API_FOOTBALL_SEASON)

    if active_league_id == 1:
        # Download from github
        teams_url = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.teams.json"
        matches_url = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.matches.json"
        
        try:
            teams_resp = requests.get(teams_url, timeout=15)
            teams_resp.raise_for_status()
            teams_json = teams_resp.json()
            
            matches_resp = requests.get(matches_url, timeout=15)
            matches_resp.raise_for_status()
            matches_json = matches_resp.json()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al conectar con GitHub para el Mundial 2026: {str(e)}"
            )

        # Parse Spain's group
        spain_group = None
        for team in teams_json:
            if team.get("name_en") == "Spain":
                spain_group = team.get("groups")
                break

        teams_map = {team["id"]: team["name_en"] for team in teams_json}
        
        stage_mapping = {
            "r32": "Dieciseisavos de Final",
            "round32": "Dieciseisavos de Final",
            "roundof32": "Dieciseisavos de Final",
            "r16": "Octavos de Final",
            "round16": "Octavos de Final",
            "roundof16": "Octavos de Final",
            "qf": "Cuartos de Final",
            "quarter": "Cuartos de Final",
            "sf": "Semifinales",
            "semi": "Semifinales",
            "third": "Tercer Puesto",
            "thirdplace": "Tercer Puesto",
            "final": "Final",
        }
        
        count = 0
        for match_item in matches_json:
            api_id = int(match_item["id"])
            equipo_local = teams_map.get(match_item["home_team_id"], match_item.get("home_team_label", "TBD"))
            equipo_visitante = teams_map.get(match_item["away_team_id"], match_item.get("away_team_label", "TBD"))
            
            # MM/DD/YYYY HH:MM (e.g. 06/11/2026 13:00)
            local_date_str = match_item["local_date"]
            stadium_id_str = str(match_item.get("stadium_id", ""))
            naive_local = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            offset = STADIUM_OFFSETS.get(stadium_id_str, 0)
            fecha_hora = naive_local - timedelta(hours=offset)
            
            match_type = match_item.get("type", "").lower()
            if match_type == "group":
                grupo_o_fase = f"Grupo {match_item.get('group', '')}"
            else:
                clean_type = match_type.replace(" ", "").replace("_", "")
                grupo_o_fase = stage_mapping.get(clean_type, match_item.get("type", "").capitalize())
                
            es_partido_doble = False
            if spain_group and match_item.get("group") == spain_group:
                es_partido_doble = True
                
            finished_str = str(match_item.get("finished", "")).upper()
            finished = finished_str == "TRUE"
            
            match = db.query(Match).filter(Match.api_id == api_id).first()
            if match:
                match.fecha_hora = fecha_hora
                match.grupo_o_fase = grupo_o_fase
                match.equipo_local = equipo_local
                match.equipo_visitante = equipo_visitante
                match.es_partido_doble = es_partido_doble
                match.league_id = active_league_id
                
                if finished:
                    api_goles_local = int(match_item["home_score"])
                    api_goles_visitante = int(match_item["away_score"])
                    if match.goles_local_real is None or match.goles_visitante_real is None:
                        match.goles_local_real = api_goles_local
                        match.goles_visitante_real = api_goles_visitante
                        recalculate_match(db, match)
            else:
                match = Match(
                    api_id=api_id,
                    equipo_local=equipo_local,
                    equipo_visitante=equipo_visitante,
                    fecha_hora=fecha_hora,
                    grupo_o_fase=grupo_o_fase,
                    es_partido_doble=es_partido_doble,
                    league_id=active_league_id
                )
                if finished:
                    match.goles_local_real = int(match_item["home_score"])
                    match.goles_visitante_real = int(match_item["away_score"])
                db.add(match)
                
            count += 1
            
        db.commit()
        return {"status": "success", "synchronized": count}

    else:
        url = f"{settings.API_FOOTBALL_URL}/fixtures"
        headers = {
            "x-apisports-key": settings.API_FOOTBALL_KEY
        }
        params = {
            "league": active_league_id,
            "season": active_season
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al conectar con API-Football: {str(e)}"
            )
            
        data = response.json()
        fixtures = data.get("response", [])
        
        # 1. Buscar el grupo de España
        spain_group = None
        for item in fixtures:
            teams = item.get("teams", {})
            home_name = teams.get("home", {}).get("name")
            away_name = teams.get("away", {}).get("name")
            if home_name == "Spain" or away_name == "Spain":
                spain_group = item.get("league", {}).get("round")
                break

        count = 0
        for item in fixtures:
            fixture_data = item.get("fixture", {})
            api_id = fixture_data.get("id")
            if api_id is None:
                continue
                
            teams = item.get("teams", {})
            equipo_local = teams.get("home", {}).get("name")
            equipo_visitante = teams.get("away", {}).get("name")
            
            date_str = fixture_data.get("date")
            if not date_str:
                continue
            fecha_hora = parse_datetime(date_str)
            
            grupo_o_fase = item.get("league", {}).get("round", "Unknown")
            
            es_partido_doble = False
            if spain_group and grupo_o_fase and (spain_group in grupo_o_fase or grupo_o_fase in spain_group):
                es_partido_doble = True
                
            match = db.query(Match).filter(Match.api_id == api_id).first()
            if match:
                match.fecha_hora = fecha_hora
                match.grupo_o_fase = grupo_o_fase
                match.equipo_local = equipo_local
                match.equipo_visitante = equipo_visitante
                match.es_partido_doble = es_partido_doble
                match.league_id = active_league_id

                # Si el partido terminó, actualizamos goles
                short_status = fixture_data.get("status", {}).get("short")
                if short_status in ["FT", "AET", "PEN"]:
                    goals = item.get("goals", {})
                    api_goles_local = goals.get("home")
                    api_goles_visitante = goals.get("away")
                    if api_goles_local is not None and api_goles_visitante is not None:
                        if match.goles_local_real is None or match.goles_visitante_real is None:
                            match.goles_local_real = api_goles_local
                            match.goles_visitante_real = api_goles_visitante
                            recalculate_match(db, match)
            else:
                match = Match(
                    api_id=api_id,
                    equipo_local=equipo_local,
                    equipo_visitante=equipo_visitante,
                    fecha_hora=fecha_hora,
                    grupo_o_fase=grupo_o_fase,
                    es_partido_doble=es_partido_doble,
                    league_id=active_league_id
                )

                # Si el partido terminó, actualizamos goles
                short_status = fixture_data.get("status", {}).get("short")
                if short_status in ["FT", "AET", "PEN"]:
                    goals = item.get("goals", {})
                    api_goles_local = goals.get("home")
                    api_goles_visitante = goals.get("away")
                    if api_goles_local is not None and api_goles_visitante is not None:
                        match.goles_local_real = api_goles_local
                        match.goles_visitante_real = api_goles_visitante
                db.add(match)
                
            count += 1
            
        db.commit()
        return {"status": "success", "synchronized": count}

def sync_match_results(db: Session) -> dict:
    """
    Fetch current statuses for all local matches that lack real goals,
    updating the scores and triggering predictions recalculation if a match is finished.
    """
    active_league_id = SystemSetting.get_int(db, "active_league_id", settings.API_FOOTBALL_LEAGUE_ID)
    active_season = SystemSetting.get_int(db, "active_season", settings.API_FOOTBALL_SEASON)

    if active_league_id == 1:
        matches = db.query(Match).filter(Match.league_id == 1, Match.goles_local_real == None).all()
        if not matches:
            return {"status": "success", "updated": 0}

        matches_url = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.matches.json"
        try:
            response = requests.get(matches_url, timeout=15)
            response.raise_for_status()
            matches_json = response.json()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al conectar con GitHub para el Mundial 2026: {str(e)}"
            )

        json_match_map = {int(m["id"]): m for m in matches_json}

        count = 0
        for match in matches:
            if match.api_id in json_match_map:
                json_match = json_match_map[match.api_id]
                finished_str = str(json_match.get("finished", "")).upper()
                if finished_str == "TRUE":
                    match.goles_local_real = int(json_match["home_score"])
                    match.goles_visitante_real = int(json_match["away_score"])
                    recalculate_match(db, match)
                    count += 1

        db.commit()
        return {"status": "success", "updated_matches_count": count}

    else:
        matches = db.query(Match).filter(Match.api_id != None, Match.goles_local_real == None, Match.league_id == active_league_id).all()
        if not matches:
            return {"status": "success", "updated": 0}

        url = f"{settings.API_FOOTBALL_URL}/fixtures"
        headers = {
            "x-apisports-key": settings.API_FOOTBALL_KEY
        }
        params = {
            "league": active_league_id,
            "season": active_season
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al conectar con API-Football: {str(e)}"
            )
            
        data = response.json()
        fixtures = data.get("response", [])
        fixture_map = {item["fixture"]["id"]: item for item in fixtures if "fixture" in item and "id" in item["fixture"]}
        
        count = 0
        for match in matches:
            fixture = fixture_map.get(match.api_id)
            if not fixture:
                continue
                
            short_status = fixture.get("fixture", {}).get("status", {}).get("short")
            if short_status in ["FT", "AET", "PEN"]:
                goals = fixture.get("goals", {})
                api_goles_local = goals.get("home")
                api_goles_visitante = goals.get("away")
                if api_goles_local is not None and api_goles_visitante is not None:
                    match.goles_local_real = api_goles_local
                    match.goles_visitante_real = api_goles_visitante
                    recalculate_match(db, match)
                    count += 1
                    
        db.commit()
        return {"status": "success", "updated_matches_count": count}
