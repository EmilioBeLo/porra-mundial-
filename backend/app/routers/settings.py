from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import SystemSetting, User
from app.schemas import ActiveCompetitionUpdate, CompetitionResponse
from app.services.scoring_service import recalculate_all_users_points

router = APIRouter(prefix="/api/settings", tags=["settings"])

COMPETITIONS = [
    {"league_id": 1, "name": "Mundial de Fútbol", "season": 2026},
    {"league_id": 140, "name": "LaLiga (España)", "season": 2025},
    {"league_id": 39, "name": "Premier League (Inglaterra)", "season": 2025},
    {"league_id": 135, "name": "Serie A (Italia)", "season": 2025},
    {"league_id": 78, "name": "Bundesliga (Alemania)", "season": 2025},
    {"league_id": 61, "name": "Ligue 1 (Francia)", "season": 2025},
]


@router.get("/competitions", response_model=List[CompetitionResponse])
def get_competitions() -> List[dict]:
    """List of supported competitions."""
    return COMPETITIONS


@router.get("/active", response_model=CompetitionResponse)
def get_active_competition(db: Session = Depends(get_db)) -> dict:
    """Get active competition details."""
    try:
        active_id = SystemSetting.get_int(db, "active_league_id", COMPETITIONS[0]["league_id"])
        active_season = SystemSetting.get_int(db, "active_season", COMPETITIONS[0]["season"])
        active_name = SystemSetting.get_str(db, "active_league_name", COMPETITIONS[0]["name"])
        return {
            "league_id": active_id,
            "name": active_name,
            "season": active_season,
        }
    except Exception:
        return COMPETITIONS[0]


@router.put("/active", response_model=CompetitionResponse)
def update_active_competition(
    body: ActiveCompetitionUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Update active competition and trigger recalculation. Requires admin."""
    selected_comp = next((c for c in COMPETITIONS if c["league_id"] == body.league_id), None)
    if not selected_comp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Liga no soportada",
        )

    def set_setting(key: str, value: str):
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)

    set_setting("active_league_id", str(selected_comp["league_id"]))
    set_setting("active_season", str(selected_comp["season"]))
    set_setting("active_league_name", selected_comp["name"])

    db.commit()

    recalculate_all_users_points(db, selected_comp["league_id"])

    return selected_comp
