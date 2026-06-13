from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserRanking
from app.services.scoring_service import calculate_assigned_team_points, calculate_tournament_points

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserRanking])
def get_ranking(db: Session = Depends(get_db)) -> List[UserRanking]:
    """Return all users sorted by puntos_totales DESC, aciertos_perfectos DESC, with ranking position."""
    # Filter out admin users
    users = (
        db.query(User)
        .filter(User.is_admin == False)
        .order_by(User.puntos_totales.desc(), User.aciertos_perfectos.desc())
        .all()
    )

    ranking: List[UserRanking] = []
    for idx, user in enumerate(users, start=1):
        puntos_underdog = calculate_assigned_team_points(db, user)
        puntos_torneo = calculate_tournament_points(db, user.id)
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
            )
        )

    return ranking

