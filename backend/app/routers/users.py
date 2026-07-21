from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserRanking
from app.services.scoring_service import calculate_assigned_team_points, calculate_tournament_points_breakdown

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserRanking])
def get_ranking(db: Session = Depends(get_db)) -> List[UserRanking]:
    """Return all users sorted by puntos_totales DESC, aciertos_perfectos DESC, with ranking position."""
    # Filter out only the user named "admin"
    users = (
        db.query(User)
        .filter(func.lower(User.nombre) != "admin")
        .order_by(User.puntos_totales.desc(), User.aciertos_perfectos.desc())
        .all()
    )

    ranking: List[UserRanking] = []
    for idx, user in enumerate(users, start=1):
        puntos_underdog = calculate_assigned_team_points(db, user)
        torneo_breakdown = calculate_tournament_points_breakdown(db, user.id)
        puntos_torneo = torneo_breakdown["total"]
        puntos_predicciones = user.puntos_totales - puntos_underdog - puntos_torneo
        ranking.append(
            UserRanking(
                id=user.id,
                nombre=user.nombre,
                puntos_totales=user.puntos_totales,
                aciertos_perfectos=user.aciertos_perfectos,
                assigned_team=user.assigned_team,
                created_at=user.created_at,
                posicion=idx,
                puntos_underdog=puntos_underdog,
                puntos_predicciones=puntos_predicciones,
                puntos_torneo=puntos_torneo,
                puntos_campeon=torneo_breakdown["campeon"],
                puntos_subcampeon=torneo_breakdown["subcampeon"],
                puntos_goleador=torneo_breakdown["goleador"],
                puntos_asistente=torneo_breakdown["asistente"],
            )
        )

    return ranking

