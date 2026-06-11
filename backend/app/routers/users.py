from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserRanking

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserRanking])
def get_ranking(db: Session = Depends(get_db)) -> List[UserRanking]:
    """Return all users sorted by puntos_totales DESC, aciertos_perfectos DESC, with ranking position."""
    users = (
        db.query(User)
        .order_by(User.puntos_totales.desc(), User.aciertos_perfectos.desc())
        .all()
    )

    ranking: List[UserRanking] = []
    for idx, user in enumerate(users, start=1):
        ranking.append(
            UserRanking(
                id=user.id,
                nombre=user.nombre,
                puntos_totales=user.puntos_totales,
                aciertos_perfectos=user.aciertos_perfectos,
                created_at=user.created_at,
                posicion=idx,
            )
        )

    return ranking
