"""
Seed script for World Cup 2026.

Drops all tables, recreates them, populates default admin/test users,
system settings, and downloads & seeds all 104 matches of the 2026 World Cup.

Usage:
    python seed_worldcup2026.py
"""

import os
import sys
from datetime import datetime, timedelta
import requests

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal
from app.models import Match, User, SystemSetting
from app.routers.auth import _hash_password

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

def seed():
    # 1. Drop and recreate all tables to start fresh
    print("🔄 dropping and recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Insert default users
        print("👤 seeding default users...")
        admin = User(
            nombre="admin",
            password_hash=_hash_password("admin123"),
            is_admin=True,
        )
        users_data = [
            ("Mura", "Mur@4c9A"),
            ("Choto", "Cho#82xB"),
            ("Cobrica", "Cob$19zY"),
            ("Vergador", "Ver%64wP"),
            ("Masca", "Mas&37vK"),
            ("Culkin", "Cul*85mN"),
            ("PerroLoco", "Per!23qR"),
            ("Juanre", "Jua#48tS"),
            ("Perico", "Per%90dL"),
            ("Cronix", "Cro*72kX"),
        ]
        db_users = [admin]
        for name, pwd in users_data:
            db_users.append(
                User(
                    nombre=name,
                    password_hash=_hash_password(pwd),
                    is_admin=False,
                )
            )
        db.add_all(db_users)
        
        # 3. Insert default settings
        print("⚙️ seeding default system settings...")
        db.add_all([
            SystemSetting(key="active_league_id", value="1"),
            SystemSetting(key="active_season", value="2026"),
            SystemSetting(key="active_league_name", value="Mundial de Fútbol"),
        ])
        db.flush()
        
        # 4. Download matches and teams from raw GitHub URLs
        print("📥 fetching teams and matches from GitHub...")
        teams_url = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.teams.json"
        matches_url = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.matches.json"
        
        teams_resp = requests.get(teams_url, timeout=15)
        teams_resp.raise_for_status()
        teams_json = teams_resp.json()
        
        matches_resp = requests.get(matches_url, timeout=15)
        matches_resp.raise_for_status()
        matches_json = matches_resp.json()
        
        # 5. Parse Spain's group
        spain_group = None
        for team in teams_json:
            if team.get("name_en") == "Spain":
                spain_group = team.get("groups")
                break
        
        if spain_group:
            print(f"🇪🇸 Spain is in group: {spain_group}")
        else:
            print("⚠️ Spain not found in teams list, cannot auto-detect group")
            
        # 6. Build teams map
        teams_map = {team["id"]: team["name_en"] for team in teams_json}
        
        # 7. Map stages/phases cleanly
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
        
        # 8. Parse and insert matches
        print("⚽ processing matches...")
        matches_count = 0
        for match_item in matches_json:
            api_id = int(match_item["id"])
            equipo_local = teams_map.get(match_item["home_team_id"], match_item.get("home_team_label", "TBD"))
            equipo_visitante = teams_map.get(match_item["away_team_id"], match_item.get("away_team_label", "TBD"))
            
            # Format: MM/DD/YYYY HH:MM (e.g. 06/11/2026 13:00)
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
                
            # Finished scores handling
            finished_str = str(match_item.get("finished", "")).upper()
            if finished_str == "TRUE":
                goles_local_real = int(match_item["home_score"])
                goles_visitante_real = int(match_item["away_score"])
            else:
                goles_local_real = None
                goles_visitante_real = None
                
            match_obj = Match(
                api_id=api_id,
                equipo_local=equipo_local,
                equipo_visitante=equipo_visitante,
                fecha_hora=fecha_hora,
                grupo_o_fase=grupo_o_fase,
                es_partido_doble=es_partido_doble,
                goles_local_real=goles_local_real,
                goles_visitante_real=goles_visitante_real,
                league_id=1
            )
            db.add(match_obj)
            matches_count += 1
            
        db.commit()
        print(f"Seeding completed: {matches_count} matches loaded.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
